"""
Telegram 客户端封装

提供 Telegram 用户客户端功能，包含：
- 消息下载与监听
- 细化的异常处理（区分网络/权限/限流错误）
- 内存使用监控
"""

import asyncio
import gc
import os
import tracemalloc
from collections.abc import Awaitable, Callable
from typing import Any, cast

import pytz
from telethon import TelegramClient, events
from telethon.errors import (
    ChannelPrivateError,
    # 权限相关错误
    ChatAdminRequiredError,
    ChatWriteForbiddenError,
    FloodWaitError,
    # RPC 错误基类
    RPCError,
    # 网络相关错误
    TimedOutError,
    UserBannedInChannelError,
    UserPrivacyRestrictedError,
)
from telethon.errors import (
    TimeoutError as TelethonTimeoutError,
)
from telethon.sessions import StringSession
from telethon.tl.types import Channel, Chat, Message, ReactionCount, ReactionCustomEmoji, ReactionEmoji, User

from tg_search.config.settings import (
    APP_HASH,
    APP_ID,
    BATCH_MSG_UNM,
    BLACK_LIST,
    NOT_RECORD_MSG,
    PROXY,
    SESSION_STRING,
    TELEGRAM_REACTIONS,
    TIME_ZONE,
    WHITE_LIST,
    IPv6,
)
from tg_search.core.logger import setup_logger
from tg_search.utils.message_tracker import (
    read_config_from_meili,
    update_latest_msg_config4_meili,
)
from tg_search.utils.permissions import is_allowed

tz = pytz.timezone(TIME_ZONE)
logger = setup_logger()

# 是否启用内存跟踪（生产环境可关闭以提升性能）
_ENABLE_TRACEMALLOC = os.getenv("ENABLE_TRACEMALLOC", "true").lower() in ("true", "1", "yes")
if _ENABLE_TRACEMALLOC:
    tracemalloc.start()


# ============ 自定义异常 ============


class TelegramNetworkError(Exception):
    """Telegram 网络错误（可重试）"""

    pass


class TelegramPermissionError(Exception):
    """Telegram 权限错误（不可重试，需跳过）"""

    pass


class TelegramRateLimitError(Exception):
    """Telegram 限流错误（需等待后重试）"""

    def __init__(self, message: str, wait_seconds: int = 0):
        super().__init__(message)
        self.wait_seconds = wait_seconds


# ============ 权限错误类型集合 ============

PERMISSION_ERRORS = (
    ChatAdminRequiredError,
    ChannelPrivateError,
    UserPrivacyRestrictedError,
    ChatWriteForbiddenError,
    UserBannedInChannelError,
)

# ============ 网络错误类型集合 ============

NETWORK_ERRORS = (
    TimedOutError,
    TelethonTimeoutError,
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
    OSError,
)


async def calculate_reaction_score(reactions: dict | None) -> float | None:
    total_score = 0.0
    if reactions:
        for reaction, count in reactions.items():
            weight = TELEGRAM_REACTIONS.get(reaction, 0.0)
            total_score += count * weight
        return total_score
    else:
        return None


async def serialize_chat(chat: Channel | Chat | User | None) -> dict[str, Any] | None:
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
        "id": chat.id,
        "type": chat_type,
        "title": getattr(chat, "title", None),
        "username": getattr(chat, "username", None),
    }


async def serialize_sender(sender: User | None) -> dict[str, Any] | None:
    if not sender:
        return None
    return {"id": sender.id, "username": getattr(sender, "username", None)}


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


