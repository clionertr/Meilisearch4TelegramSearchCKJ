import asyncio
from Meilisearch4TelegramSearchCKJ.src.config.env import MEILI_HOST, MEILI_PASS, WHITE_LIST, BLACK_LIST
from Meilisearch4TelegramSearchCKJ.src.models.bot_handler import BotHandler
from Meilisearch4TelegramSearchCKJ.src.models.logger import setup_logger
from Meilisearch4TelegramSearchCKJ.src.models.meilisearch_handler import MeiliSearchClient
from Meilisearch4TelegramSearchCKJ.src.models.telegram_client_handler import TelegramUserBot
from Meilisearch4TelegramSearchCKJ.src.utils.record_lastest_msg_id import get_latest_msg_id, read_config, \
    get_latest_msg_id4_meili, read_config_from_meili

meili = MeiliSearchClient(MEILI_HOST, MEILI_PASS)
logger = setup_logger()


async def download_and_listen(user_bot_client: TelegramUserBot):
    try:
        config = read_config_from_meili(meili)
        white_list = config.get("WHITE_LIST") or WHITE_LIST
        black_list = config.get("BLACK_LIST") or BLACK_LIST
        logger.info("Reading latest message id from config")
        logger.log(25, f"Current white_list: {white_list}, black_list: {black_list}")
        tasks = []
        async for d in user_bot_client.client.iter_dialogs():
            logger.log(25, f"Dialogs: {d.id}, {d.title if d.title else d}")
            if (white_list and d.id in white_list) or (not white_list and d.id not in black_list):
                logger.log(25, f"Downloading history for {d.title or d.id}")
                peer = await user_bot_client.client.get_entity(d.id)
                tasks.append(
                    user_bot_client.download_history(peer, limit=None, offset_id=get_latest_msg_id4_meili(config, d.id),
                                                     latest_msg_config=config, meili=meili, dialog_id=d.id))
        # 并行处理所有下载任务
        await asyncio.gather(*tasks)
        # 监控内存使用
        user_bot_client.get_memory_usage()
        logger.info("Finished downloading history, now listening for new messages...")
        await user_bot_client.client.run_until_disconnected()
    except asyncio.CancelledError:
        logger.info("下载任务被取消")
    except Exception as e:
        logger.error(f"下载任务出错: {e}")


async def main():
    user_bot_client = TelegramUserBot(meili)
    try:
        await user_bot_client.start()
        logger.info("User Bot started")

        # 创建并运行下载和监听任务
        download_task = asyncio.create_task(download_and_listen(user_bot_client))

        # 这里可以添加其他需要并行运行的任务

        # 等待下载和监听任务结束 (通常不会结束，除非客户端断开连接)
        await download_task

    except Exception as e:
        logger.error(f"Error running bot: {str(e)}")
        if not isinstance(e, KeyboardInterrupt):
            if isinstance(e, ValueError):
                logger.error("Please check your environment variables “WHITE_LIST“ ")
    finally:
        await user_bot_client.cleanup()


async def run():
    try:
        await main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")


if __name__ == "__main__":
    bot_handler = BotHandler(run)
    asyncio.run(bot_handler.run())
