import asyncio

from tg_search.config.settings import MEILI_HOST, MEILI_PASS
from tg_search.core.logger import setup_logger
from tg_search.core.meilisearch import MeiliSearchClient
from tg_search.core.telegram import TelegramUserBot

logger = setup_logger(__name__)


async def main() -> None:
    # This is a manual demo script, not a unit test.
    meili = MeiliSearchClient(MEILI_HOST, MEILI_PASS)
    bot = TelegramUserBot(meili)
    try:
        await bot.start()
        bot.get_memory_usage()
        await bot.client.run_until_disconnected()
    finally:
        await bot.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
