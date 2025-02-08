import asyncio

from Meilisearch4TelegramSearchCKJ.src.models.meilisearch_handler import MeiliSearchClient
from Meilisearch4TelegramSearchCKJ.src.models.logger import setup_logger
from Meilisearch4TelegramSearchCKJ.src.models.telegram_client_handler import TelegramUserBot
from Meilisearch4TelegramSearchCKJ.src.config.env import MEILI_HOST, MEILI_PASS, WHITE_LIST, BLACK_LIST
from Meilisearch4TelegramSearchCKJ.src.utils.record_lastest_msg_id import get_latest_msg_id4_meili, \
    read_config_from_meili

logger = setup_logger()
meili = MeiliSearchClient(MEILI_HOST, MEILI_PASS)


# !
async def download_and_listen():
    user_bot_client = TelegramUserBot(meili)
    try:
        await user_bot_client.start()
        logger.info("UserBot 已启动")
        config = read_config_from_meili(meili)
        white_list = config.get("WHITE_LIST") or WHITE_LIST
        black_list = config.get("BLACK_LIST") or BLACK_LIST
        logger.info(f"当前白名单: {config.get('WHITE_LIST', WHITE_LIST)}")
        tasks = []
        async for dialog in user_bot_client.client.iter_dialogs():
            logger.info(f"处理 Dialog: {dialog.id}, {dialog.title or "被删除的账户"}")  # !
            # 判断是否下载（白名单优先，黑名单过滤）
            if (white_list and dialog.id in white_list) or \
               (not white_list and dialog.id not in black_list):
                peer = await user_bot_client.client.get_entity(dialog.id)
                offset_id = get_latest_msg_id4_meili(config, dialog.id)
                tasks.append(user_bot_client.download_history(peer, limit=None, offset_id=offset_id,
                                                              latest_msg_config=config, meili=meili, dialog_id=dialog.id))
        if tasks:
            await asyncio.gather(*tasks)
        logger.info("历史消息下载完成，开始监听新消息...")
        await user_bot_client.client.run_until_disconnected()
    except asyncio.CancelledError:
        logger.info("下载任务被取消")
    except Exception as e:
        logger.error(f"运行出错: {e}")
    finally:
        await user_bot_client.cleanup()


async def main():
    await download_and_listen()


if __name__ == "__main__":
    from Meilisearch4TelegramSearchCKJ.src.models.bot_handler import BotHandler
    bot_handler = BotHandler(main)
    try:
        asyncio.run(bot_handler.run())
    except KeyboardInterrupt:
        logger.info("程序被用户中断")