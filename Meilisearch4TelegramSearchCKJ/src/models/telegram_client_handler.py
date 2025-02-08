import asyncio
import gc
import tracemalloc
import pytz

from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
from telethon.sessions import StringSession
from telethon.tl.types import Channel, Chat, User, Message, ReactionCount, ReactionEmoji, ReactionCustomEmoji

from Meilisearch4TelegramSearchCKJ.src.config.env import APP_ID, APP_HASH, BATCH_MSG_UNM, NOT_RECORD_MSG, TIME_ZONE, \
    TELEGRAM_REACTIONS, IPv6, PROXY, SESSION_STRING, WHITE_LIST, BLACK_LIST
from Meilisearch4TelegramSearchCKJ.src.models.logger import setup_logger
from Meilisearch4TelegramSearchCKJ.src.utils.is_in_white_or_black_list import is_allowed
from Meilisearch4TelegramSearchCKJ.src.utils.record_lastest_msg_id import update_latest_msg_config4_meili, read_config_from_meili

tz = pytz.timezone(TIME_ZONE)
logger = setup_logger()

# 开启内存跟踪
tracemalloc.start()


async def calculate_reaction_score(reactions: dict) -> float | None:
    total_score = 0.0
    if reactions:
        for reaction, count in reactions.items():
            weight = TELEGRAM_REACTIONS.get(reaction, 0.0)
            total_score += count * weight
        return total_score
    return None


async def serialize_chat(chat):
    if not chat:
        return None
    chat_type = "private"
    if hasattr(chat, 'megagroup') and chat.megagroup:
        chat_type = "group"
    elif isinstance(chat, Channel):
        chat_type = "channel"
    elif isinstance(chat, Chat):
        chat_type = "group"
    return {
        'id': chat.id,
        'type': chat_type,
        'title': getattr(chat, 'title', None),
        'username': getattr(chat, 'username', None)
    }


async def serialize_sender(sender):
    if not sender:
        return None
    return {
        'id': sender.id,
        'username': getattr(sender, 'username', None)
    }


async def serialize_reactions(message: Message):
    """获取消息对象的 reaction 表情和数量，并返回字典。"""
    reactions_dict = {}
    if message.reactions:
        for reaction_count in message.reactions.results:
            if isinstance(reaction_count, ReactionCount):
                reaction = reaction_count.reaction
                count = reaction_count.count
                if isinstance(reaction, ReactionEmoji):
                    reactions_dict[reaction.emoticon] = count
                elif isinstance(reaction, ReactionCustomEmoji):
                    reactions_dict[reaction.document_id] = count
                else:
                    reactions_dict[f"Unknown:{type(reaction)}"] = count
    return reactions_dict if reactions_dict else None


async def serialize_message(message: Message, not_edited=True):
    try:
        # 并行获取 chat 与 sender
        chat, sender = await asyncio.gather(message.get_chat(), message.get_sender())
        reactions = await serialize_reactions(message)
        reaction_score = await calculate_reaction_score(reactions)
        return {
            'id': f"{chat.id}-{message.id}" if not_edited else f"{chat.id}-{message.id}-{int(message.edit_date.timestamp())}",
            'chat': await serialize_chat(chat),
            'date': message.date.astimezone(tz).isoformat(),
            'text': getattr(message, 'text', None) or getattr(message, 'caption', None),
            'from_user': await serialize_sender(sender),
            'reactions': reactions,
            'reactions_scores': reaction_score,
            'text_len': len(getattr(message, 'text', '') or '')
        }
    except Exception as e:
        logger.error(f"Error serializing message (id: {getattr(message, 'id', 'unknown')}): {e}")
        return None


