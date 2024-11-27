import asyncio
from telethon import TelegramClient, events
from telethon.tl.types import Message
from telethon.errors import FloodWaitError
import gc
import tracemalloc
from Meilisearch4TelegramSearchCKJ.src.config.env import APP_ID, APP_HASH
from Meilisearch4TelegramSearchCKJ.src.models.logger import setup_logger
from Meilisearch4TelegramSearchCKJ.src.utils.is_in_white_or_black_list import is_allowed, check_is_allowed

logger = setup_logger()

# 内存跟踪
tracemalloc.start()

import asyncio
from telethon.tl.types import Channel, Chat, User


async def serialize_chat(chat):
    if not chat:
        return None
    chat_type = None
    if isinstance(chat, Channel):
        chat_type = "channel"
    elif isinstance(chat, Chat):
        chat_type = "group"
    elif isinstance(chat, User):
        chat_type = "private"
    return {
        'id': chat.id,
        'type': chat_type,
        'title': chat.title if hasattr(chat, 'title') else None,
        'username': chat.username if hasattr(chat, 'username') else None
    }


async def serialize_sender(sender):
    if not sender:
        return None
    return {
        'id': sender.id,
        'username': sender.username if hasattr(sender, 'username') else None
    }


async def serialize_message(message):
    chat_future = message.get_chat()
    sender_future = message.get_sender()
    chat, sender = await asyncio.gather(chat_future, sender_future)
    return {
        'id': f"{chat.id}-{message.id}" if chat else None,
        'chat': await serialize_chat(chat),
        'date': message.date.isoformat() if message.date else None,
        'text': message.text if hasattr(message, 'message') else message.caption if hasattr(message,
                                                                                            'caption') else None,
        'from_user': await serialize_sender(sender),
        # 'raw': str(message)
    }


class TelegramUserBot:
    def __init__(self, MeiliClient):
        """
        初始化 Telegram 客户端
        :param MeiliClient: MeiliSearch 客户端
        """
        # Telegram API 认证信息
        self.api_id = APP_ID
        self.api_hash = APP_HASH
        self.session_name = 'session/user_bot_session'

        self.meili = MeiliClient

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
            peer_id = event.chat_id
            try:
                if is_allowed(peer_id):
                    await self._process_message(event.message)
                else:
                    logger.info(f"Chat id {peer_id} is not allowed")
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")

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
        result = self.meili.add_documents([await serialize_message(message)])
        # logger.info(f"Successfully added 1 documents to index 'telegram")
        logger.info(result)

    # @check_is_allowed()
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
                messages.append(await serialize_message(message))

                total_messages += 1

                # 批量处理
                if len(messages) >= batch_size:
                    await self._process_message_batch(messages)
                    messages = []

                    # 垃圾回收
                    gc.collect()

                logger.info(f"Downloaded {total_messages} messages")
                self.get_memory_usage()

            # 处理剩余消息
            if messages:
                await self._process_message_batch(messages)
                messages = []
                gc.collect()
                logger.info(f"Download completed for {chat_id}")

        except FloodWaitError as e:
            logger.warning(f"Need to wait {e.seconds} seconds")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            logger.error(f"Error downloading history: {str(e)}")
            raise

    async def _process_message_batch(self, messages):
        """批量处理消息"""
        try:
            self.meili.add_documents(messages)
            logger.info(f"Processing batch of {len(messages)} messages")
        except Exception as e:
            logger.error(f"Error processing message batch: {str(e)}")

    async def cleanup(self):
        """清理资源"""
        try:

            # 断开连接
            await self.client.disconnect()

            # 强制垃圾回收
            gc.collect()

            logger.info("Cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

    @staticmethod
    def get_memory_usage():
        """获取内存使用情况"""
        current, peak = tracemalloc.get_traced_memory()
        logger.info(f"Current memory usage: {current / 10 ** 6}MB")
        logger.info(f"Peak memory usage: {peak / 10 ** 6}MB")
        return current, peak
