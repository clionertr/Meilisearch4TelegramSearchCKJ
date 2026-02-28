"""
Dialog Download Scheduler

队列驱动的顺序下载调度器，支持每个会话的即时 pause/resume。

核心设计：
  - asyncio.Queue 驱动的 FIFO 队列
  - 单 worker 协程逐个取出执行（防止 Telegram 限流）
  - 每 batch 后通过 state_checker 检查 sync_state 实现优雅暂停
  - _pending_ids 集合防止重复入队
  - 集成 ProgressRegistry 进度上报
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from tg_search.core.logger import setup_logger

if TYPE_CHECKING:
    from tg_search.api.state import ProgressRegistry
    from tg_search.config.config_store import ConfigStore
    from tg_search.core.meilisearch import MeiliSearchClient
    from tg_search.core.telegram import TelegramUserBot

logger = setup_logger()


class DownloadPausedError(Exception):
    """下载被暂停（sync_state 不再是 active）"""


class DialogDownloadScheduler:
    """
    队列驱动的顺序下载调度器。

    用法：
        scheduler = DialogDownloadScheduler(config_store, meili, progress_registry)
        scheduler.set_client(user_bot)
        await scheduler.start()           # 启动 worker
        await scheduler.enqueue(12345)    # 动态添加下载任务
        await scheduler.stop()            # 优雅关闭
    """

    def __init__(
        self,
        config_store: ConfigStore,
        meili: MeiliSearchClient,
        progress_registry: ProgressRegistry | None = None,
    ) -> None:
        self._config_store = config_store
        self._meili = meili
        self._progress_registry = progress_registry

        self._queue: asyncio.Queue[int] = asyncio.Queue()
        self._pending_ids: set[int] = set()
        self._current_dialog_id: int | None = None
        self._worker_task: asyncio.Task[None] | None = None
        self._user_bot: TelegramUserBot | None = None
        self._client_ready = asyncio.Event()
        self._stopped = False

    # ── Lifecycle ──

    def set_client(self, user_bot: TelegramUserBot) -> None:
        """设置 Telegram 客户端（可在 on_ready 回调中调用）"""
        self._user_bot = user_bot
        self._client_ready.set()
        logger.info("[DownloadScheduler] Telegram client ready")

    async def start(self) -> None:
        """启动 worker 协程"""
        if self._worker_task is not None and not self._worker_task.done():
            logger.warning("[DownloadScheduler] already started, ignoring")
            return

        self._stopped = False
        self._worker_task = asyncio.create_task(self._worker(), name="download_scheduler_worker")
        logger.info("[DownloadScheduler] started")

    async def stop(self) -> None:
        """优雅停止 worker"""
        self._stopped = True
        if self._worker_task is not None and not self._worker_task.done():
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        self._worker_task = None
        logger.info("[DownloadScheduler] stopped")

    # ── Public API ──

    async def enqueue(self, dialog_id: int) -> bool:
        """
        将 dialog 加入下载队列。

        Returns:
            True 如果成功入队，False 如果已在队列中或正在下载
        """
        if dialog_id in self._pending_ids:
            logger.debug("[DownloadScheduler] dialog %d already pending, skip", dialog_id)
            return False
        if dialog_id == self._current_dialog_id:
            logger.debug("[DownloadScheduler] dialog %d currently downloading, skip", dialog_id)
            return False
        self._pending_ids.add(dialog_id)
        await self._queue.put(dialog_id)
        logger.info("[DownloadScheduler] enqueued dialog %d (queue_size=%d)", dialog_id, self._queue.qsize())
        return True

    async def enqueue_all_active(self) -> int:
        """从 config_store 读取所有 active sync dialogs 并入队。返回入队数量。"""
        config = await asyncio.to_thread(self._config_store.load_config, True)
        count = 0
        for str_id, state in config.sync.dialogs.items():
            if state.sync_state == "active":
                try:
                    did = int(str_id)
                except ValueError:
                    continue
                if await self.enqueue(did):
                    count += 1
        logger.info("[DownloadScheduler] enqueued %d active dialogs from config", count)
        return count

    @property
    def current_dialog_id(self) -> int | None:
        return self._current_dialog_id

    @property
    def pending_count(self) -> int:
        return self._queue.qsize()

    @property
    def is_running(self) -> bool:
        return self._worker_task is not None and not self._worker_task.done()

    # ── Worker ──

    async def _worker(self) -> None:
        """主 worker 循环：逐个取出 dialog 并下载"""
        logger.info("[DownloadScheduler] worker started, waiting for client...")
        await self._client_ready.wait()
        logger.info("[DownloadScheduler] client ready, processing queue")

        while not self._stopped:
            try:
                # 使用 wait_for 让 cancel 时不会永远阻塞
                dialog_id = await asyncio.wait_for(self._queue.get(), timeout=2.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            self._pending_ids.discard(dialog_id)
            self._current_dialog_id = dialog_id

            try:
                await self._download_one(dialog_id)
            except asyncio.CancelledError:
                logger.info("[DownloadScheduler] worker cancelled during download of dialog %d", dialog_id)
                break
            except Exception as exc:
                logger.error(
                    "[DownloadScheduler] unexpected error downloading dialog %d: %s: %s",
                    dialog_id,
                    type(exc).__name__,
                    exc,
                )
            finally:
                self._current_dialog_id = None

        logger.info("[DownloadScheduler] worker exited")

    async def _download_one(self, dialog_id: int) -> None:
        """下载单个 dialog 的历史消息"""
        # 1. 检查当前 sync_state
        config = await asyncio.to_thread(self._config_store.load_config, True)
        str_id = str(dialog_id)
        dialog_state = config.sync.dialogs.get(str_id)
        if dialog_state is None or dialog_state.sync_state != "active":
            logger.info("[DownloadScheduler] dialog %d is not active (state=%s), skipping",
                        dialog_id, dialog_state.sync_state if dialog_state else "deleted")
            return

        # 2. 获取 Telegram peer
        user_bot = self._user_bot
        if user_bot is None:
            logger.warning("[DownloadScheduler] no telegram client, skipping dialog %d", dialog_id)
            return

        try:
            peer = await user_bot.client.get_entity(dialog_id)
        except Exception as exc:
            logger.error("[DownloadScheduler] failed to get entity for dialog %d: %s", dialog_id, exc)
            if self._progress_registry is not None:
                await self._progress_registry.fail_progress(dialog_id, str(exc))
            return

        dialog_title = getattr(peer, "title", None) or str(dialog_id)

        # 3. 构建 state_checker（每 batch 后检查是否应继续）
        async def state_checker() -> bool:
            cfg = await asyncio.to_thread(self._config_store.load_config, True)
            ds = cfg.sync.dialogs.get(str_id)
            if ds is None:
                logger.info("[DownloadScheduler] dialog %d removed from sync, stopping download", dialog_id)
                return False
            if ds.sync_state != "active":
                logger.info("[DownloadScheduler] dialog %d state changed to %s, pausing download",
                            dialog_id, ds.sync_state)
                return False
            return True

        # 4. 进度回调
        async def progress_callback(current: int, did: int = dialog_id, dtitle: str = dialog_title) -> None:
            if self._progress_registry is None:
                return
            await self._progress_registry.update_progress(
                dialog_id=did,
                dialog_title=dtitle,
                current=current,
                total=0,
                status="downloading",
            )

        # 5. 计算断点
        offset_id = await asyncio.to_thread(self._config_store.get_latest_msg_id, dialog_id)

        async def latest_msg_id_setter(msg_id: int, did: int = dialog_id) -> None:
            await asyncio.to_thread(self._config_store.set_latest_msg_id, did, msg_id)

        # 5a. 是否有时间过滤（仅在首次下载，即 offset_id==0 时应用）
        offset_date: datetime | None = None
        if offset_id == 0 and dialog_state.date_from:
            try:
                offset_date = datetime.fromisoformat(dialog_state.date_from)
                if offset_date.tzinfo is None:
                    offset_date = offset_date.replace(tzinfo=timezone.utc)
                logger.info(
                    "[DownloadScheduler] applying date_from=%s for dialog %d",
                    dialog_state.date_from, dialog_id,
                )
            except ValueError:
                logger.warning(
                    "[DownloadScheduler] invalid date_from=%r for dialog %d, ignoring",
                    dialog_state.date_from, dialog_id,
                )

        # 6. 上报进度开始
        if self._progress_registry is not None:
            await self._progress_registry.update_progress(
                dialog_id=dialog_id,
                dialog_title=dialog_title,
                current=0,
                total=0,
                status="downloading",
            )

        logger.log(25, "[DownloadScheduler] starting download for %s (id=%d, offset=%d)",
                   dialog_title, dialog_id, offset_id)

        # 7. 执行下载
        try:
            await user_bot.download_history(
                peer,
                limit=None,
                offset_id=offset_id,
                offset_date=offset_date,
                dialog_id=dialog_id,
                progress_callback=progress_callback,
                state_checker=state_checker,
                latest_msg_id_setter=latest_msg_id_setter,
            )
            # 正常完成
            if self._progress_registry is not None:
                await self._progress_registry.complete_progress(dialog_id)
            logger.log(25, "[DownloadScheduler] download completed for %s (id=%d)", dialog_title, dialog_id)
        except DownloadPausedError:
            logger.info("[DownloadScheduler] download paused for %s (id=%d)", dialog_title, dialog_id)
            # 不标记失败，保留当前进度状态
        except Exception as exc:
            if self._progress_registry is not None:
                await self._progress_registry.fail_progress(dialog_id, str(exc))
            logger.error("[DownloadScheduler] download failed for dialog %d: %s: %s",
                         dialog_id, type(exc).__name__, exc)
