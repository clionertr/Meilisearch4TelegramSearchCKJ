import asyncio

from tg_search.config.settings import MEILI_HOST, MEILI_PASS
from tg_search.core.logger import setup_logger
from tg_search.core.meilisearch import MeiliSearchClient
from tg_search.core.telegram import TelegramUserBot

meili = MeiliSearchClient(MEILI_HOST, MEILI_PASS)
logger = setup_logger()


async def main():
    bot = TelegramUserBot(meili)
    try:
        await bot.start()

        # 示例：下载特定聊天的历史消息
        #await bot.download_history('Qikan2023', limit=None)

        # 监控内存使用
        bot.get_memory_usage()

        # 保持运行
        await bot.client.run_until_disconnected()
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
