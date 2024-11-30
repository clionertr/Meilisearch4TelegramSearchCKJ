import asyncio

import pytz
from telethon import TelegramClient, events
from telethon.tl.types import Message, ReactionCount, ReactionEmoji, ReactionCustomEmoji
from telethon.errors import FloodWaitError
import gc
import tracemalloc
from Meilisearch4TelegramSearchCKJ.src.config.env import APP_ID, APP_HASH, BATCH_MSG_UNM, NOT_RECORD_MSG
from Meilisearch4TelegramSearchCKJ.src.models.logger import setup_logger
from Meilisearch4TelegramSearchCKJ.src.utils.is_in_white_or_black_list import is_allowed
from Meilisearch4TelegramSearchCKJ.src.utils.record_lastest_msg_id import read_config, write_config
from telethon.tl.types import Channel, Chat, User

tz = pytz.timezone('Asia/Shanghai')
logger = setup_logger()
latest_msg_config = read_config()

# 内存跟踪
tracemalloc.start()


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


async def serialize_reactions(message: Message):
    """
    获取消息对象的 reaction 表情和数量，并返回字典。

    Args:
        message: Telethon Message 对象。

    Returns:
        一个字典，键为 reaction 表情（Unicode 字符或 Document ID），值为 reaction 数量。
        如果消息没有 reaction，则返回空字典。
    """

    reactions_dict = {}

    if message.reactions:
        for reaction_count in message.reactions.results:
            if isinstance(reaction_count, ReactionCount):
                reaction = reaction_count.reaction
                count = reaction_count.count

                if isinstance(reaction, ReactionEmoji):
                    emoticon = reaction.emoticon
                    reactions_dict[emoticon] = count
                elif isinstance(reaction, ReactionCustomEmoji):
                    document_id = reaction.document_id
                    reactions_dict[document_id] = count
                else:
                    reactions_dict[f"Unknown Reaction Type: {type(reaction)}"] = count

    return reactions_dict if reactions_dict else None


async def serialize_message(message, not_edited=True):
    try:
        chat_future = message.get_chat()
        sender_future = message.get_sender()
        chat, sender = await asyncio.gather(chat_future, sender_future)
        return {
            'id': f"{chat.id}-{message.id}" if not_edited else f"{chat.id}-{message.id}-{int(message.edit_date.timestamp())}",
            'chat': await serialize_chat(chat),
            'date': message.date.astimezone(tz).isoformat(),
            'text': message.text if hasattr(message, 'message') else message.caption if hasattr(message,
                                                                                                'caption') else None,
            'from_user': await serialize_sender(sender),
            'reactions': await serialize_reactions(message),
            # 'raw': message.message
        }
    except Exception as e:
        logger.error(f"Error serializing message: {str(e)}")
        return None


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

        @self.client.on(events.MessageEdited)
        async def handle_edit_message(event):
            peer_id = event.chat_id
            try:
                if is_allowed(peer_id):
                    await self._process_message(event.message, NOT_RECORD_MSG)
                else:
                    logger.info(f"Chat id {peer_id} is not allowed")
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")

    async def _process_message(self, message: Message, not_edited=True):
        """处理新消息"""
        try:
            # 消息处理逻辑
            if message.text:
                logger.info(f"Received message: {message.text[:100] if message.text else message.caption}")
                # 缓存消息
                await self._cache_message(message, not_edited)
        except Exception as e:
            logger.error(f"Error in message processing for {message.id}: {str(e)}")

    async def _cache_message(self, message: Message, not_edited=True):
        try:
            result = self.meili.add_documents([await serialize_message(message, not_edited)])
            # logger.info(f"Successfully added 1 documents to index 'telegram")
            logger.info(result)
        except Exception as e:
            logger.error(f"Error caching message: {str(e)}")

    # @check_is_allowed()
    async def download_history(self, chat_id, limit=None, batch_size=BATCH_MSG_UNM, offset_id=0, offset_date=None):
        """
        下载历史消息
        :param chat_id: 聊天ID
        :param limit: 限制下载消息数量
        :param batch_size: 批量下载大小
        :param offset_date:
        :param offset_id:
        """
        try:
            messages = []
            total_messages = 0

            async for message in self.client.iter_messages(
                    chat_id,
                    offset_id=offset_id,
                    offset_date=offset_date,
                    limit=limit,
                    reverse=True,
                    #wait_time=1.4  # 防止请求过快
            ):
                messages.append(await serialize_message(message))

                total_messages += 1

                # 批量处理
                if len(messages) >= batch_size:
                    latest_msg_config["latest_msg_id"][str(chat_id)] = str(message.id)
                    latest_msg_config["latest_msg_date"][str(chat_id)] = str(message.date.timestamp())
                    write_config(latest_msg_config)
                    await self._process_message_batch(messages)
                    messages = []

                    # 垃圾回收
                    gc.collect()

                    logger.info(f"Downloaded {total_messages} messages")
                    self.get_memory_usage()

            # 处理剩余消息
            if messages:
                latest_msg_config["latest_msg_id"][str(chat_id)] = str(messages[-1]["id"].split('-')[1])
                latest_msg_config["latest_msg_date"][str(chat_id)] = str(messages[-1]["date"])
                write_config(latest_msg_config)
                await self._process_message_batch(messages)
                messages = []
                gc.collect()
                logger.log(25, f"Download completed for {chat_id}")

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
