import asyncio
from Meilisearch4TelegramSearchCKJ.src.config.env import MEILI_HOST, MEILI_PASS, WHITE_LIST, BLACK_LIST
from Meilisearch4TelegramSearchCKJ.src.models.bot_handler import BotHandler
from Meilisearch4TelegramSearchCKJ.src.models.logger import setup_logger
from Meilisearch4TelegramSearchCKJ.src.models.meilisearch_handler import MeiliSearchClient
from Meilisearch4TelegramSearchCKJ.src.models.telegram_client_handler import TelegramUserBot
from Meilisearch4TelegramSearchCKJ.src.utils.record_lastest_msg_id import get_latest_msg_id, read_config

meili = MeiliSearchClient(MEILI_HOST, MEILI_PASS)
logger = setup_logger()


async def main():
    user_bot_client = TelegramUserBot(meili)
    try:
        await user_bot_client.start()
        logger.info("Bot started")
        config = read_config()
        logger.info("Reading latest message id from config")
        async for d in user_bot_client.client.iter_dialogs():
            # 便于获取对话的 id 和标题
            logger.log(25, f"Dialogs: {d.id}, {d.title if d.title else d }")
            if WHITE_LIST:
                if d.id in WHITE_LIST:
                    logger.info(f"Downloading history for {d.title or d.id}")
                    peer = await user_bot_client.client.get_entity(d.id)
                    await user_bot_client.download_history(peer, limit=None, offset_id=get_latest_msg_id(config, d.id))
            else:
                if d.id not in BLACK_LIST:
                    logger.info(f"Downloading history for {d.title or d.id}")
                    peer = await user_bot_client.client.get_entity(d.id)
                    await user_bot_client.download_history(peer, limit=None, offset_id=get_latest_msg_id(config, d.id))
        # 监控内存使用
        user_bot_client.get_memory_usage()

        # 保持运行
        await user_bot_client.client.run_until_disconnected()
    except Exception as e:
        logger.error(f"Error running bot: {str(e)}")
        if not isinstance(e, KeyboardInterrupt):
            if isinstance(e, ValueError):
                logger.error("Please check your environment variables “WHITE_LIST“ ")

    finally:
        await user_bot_client.cleanup()


async def run():
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(await main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    finally:
        loop.close()


if __name__ == "__main__":
    bot_handler = BotHandler(run)
    bot_handler.run()