class TelegramUserBot:
    def __init__(self, meili_client):
        self.api_id = APP_ID
        self.api_hash = APP_HASH
        self.session = StringSession(SESSION_STRING) if SESSION_STRING else 'session/user_bot_session'
        self.meili = meili_client
        config = read_config_from_meili(self.meili)
        self.white_list = config.get("WHITE_LIST") or WHITE_LIST
        self.black_list = config.get("BLACK_LIST") or BLACK_LIST

        self.client = TelegramClient(
            self.session,
            self.api_id,
            self.api_hash,
            device_model="UserBot",
            system_version="1.0",
            app_version="1.0",
            lang_code="en",
            connection_retries=5,
            auto_reconnect=True,
            retry_delay=2,
            use_ipv6=IPv6,
            proxy=PROXY
        )
        # 限制缓存大小
        self.cache_size_limit = 1000

    async def start(self):
        try:
            await self.client.start()
            logger.info("UserBot 启动成功")
            self.register_handlers()
        except Exception as e:
            logger.error(f"启动 bot 失败: {e}")
            raise

    def register_handlers(self):
        @self.client.on(events.NewMessage)
        async def handle_new_message(event):
            peer_id = event.chat_id
            try:
                if is_allowed(peer_id, self.white_list, self.black_list):
                    await self._process_message(event.message)
                else:
                    logger.info(f"Chat id {peer_id} 不在允许列表内")
            except Exception as e:
                logger.error(f"处理消息错误: {e}")

        @self.client.on(events.MessageEdited)
        async def handle_edit_message(event):
            peer_id = event.chat_id
            try:
                if is_allowed(peer_id, self.white_list, self.black_list):
                    await self._process_message(event.message, NOT_RECORD_MSG)
                else:
                    logger.info(f"Chat id {peer_id} 不在允许列表内")
            except Exception as e:
                logger.error(f"处理编辑消息错误: {e}")

    async def _process_message(self, message, not_edited=True):
        try:
            if message.text or getattr(message, 'caption', None):
                logger.info(f"收到消息: {message.text[:100] if message.text else message.caption}")
                await self._cache_message(message, not_edited)
        except Exception as e:
            logger.error(f"处理消息 id {message.id} 出错: {e}")

    async def _cache_message(self, message, not_edited=True):
        try:
            doc = await serialize_message(message, not_edited)
            if doc:
                result = self.meili.add_documents([doc])
                logger.info(f"缓存消息结果: {result}")
        except Exception as e:
            logger.error(f"缓存消息出错: {e}")

    async def download_history(self, peer, limit=None, batch_size=BATCH_MSG_UNM, offset_id=0, offset_date=None,
                               latest_msg_config=None, meili=None, dialog_id=None):
        try:
            messages = []
            total_messages = 0
            async for message in self.client.iter_messages(
                    peer,
                    offset_id=offset_id,
                    offset_date=offset_date,
                    limit=limit,
                    reverse=True,
                    # wait_time=1.4  # 防止请求过快
            ):
                serialized = await serialize_message(message)
                if serialized:
                    messages.append(serialized)
                    total_messages += 1
                if len(messages) >= batch_size:
                    update_latest_msg_config4_meili(dialog_id, messages[-1], latest_msg_config, meili)
                    await self._process_message_batch(messages)
                    messages.clear()
                    logger.info(f"已下载 {total_messages} 条消息")
            if messages:
                update_latest_msg_config4_meili(dialog_id, messages[-1], latest_msg_config, meili)
                await self._process_message_batch(messages)
                logger.info(f"完成下载 {peer.id} 的历史消息")
        except FloodWaitError as e:
            logger.warning(f"等待 {e.seconds} 秒后重试")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            logger.error(f"下载历史消息出错: {e}")
            raise

    async def _process_message_batch(self, messages):
        try:
            self.meili.add_documents(messages)
            logger.info(f"处理批量消息 {len(messages)} 条")
        except Exception as e:
            logger.error(f"处理消息批量出错: {e}")

    async def cleanup(self):
        try:
            await self.client.disconnect()
            gc.collect()
            logger.info("清理工作完成")
        except Exception as e:
            logger.error(f"清理资源时出错: {e}")

    @staticmethod
    def get_memory_usage():
        current, peak = tracemalloc.get_traced_memory()
        logger.debug(f"当前内存: {current / 10 ** 6:.2f}MB, 峰值内存: {peak / 10 ** 6:.2f}MB")
        return current, peak