async def serialize_message(message: Any, not_edited: bool = True) -> dict | None:
    """
    序列化 Telegram 消息为字典

    Args:
        message: Telethon Message 对象
        not_edited: 是否为原始消息（非编辑版本）

    Returns:
        序列化后的消息字典，失败返回 None
    """
    try:
        chat_future = cast(Awaitable[Any], message.get_chat())
        sender_future = cast(Awaitable[Any], message.get_sender())
        chat, sender = await asyncio.gather(chat_future, sender_future)

        chat_id = getattr(chat, "id", None)
        msg_id = getattr(message, "id", None)
        msg_date = getattr(message, "date", None)
        if chat_id is None or msg_id is None or msg_date is None:
            return None

        reactions = await serialize_reactions(message)
        edit_date = getattr(message, "edit_date", None)
        edit_ts = int(edit_date.timestamp()) if edit_date else 0
        text = getattr(message, "text", None) or getattr(message, "caption", None)
        return {
            "id": f"{chat_id}-{msg_id}" if not_edited else f"{chat_id}-{msg_id}-{edit_ts}",
            "chat": await serialize_chat(chat),
            "date": msg_date.astimezone(tz).isoformat(),
            "text": text,
            "from_user": await serialize_sender(sender),
            "reactions": reactions,
            "reactions_scores": await calculate_reaction_score(reactions),
            "text_len": len(text or ""),
        }
    except NETWORK_ERRORS as e:
        logger.warning(f"Network error serializing message {message.id}: {type(e).__name__}: {str(e)}")
        return None
    except PERMISSION_ERRORS as e:
        logger.warning(f"Permission error serializing message {message.id}: {type(e).__name__}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error serializing message {message.id}: {type(e).__name__}: {str(e)}")
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
            self.session = "session/user_bot_session"

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
            proxy=cast(Any, PROXY),
        )

        # 消息缓存，用于优化性能
        self.cache_size_limit = 1000

    async def start(self):
        """启动客户端"""
        try:
            await cast(Awaitable[Any], self.client.start())
            logger.info("Bot started successfully")
            self.register_handlers()
        except FloodWaitError as e:
            logger.error(f"Rate limited on start, need to wait {e.seconds} seconds")
            raise TelegramRateLimitError(f"限流，需等待 {e.seconds} 秒", e.seconds) from e
        except NETWORK_ERRORS as e:
            logger.error(f"Network error starting bot: {type(e).__name__}: {str(e)}")
            raise TelegramNetworkError(f"网络错误: {str(e)}") from e
        except PERMISSION_ERRORS as e:
            logger.error(f"Permission error starting bot: {type(e).__name__}: {str(e)}")
            raise TelegramPermissionError(f"权限错误: {str(e)}") from e
        except RPCError as e:
            logger.error(f"RPC error starting bot: {type(e).__name__}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Failed to start bot: {type(e).__name__}: {str(e)}")
            raise

    def register_handlers(self):
        """注册消息处理器"""

        @self.client.on(cast(Any, events.NewMessage))
        async def handle_new_message(event):
            peer_id = event.chat_id
            try:
                if is_allowed(peer_id, self.white_list, self.black_list):
                    await self._process_message(event.message)
                else:
                    logger.debug(f"Chat id {peer_id} is not allowed")
            except FloodWaitError as e:
                logger.warning(f"Rate limited processing message, waiting {e.seconds}s")
                await asyncio.sleep(e.seconds)
            except NETWORK_ERRORS as e:
                logger.warning(f"Network error processing message: {type(e).__name__}")
            except PERMISSION_ERRORS as e:
                logger.warning(f"Permission denied for chat {peer_id}: {type(e).__name__}")
            except Exception as e:
                logger.error(f"Error processing message: {type(e).__name__}: {str(e)}")

        @self.client.on(cast(Any, events.MessageEdited))
        async def handle_edit_message(event):
            peer_id = event.chat_id
            try:
                if is_allowed(peer_id, self.white_list, self.black_list):
                    await self._process_message(event.message, NOT_RECORD_MSG)
                else:
                    logger.debug(f"Chat id {peer_id} is not allowed")
            except FloodWaitError as e:
                logger.warning(f"Rate limited processing edit, waiting {e.seconds}s")
                await asyncio.sleep(e.seconds)
            except NETWORK_ERRORS as e:
                logger.warning(f"Network error processing edit: {type(e).__name__}")
            except PERMISSION_ERRORS as e:
                logger.warning(f"Permission denied for chat {peer_id}: {type(e).__name__}")
            except Exception as e:
                logger.error(f"Error processing message edit: {type(e).__name__}: {str(e)}")

    async def _process_message(self, message: Any, not_edited: bool = True):
        """处理新消息"""
        try:
            # 消息处理逻辑
            text = getattr(message, "text", None)
            caption = getattr(message, "caption", None)
            if text or caption:
                preview = (text or caption or "")[:100]
                logger.info(f"Received message: {preview}")
                # 缓存消息
                await self._cache_message(message, not_edited)
        except NETWORK_ERRORS as e:
            logger.warning(f"Network error processing message {message.id}: {type(e).__name__}")
        except Exception as e:
            logger.error(f"Error in message processing for {message.id}: {type(e).__name__}: {str(e)}")

    async def _cache_message(self, message: Any, not_edited: bool = True):
        """缓存消息到 MeiliSearch"""
        try:
            serialized = await serialize_message(message, not_edited)
            if serialized:
                result = await asyncio.to_thread(self.meili.add_documents, [serialized])
                logger.info(result)
        except NETWORK_ERRORS as e:
            logger.warning(f"Network error caching message {message.id}: {type(e).__name__}")
        except Exception as e:
            logger.error(f"Error caching message {message.id}: {type(e).__name__}: {str(e)}")

    # @check_is_allowed()
    async def download_history(
        self,
        peer,
        limit=None,
        batch_size=BATCH_MSG_UNM,
        offset_id=0,
        offset_date=None,
        latest_msg_config=None,
        meili=None,
        dialog_id=None,
        progress_callback: Callable[[int], Awaitable[None]] | None = None,
    ):
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
            last_seen_marker = None
            total_messages = 0

            async for message in self.client.iter_messages(
                peer,
                offset_id=offset_id,
                offset_date=offset_date,
                limit=cast(Any, limit),
                reverse=True,
                # wait_time=1.4  # 防止请求过快
            ):
                # 用于记录增量位置：即使序列化失败，也应推进 offset，避免下次重复下载
                if dialog_id is not None:
                    last_seen_marker = {"id": f"{dialog_id}-{message.id}"}

                serialized = await serialize_message(message)
                if serialized is not None:
                    messages.append(serialized)

                total_messages += 1

                # 批量处理
                if len(messages) >= batch_size:
                    if last_seen_marker is not None and latest_msg_config is not None and meili is not None:
                        await update_latest_msg_config4_meili(dialog_id, last_seen_marker, latest_msg_config, meili)
                    await self._process_message_batch(messages)
                    messages = []

                    # 垃圾回收
                    gc.collect()

                    logger.info(f"Downloaded {total_messages} messages")
                    self.get_memory_usage()
                    if progress_callback is not None:
                        await progress_callback(total_messages)

            # 处理剩余消息
            if messages:
                if last_seen_marker is not None and latest_msg_config is not None and meili is not None:
                    await update_latest_msg_config4_meili(dialog_id, last_seen_marker, latest_msg_config, meili)
                await self._process_message_batch(messages)
                messages = []
                gc.collect()
                logger.log(25, f"Download completed for {peer.id}")
                if progress_callback is not None:
                    await progress_callback(total_messages)
            elif last_seen_marker is not None and latest_msg_config is not None and meili is not None:
                await update_latest_msg_config4_meili(dialog_id, last_seen_marker, latest_msg_config, meili)
                if progress_callback is not None:
                    await progress_callback(total_messages)
            elif progress_callback is not None:
                await progress_callback(total_messages)

        except FloodWaitError as e:
            logger.warning(f"Rate limited, need to wait {e.seconds} seconds")
            await asyncio.sleep(e.seconds)
            # 等待后继续（递归调用可能导致栈溢出，这里选择让调用者重试）
        except NETWORK_ERRORS as e:
            logger.error(f"Network error downloading history: {type(e).__name__}: {str(e)}")
            raise TelegramNetworkError(f"网络错误: {str(e)}") from e
        except PERMISSION_ERRORS as e:
            logger.error(f"Permission denied downloading history from {peer}: {type(e).__name__}")
            raise TelegramPermissionError(f"权限错误: {str(e)}") from e
        except Exception as e:
            logger.error(f"Error downloading history: {type(e).__name__}: {str(e)}")
            raise

    async def _process_message_batch(self, messages: list):
        """批量处理消息"""
        # 过滤掉 None 值
        valid_messages = [m for m in messages if m is not None]
        if not valid_messages:
            return

        try:
            await asyncio.to_thread(self.meili.add_documents, valid_messages)
            logger.info(f"Processing batch of {len(valid_messages)} messages")
        except NETWORK_ERRORS as e:
            logger.warning(f"Network error processing batch: {type(e).__name__}")
        except Exception as e:
            logger.error(f"Error processing message batch: {type(e).__name__}: {str(e)}")

    async def cleanup(self):
        """清理资源"""
        try:
            # 断开连接
            await cast(Awaitable[Any], self.client.disconnect())

            # 强制垃圾回收
            gc.collect()

            logger.info("Cleanup completed")
        except NETWORK_ERRORS as e:
            logger.warning(f"Network error during cleanup: {type(e).__name__}")
        except Exception as e:
            logger.error(f"Error during cleanup: {type(e).__name__}: {str(e)}")

    @staticmethod
    def get_memory_usage():
        """获取内存使用情况"""
        current, peak = tracemalloc.get_traced_memory()
        logger.debug(f"Current memory usage: {current / 10**6}MB")
        logger.debug(f"Peak memory usage: {peak / 10**6}MB")
        return current, peak
