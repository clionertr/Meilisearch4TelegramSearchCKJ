import asyncio

import pytz
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.types import Message, ReactionCount, ReactionEmoji, ReactionCustomEmoji
from telethon.errors import FloodWaitError
import gc
import tracemalloc
from Meilisearch4TelegramSearchCKJ.src.config.env import APP_ID, APP_HASH, BATCH_MSG_UNM, NOT_RECORD_MSG, TIME_ZONE, \
    TELEGRAM_REACTIONS, IPv6, PROXY, SESSION_STRING, WHITE_LIST, BLACK_LIST
from Meilisearch4TelegramSearchCKJ.src.models.logger import setup_logger
from Meilisearch4TelegramSearchCKJ.src.utils.is_in_white_or_black_list import is_allowed
from Meilisearch4TelegramSearchCKJ.src.utils.record_lastest_msg_id import update_latest_msg_config4_meili, \
    read_config_from_meili
from telethon.tl.types import Channel, Chat, User

tz = pytz.timezone(TIME_ZONE)
logger = setup_logger()

# latest_msg_config = read_config()
#从config.ini获取最新消息ID

# 内存跟踪
tracemalloc.start()

async def calculate_reaction_score(reactions: dict) -> float|None:
    total_score = 0.0
    if reactions:
        for reaction, count in reactions.items():
            weight = TELEGRAM_REACTIONS.get(reaction, 0.0)
            total_score += count * weight
        return total_score
    else:
        return None


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


async def serialize_message(message:Message, not_edited=True):
    try:
        chat_future = message.get_chat()
        sender_future = message.get_sender()
        chat, sender = await asyncio.gather(chat_future, sender_future)
        reactions = await serialize_reactions(message)
        return {
            'id': f"{chat.id}-{message.id}" if not_edited else f"{chat.id}-{message.id}-{int(message.edit_date.timestamp())}",
            'chat': await serialize_chat(chat),
            'date': message.date.astimezone(tz).isoformat(),
            'text': message.text if hasattr(message, 'message') else message.caption if hasattr(message,
                                                                                                'caption') else None,
            'from_user': await serialize_sender(sender),
            'reactions': await serialize_reactions(message),
            'reactions_scores': await calculate_reaction_score(reactions)
            # 'raw': message.message
        }
    except Exception as e:
        logger.error(f"Error serializing message: {str(e)}")
        return None


class TelegramUserBot:
    def __init__(self, meili_client):
        """
        初始化 Telegram 客户端
        :param meili_client: MeiliSearch 客户端
        """
        # Telegram API 认证信息
        self.api_id = APP_ID
        self.api_hash = APP_HASH
        if SESSION_STRING:
            self.session = StringSession(SESSION_STRING)
        else:
            self.session = 'session/user_bot_session'

        self.meili = meili_client
        config = read_config_from_meili(self.meili)
        self.white_list = config.get("WHITE_LIST") or WHITE_LIST
        self.black_list = config.get("BLACK_LIST") or BLACK_LIST

        # 初始化客户端
        self.client = TelegramClient(
            self.session,
            self.api_id,
            self.api_hash,
            device_model="UserBot",
            system_version="1.0",
            app_version="1.0",
            lang_code="en",
            # 性能优化参数
            connection_retries=5,
            auto_reconnect=True,
            retry_delay=2,
            use_ipv6=IPv6,
            proxy=PROXY

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
                if is_allowed(peer_id, self.white_list, self.black_list):
                    await self._process_message(event.message)
                else:
                    logger.info(f"Chat id {peer_id} is not allowed")
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")

        @self.client.on(events.MessageEdited)
        async def handle_edit_message(event):
            peer_id = event.chat_id
            try:
                if is_allowed(peer_id, self.white_list, self.black_list):
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
    async def download_history(self, peer, limit=None, batch_size=BATCH_MSG_UNM, offset_id=0, offset_date=None,latest_msg_config=None,meili=None,dialog_id=None):
        """
        下载历史消息
        :param meili:
        :param latest_msg_config: 最新消息配置
        :param peer: 聊天实例
        :param limit: 限制下载消息数量
        :param batch_size: 批量下载大小
        :param offset_date:
        :param offset_id:
        """
        try:
            messages = []
            total_messages = 0

            async for message in self.client.iter_messages(
                    peer,
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
                    update_latest_msg_config4_meili(dialog_id, messages[-1], latest_msg_config,meili)
                    await self._process_message_batch(messages)
                    messages = []

                    # 垃圾回收
                    gc.collect()

                    logger.info(f"Downloaded {total_messages} messages")
                    self.get_memory_usage()

            # 处理剩余消息
            if messages:
                update_latest_msg_config4_meili(dialog_id, messages[-1], latest_msg_config,meili)
                await self._process_message_batch(messages)
                messages = []
                gc.collect()
                logger.log(25, f"Download completed for {peer.id}")

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
        logger.debug(f"Current memory usage: {current / 10 ** 6}MB")
        logger.debug(f"Peak memory usage: {peak / 10 ** 6}MB")
        return current, peak
