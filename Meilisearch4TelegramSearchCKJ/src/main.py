import asyncio
from Meilisearch4TelegramSearchCKJ.src.config.env import MEILI_HOST, MEILI_PASS, WHITE_LIST
from Meilisearch4TelegramSearchCKJ.src.models.logger import setup_logger
from Meilisearch4TelegramSearchCKJ.src.models.meilisearch_handler import MeiliSearchClient
from Meilisearch4TelegramSearchCKJ.src.models.telegram_client_handler import TelegramUserBot
from Meilisearch4TelegramSearchCKJ.src.utils.record_lastest_msg_id import get_latest_msg_id, read_config

meili = MeiliSearchClient(MEILI_HOST, MEILI_PASS)
logger = setup_logger()


async def main():
    bot = TelegramUserBot(meili)
    try:
        await bot.start()
        logger.info("Bot started")
        config = read_config()
        logger.info("Reading latest message id from config")
        async for d in bot.client.iter_dialogs():
            if d.id in WHITE_LIST:
                logger.info(f"Downloading history for {d.title or d.id}")
                peer = await bot.client.get_entity(d.id)
                await bot.download_history(peer, limit=None, offset_id=get_latest_msg_id(config, d.id))

        # 监控内存使用
        bot.get_memory_usage()

        # 保持运行
        await bot.client.run_until_disconnected()
    except Exception as e:
        logger.error(f"Error running bot: {str(e)}")
        if not isinstance(e, KeyboardInterrupt):
            if isinstance(e, ValueError):
                logger.error("Please check your environment variables “WHITE_LIST“ ")

    finally:
        await bot.cleanup()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    finally:
        loop.close()
