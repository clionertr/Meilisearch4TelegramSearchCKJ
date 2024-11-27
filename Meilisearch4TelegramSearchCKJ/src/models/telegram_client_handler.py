import json
import os
import logging
import asyncio
from datetime import datetime
from telethon import TelegramClient, events
from telethon.tl.types import Message
from telethon.errors import FloodWaitError
import gc
import tracemalloc
from Meilisearch4TelegramSearchCKJ.src.config.env import APP_ID, APP_HASH
from Meilisearch4TelegramSearchCKJ.src.utils.bridge import add_documents2meilisearch
from Meilisearch4TelegramSearchCKJ.src.models.logger import setup_logger
import json
from telethon.tl.types import (
    Message,
    Channel,
    Chat,
    User,
    MessageMediaPhoto,
    MessageMediaDocument,
    MessageService,
)

logger = setup_logger()

# 内存跟踪
tracemalloc.start()


class TelegramUserBot():
    def __init__(self):
        # Telegram API 认证信息
        self.api_id = APP_ID
        self.api_hash = APP_HASH
        self.session_name = 'user_bot_session'

        # 初始化客户端
        self.client = TelegramClient(
            self.session_name,
            self.api_id,
            self.api_hash,
            device_model="UserBot",
            system_version="1.0",
            app_version="1.0",
            lang_code="en",
            # 性能优化参数
            connection_retries=5,
            auto_reconnect=True,
            retry_delay=1
        )

        # 消息缓存，用于优化性能
        self.message_cache = {}
        self.cache_size_limit = 1000

    async def start(self):
        """启动客户端"""
        try:
            await self.client.start()
            logger.info("Bot started successfully")
            self.register_handlers()
        except Exception as e:
            logger.error(f"Failed to start bot: {str(e)}")
            raise

    def register_handlers(self):
        """注册消息处理器"""

        @self.client.on(events.NewMessage)
        async def handle_new_message(event):
            try:
                await self._process_message(event.message)
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")





    @staticmethod
    async def serialize_message(message):
        # 假设 serialize_message 是你的异步序列化函数
        chat = await message.get_chat()
        sender = await message.get_sender()
        return {
            'id': message.id,
            'chat': {
                'id': getattr(chat, 'id', None),
                'type': getattr(chat, 'megagroup', None) and 'supergroup' or 'private',
                'title': getattr(chat, 'title', None),
                'username': getattr(chat, 'username', None)
            } if chat else None,
            'date': message.date.isoformat() if message.date else None,
            'text': getattr(message, 'message', None),
            'from_user': {
                'id': getattr(sender, 'id', None),
                'username': getattr(sender, 'username', None)
            } if sender else None
        }

    async def _process_message(self, message: Message):
        """处理新消息"""
        try:
            # 消息处理逻辑
            if message.text:
                logger.info(f"Received message: {message.text[:100] if message.text else message.caption}")
                # 缓存消息
                await self._cache_message(message)
        except Exception as e:
            logger.error(f"Error in message processing: {str(e)}")

    async def _cache_message(self, message: Message):
        index = meili.client.index('telegram')
        result = index.add_documents([await self.serialize_message(message)])
        logger.info(f"Successfully added 1 documents to index 'telegram")
        logger.info(result)

    async def download_history(self, chat_id, limit=None, batch_size=100):
        """
        下载历史消息
        :param chat_id: 聊天ID
        :param limit: 限制下载消息数量
        :param batch_size: 批量下载大小
        """
        try:
            messages = []
            total_messages = 0

            async for message in self.client.iter_messages(
                    chat_id,
                    limit=limit,
                    reverse=True,
                    wait_time=1.4  # 防止请求过快
            ):
                messages.append(await self.serialize_message(message))

                total_messages += 1

                # 批量处理
                if len(messages) >= batch_size:
                    await self._process_message_batch(meili, messages)
                    messages = []

                    # 垃圾回收
                    gc.collect()

                logger.info(f"Downloaded {total_messages} messages")
                self.get_memory_usage()

            # 处理剩余消息
            if messages:
                await self._process_message_batch(meili, messages)
                messages = []
                gc.collect()
                logger.info("Download completed for s%ds" % chat_id)


        except FloodWaitError as e:
            logger.warning(f"Need to wait {e.seconds} seconds")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            logger.error(f"Error downloading history: {str(e)}")
            raise

    async def _process_message_batch(self, MeiliSearchClient, messages):
        """批量处理消息"""
        try:
            add_documents2meilisearch(MeiliSearchClient, messages)
            logger.info(f"Processing batch of {len(messages)} messages")
        except Exception as e:
            logger.error(f"Error processing message batch: {str(e)}")

    async def cleanup(self):
        """清理资源"""
        try:
            # 清空缓存
            self.message_cache.clear()

            # 断开连接
            await self.client.disconnect()

            # 强制垃圾回收
            gc.collect()

            logger.info("Cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

    def get_memory_usage(self):
        """获取内存使用情况"""
        current, peak = tracemalloc.get_traced_memory()
        logger.info(f"Current memory usage: {current / 10 ** 6}MB")
        logger.info(f"Peak memory usage: {peak / 10 ** 6}MB")
        return current, peak


async def main():
    bot = TelegramUserBot()
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


from Meilisearch4TelegramSearchCKJ.src.config.env import MEILI_HOST, MEILI_PASS
from Meilisearch4TelegramSearchCKJ.src.models.meilisearch_handler import MeiliSearchClient

meili = MeiliSearchClient(MEILI_HOST, MEILI_PASS)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    finally:
        loop.close()
