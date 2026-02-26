import asyncio
import os
from collections.abc import Awaitable
from typing import Any, cast

from tg_search.config.settings import (
    POLICY_REFRESH_TTL_SEC,
    validate_config,
)
from tg_search.core.bot import BotHandler
from tg_search.core.logger import setup_logger
from tg_search.core.meilisearch import MeiliSearchClient
from tg_search.core.telegram import TelegramUserBot
from tg_search.services.config_policy_service import ConfigPolicyService
from tg_search.services.container import ServiceContainer, build_service_container
from tg_search.utils.message_tracker import (
    get_latest_msg_id4_meili,
    read_config_from_meili,
)
from tg_search.utils.permissions import is_allowed

logger = setup_logger()


def _maybe_validate_config() -> None:
    if os.getenv("SKIP_CONFIG_VALIDATION", "").lower() in ("true", "1", "yes"):
        return
    validate_config()


async def download_and_listen(
    user_bot_client: TelegramUserBot,
    meili: MeiliSearchClient,
    policy_service: ConfigPolicyService,
    progress_registry: Any | None = None,
):
    try:
        policy = await policy_service.get_policy(refresh=True)
        white_list = policy.white_list
        black_list = policy.black_list
        latest_msg_config = read_config_from_meili(meili)
        logger.info("Reading policy and latest message id from stores")
        logger.log(25, f"Current white_list: {white_list}, black_list: {black_list}")
        tasks = []
        dialogs = await user_bot_client.client.get_dialogs()
        for d in dialogs:
            dialog_title = d.title or str(d.id)
            logger.log(25, f"Dialog discovered: {d.id} ({dialog_title})")
            if is_allowed(d.id, white_list, black_list):
                logger.log(25, f"Downloading history for {dialog_title}")
                peer = await user_bot_client.client.get_entity(d.id)

                dialog_id = d.id

                async def _progress(current: int, did: int = dialog_id, dtitle: str = dialog_title):
                    if progress_registry is None:
                        return
                    await progress_registry.update_progress(
                        dialog_id=did,
                        dialog_title=dtitle,
                        current=current,
                        total=0,
                        status="downloading",
                    )

                async def _download_one(p=peer, did: int = dialog_id, dtitle: str = dialog_title):
                    if progress_registry is not None:
                        await progress_registry.update_progress(
                            dialog_id=did,
                            dialog_title=dtitle,
                            current=0,
                            total=0,
                            status="downloading",
                        )
                    try:
                        await user_bot_client.download_history(
                            p,
                            limit=None,
                            offset_id=get_latest_msg_id4_meili(latest_msg_config, did),
                            latest_msg_config=latest_msg_config,
                            meili=meili,
                            dialog_id=did,
                            progress_callback=_progress,
                        )
                        if progress_registry is not None:
                            await progress_registry.complete_progress(did)
                    except Exception as e:
                        if progress_registry is not None:
                            await progress_registry.fail_progress(did, str(e))
                        raise

                tasks.append(_download_one())
        # 并行处理所有下载任务
        await asyncio.gather(*tasks)
        # 监控内存使用
        user_bot_client.get_memory_usage()
        logger.info("Finished downloading history, now listening for new messages...")
        await cast(Awaitable[None], user_bot_client.client.disconnected)
    except asyncio.CancelledError:
        logger.info("下载任务被取消")
    except Exception as e:
        logger.error(f"下载任务出错: {e}")


async def main(
    progress_registry: Any | None = None,
    *,
    services: ServiceContainer | None = None,
    on_ready: Any | None = None,
):
    _maybe_validate_config()

    service_container = services or build_service_container()
    meili = service_container.meili_client
    policy_service = service_container.config_policy_service

    async def _load_policy_lists() -> tuple[list[int], list[int]]:
        return await policy_service.get_policy_lists(refresh=True)

    user_bot_client = TelegramUserBot(
        meili,
        policy_loader=_load_policy_lists,
        policy_ttl_sec=POLICY_REFRESH_TTL_SEC,
    )
    unsubscribe_policy = policy_service.subscribe(
        lambda policy: user_bot_client.apply_policy_snapshot(policy.white_list, policy.black_list)
    )
    try:
        await user_bot_client.start()
        logger.info("User Bot started (policy_refresh_ttl_sec=%d)", POLICY_REFRESH_TTL_SEC)

        if on_ready is not None:
            try:
                if asyncio.iscoroutinefunction(on_ready):
                    await on_ready(user_bot_client.client)
                else:
                    on_ready(user_bot_client.client)
            except Exception as e:
                logger.error(f"Error calling on_ready callback: {e}")

        # 创建并运行下载和监听任务
        download_task = asyncio.create_task(
            download_and_listen(user_bot_client, meili, policy_service, progress_registry)
        )

        # 这里可以添加其他需要并行运行的任务

        # 等待下载和监听任务结束 (通常不会结束，除非客户端断开连接)
        await download_task

    except Exception as e:
        logger.error(f"Error running bot: {str(e)}")
    finally:
        unsubscribe_policy()
        await user_bot_client.cleanup()


async def run(
    progress_registry: Any | None = None,
    *,
    services: ServiceContainer | None = None,
    on_ready: Any | None = None,
):
    try:
        _maybe_validate_config()
        await main(progress_registry, services=services, on_ready=on_ready)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")


if __name__ == "__main__":
    _maybe_validate_config()
    services = build_service_container()
    bot_handler = BotHandler(lambda: run(services=services), services=services)
    asyncio.run(bot_handler.run())
