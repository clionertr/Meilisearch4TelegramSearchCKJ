"""Unit tests for DialogDownloadScheduler."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tg_search.config.config_store import DialogSyncState, GlobalConfig, SyncConfig
from tg_search.services.download_scheduler import (
    DialogDownloadScheduler,
    DownloadPausedError,
)

pytestmark = [pytest.mark.unit]


class FakeConfigStore:
    """In-memory ConfigStore stub."""

    def __init__(self, initial: GlobalConfig | None = None):
        self._config = initial or GlobalConfig()
        self._latest_msg_ids: dict[int, int] = {}

    def load_config(self, refresh: bool = False) -> GlobalConfig:
        return GlobalConfig.model_validate(self._config.model_dump())

    def get_latest_msg_id(self, dialog_id: int) -> int:
        return int(self._latest_msg_ids.get(dialog_id, 0))

    def set_latest_msg_id(self, dialog_id: int, latest_msg_id: int) -> None:
        self._latest_msg_ids[dialog_id] = int(latest_msg_id)


class FakeProgressRegistry:
    """Minimal progress registry stub."""

    def __init__(self):
        self.updates: list[dict] = []
        self.completed: list[int] = []
        self.failed: list[tuple[int, str]] = []

    async def update_progress(self, dialog_id, dialog_title, current, total, status):
        self.updates.append({"dialog_id": dialog_id, "current": current, "status": status})

    async def complete_progress(self, dialog_id):
        self.completed.append(dialog_id)

    async def fail_progress(self, dialog_id, error):
        self.failed.append((dialog_id, error))


# ── enqueue deduplication ──

@pytest.mark.asyncio
async def test_enqueue_deduplicates():
    """同一 dialog_id 不应重复入队。"""
    store = FakeConfigStore()
    scheduler = DialogDownloadScheduler(store, MagicMock(), None)

    assert await scheduler.enqueue(100) is True
    assert await scheduler.enqueue(100) is False  # 重复
    assert scheduler.pending_count == 1


@pytest.mark.asyncio
async def test_enqueue_rejects_currently_downloading():
    """正在下载的 dialog 不应再入队。"""
    store = FakeConfigStore()
    scheduler = DialogDownloadScheduler(store, MagicMock(), None)
    scheduler._current_dialog_id = 200

    assert await scheduler.enqueue(200) is False


# ── enqueue_all_active ──

@pytest.mark.asyncio
async def test_enqueue_all_active():
    """应自动入队所有 sync_state == active 的 dialog。"""
    initial = GlobalConfig(
        sync=SyncConfig(
            dialogs={
                "100": DialogSyncState(sync_state="active"),
                "200": DialogSyncState(sync_state="paused"),
                "300": DialogSyncState(sync_state="active"),
            }
        ),
    )
    store = FakeConfigStore(initial)
    scheduler = DialogDownloadScheduler(store, MagicMock(), None)

    count = await scheduler.enqueue_all_active()

    assert count == 2
    assert scheduler.pending_count == 2


# ── worker skips non-active dialogs ──

@pytest.mark.asyncio
async def test_worker_skips_paused_dialog():
    """Worker 取出 dialog 后如果已被 pause，应跳过不下载。"""
    initial = GlobalConfig(
        sync=SyncConfig(
            dialogs={
                "100": DialogSyncState(sync_state="paused"),
            }
        ),
    )
    store = FakeConfigStore(initial)
    progress = FakeProgressRegistry()
    scheduler = DialogDownloadScheduler(store, MagicMock(), progress)

    # 直接调用 _download_one 模拟 worker 处理
    fake_bot = MagicMock()
    scheduler._user_bot = fake_bot
    await scheduler._download_one(100)

    # 不应调用 download_history
    fake_bot.download_history.assert_not_called()
    # 不应上报完成
    assert len(progress.completed) == 0


# ── lifecycle ──

@pytest.mark.asyncio
async def test_start_stop():
    """Scheduler 应能正常启停。"""
    store = FakeConfigStore()
    scheduler = DialogDownloadScheduler(store, MagicMock(), None)

    # Start requires client to be set
    fake_bot = MagicMock()
    scheduler.set_client(fake_bot)

    await scheduler.start()
    assert scheduler.is_running

    await scheduler.stop()
    assert not scheduler.is_running


@pytest.mark.asyncio
async def test_start_idempotent():
    """重复 start 不应创建多个 worker。"""
    store = FakeConfigStore()
    scheduler = DialogDownloadScheduler(store, MagicMock(), None)
    scheduler.set_client(MagicMock())

    await scheduler.start()
    task1 = scheduler._worker_task

    await scheduler.start()
    task2 = scheduler._worker_task

    assert task1 is task2

    await scheduler.stop()


# ── DownloadPausedError ──

def test_download_paused_error_is_exception():
    """DownloadPausedError 应该是 Exception 子类。"""
    err = DownloadPausedError("test")
    assert isinstance(err, Exception)
    assert str(err) == "test"
