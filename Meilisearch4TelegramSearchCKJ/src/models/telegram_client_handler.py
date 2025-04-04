#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""
Telegram消息获取与索引模块

本模块实现了Telegram消息的获取、处理和存储到Meilisearch的功能。
主要包括消息序列化、反应数据处理以及历史消息下载等功能。
"""
import asyncio
import gc
import tracemalloc
import pytz

from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
from telethon.sessions import StringSession
from telethon.tl.types import Channel, Chat, User, Message, ReactionCount, ReactionEmoji, ReactionCustomEmoji

from Meilisearch4TelegramSearchCKJ.src.config.env import (
    APP_ID, APP_HASH, BATCH_MSG_NUM, NOT_RECORD_MSG, TIME_ZONE,
    TELEGRAM_REACTIONS, IPv6, PROXY, SESSION_STRING, WHITE_LIST,
    BLACK_LIST, BANNED_IDS, BANNED_WORDS
)
from Meilisearch4TelegramSearchCKJ.src.models.logger import setup_logger
from Meilisearch4TelegramSearchCKJ.src.utils.is_in_white_or_black_list import is_allowed
from Meilisearch4TelegramSearchCKJ.src.utils.record_lastest_msg_id import update_download_incremental

# 设置时区
tz = pytz.timezone(TIME_ZONE)
# 设置日志记录器
logger = setup_logger()

# 开启内存跟踪
tracemalloc.start()


async def calculate_reaction_score(reactions: dict) -> float | None:
    """
    计算消息反应的总分数

    根据不同反应类型的权重计算总分数

    Args:
        reactions: 包含反应类型和数量的字典

    Returns:
        计算的总分数，如果没有反应则ReturnsNone
    """
    total_score = 0.0
    if reactions:
        for reaction, count in reactions.items():
            weight = TELEGRAM_REACTIONS.get(reaction, 0.0)
            total_score += count * weight
        return total_score
    return None


async def serialize_chat(chat):
    """
    将聊天对象序列化为字典

    Args:
        chat: Telegram聊天对象

    Returns:
        包含聊天信息的字典，如果chat为None则ReturnsNone
    """
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
    """
    将发送者对象序列化为字典

    Args:
        sender: Telegram用户对象

    Returns:
        包含发送者信息的字典，如果sender为None则ReturnsNone
    """
    if not sender:
        return None

    return {
        'id': sender.id,
        'username': getattr(sender, 'username', None)
    }


async def serialize_reactions(message: Message):
    """
    获取消息对象的reaction表情和数量，并Returns字典

    Args:
        message: Telegram消息对象

    Returns:
        包含反应信息的字典，如果没有反应则ReturnsNone
    """
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


def is_banned_message(text, from_user):
    """
    检查消息是否被禁止

    检查消息发送者是否在禁止列表中或消息文本是否包含敏感词

    Args:
        text: 消息文本
        from_user: 发送者信息字典

    Returns:
        是否禁止该消息的布尔值
    """
    # 检查用户是否被禁言
    if from_user is not None:
        user_id = from_user.get('id')
        if user_id in BANNED_IDS:
            logger.debug(f"用户 {user_id} 被禁止")
            return True  # 用户被禁止

    # 处理text为None的情况
    text = text or ''

    # 检查是否存在敏感词
    for banned_word in BANNED_WORDS:
        if banned_word in text:
            logger.debug(f"消息含有违禁词，已被过滤")
            return True  # 含违禁词

    return False  # 消息合法


async def serialize_message(message: Message, not_edited=True):
    """
    将消息对象序列化为字典

    Args:
        message: Telegram消息对象
        not_edited: 是否为未编辑的消息，默认为True

    Returns:
        包含消息信息的字典，如果消息不合法则ReturnsNone
    """
    try:
        # 并行获取chat与sender
        chat, sender = await asyncio.gather(message.get_chat(), message.get_sender())
        reactions = await serialize_reactions(message)
        reaction_score = await calculate_reaction_score(reactions)
        text = getattr(message, 'text', None) or getattr(message, 'caption', None)
        from_user = await serialize_sender(sender)

        # 检查消息是否被禁止
        if from_user is None:
            logger.warning(f"消息 (ID: {getattr(message, 'id', '未知')}) 的发送者信息为空")
        if is_banned_message(text, from_user):
            return None

        # 构建消息ID
        if not_edited:
            message_id = f"{chat.id}-{message.id}"
        else:
            message_id = f"{chat.id}-{message.id}-{int(message.edit_date.timestamp())}"

        return {
            'id': message_id,
            'chat': await serialize_chat(chat),
            'date': message.date.astimezone(tz).isoformat(),
            'text': text,
            'from_user': from_user,
            'reactions': reactions,
            'reactions_scores': reaction_score,
            'text_len': len(getattr(message, 'text', '') or '')
        }
    except Exception as e:
        logger.error(f"序列化消息出错 (ID: {getattr(message, 'id', '未知')}): {e}")
        return None


class TelegramUserBot:
    """
    Telegram用户机器人类

    用于获取和处理Telegram消息，并将消息存储到Meilisearch
    """

    def __init__(self, meili_client):
        """
        初始化Telegram用户机器人

        Args:
            meili_client: Meilisearch客户端实例
        """
        self.api_id = APP_ID
        self.api_hash = APP_HASH
        self.session = StringSession(SESSION_STRING) if SESSION_STRING else 'session/user_bot_session'
        self.meili = meili_client
        self.white_list = WHITE_LIST
        self.black_list = BLACK_LIST

        # 初始化Telegram客户端
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
        """
        启动Telegram用户机器人
        """
        try:
            await self.client.start()
            logger.info("用户机器人启动成功")
            self.register_handlers()
        except Exception as e:
            logger.error(f"启动机器人失败: {e}")
            raise

    def register_handlers(self):
        """
        注册消息处理器
        """
        @self.client.on(events.NewMessage)
        async def handle_new_message(event):
            """处理新消息事件"""
            peer_id = event.chat_id
            try:
                if is_allowed(peer_id, self.white_list, self.black_list):
                    await self._process_message(event.message)
                else:
                    logger.info(f"聊天ID {peer_id} 不在允许列表内")
            except Exception as e:
                logger.error(f"处理新消息出错: {e}")

        @self.client.on(events.MessageEdited)
        async def handle_edit_message(event):
            """处理消息编辑事件"""
            peer_id = event.chat_id
            try:
                if is_allowed(peer_id, self.white_list, self.black_list):
                    await self._process_message(event.message, NOT_RECORD_MSG)
                else:
                    logger.info(f"聊天ID {peer_id} 不在允许列表内")
            except Exception as e:
                logger.error(f"处理编辑消息出错: {e}")

    async def _process_message(self, message, not_edited=True):
        """
        处理消息

        Args:
            message: Telegram消息对象
            not_edited: 是否为未编辑的消息，默认为True
        """
        try:
            if message.text or getattr(message, 'caption', None):
                message_preview = message.text[:100] if message.text else message.caption
                logger.info(f"收到消息: {message_preview}")
                await self._cache_message(message, not_edited)
        except Exception as e:
            logger.error(f"处理消息 ID {message.id} 出错: {e}")

    async def _cache_message(self, message, not_edited=True):
        """
        缓存消息到Meilisearch

        Args:
            message: Telegram消息对象
            not_edited: 是否为未编辑的消息，默认为True
        """
        try:
            doc = await serialize_message(message, not_edited)
            if doc:
                result = self.meili.add_documents([doc])
                logger.info(f"缓存消息结果: {result}")
        except Exception as e:
            logger.error(f"缓存消息出错: {e}")

    async def download_history(self, peer, limit=None, batch_size=BATCH_MSG_NUM, offset_id=0, offset_date=None,
                               latest_msg_config=None, dialog_id=None):
        """
        下载聊天历史记录

        Args:
            peer: Telegram聊天对象
            limit: 限制下载消息数量，默认为None表示不限制
            batch_size: 每批处理的消息数量
            offset_id: 起始消息ID偏移
            offset_date: 起始日期偏移
            latest_msg_config: 最新消息配置
            dialog_id: 对话ID
        """
        try:
            messages = []
            total_messages = 0

            # 迭代获取消息
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

                # 达到批处理数量时处理一批消息
                if len(messages) >= batch_size:
                    update_download_incremental(dialog_id, messages[-1], latest_msg_config)
                    await self._process_message_batch(messages)
                    messages.clear()
                    logger.info(f"已下载 {total_messages} 条消息")

            # 处理剩余消息
            if messages:
                update_download_incremental(dialog_id, messages[-1], latest_msg_config)
                await self._process_message_batch(messages)
                logger.info(f"完成下载 {peer.id} 的历史消息")

        except FloodWaitError as e:
            logger.warning(f"请求过于频繁，等待 {e.seconds} 秒后重试")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            logger.error(f"下载历史消息出错: {e}")
            raise

    async def _process_message_batch(self, messages):
        """
        批量处理消息

        Args:
            messages: 消息列表
        """
        try:
            self.meili.add_documents(messages)
            logger.info(f"处理批量消息 {len(messages)} 条")
        except Exception as e:
            logger.error(f"处理消息批量出错: {e}")

    async def cleanup(self):
        """
        清理资源
        """
        try:
            # 使用超时来防止断开连接操作无限等待
            if self.client and self.client.is_connected():
                logger.info("正在断开 UserBot 客户端连接...")
                try:
                    await asyncio.wait_for(self.client.disconnect(), timeout=3.0)
                    logger.info("UserBot 客户端已断开连接")
                except asyncio.TimeoutError:
                    logger.warning("UserBot 客户端断开连接超时")
                except Exception as e:
                    logger.error(f"断开 UserBot 客户端连接时出错: {e}", exc_info=True)

            # 强制进行垃圾回收
            gc.collect()
            logger.info("资源清理完成")
        except Exception as e:
            logger.error(f"清理资源时出错: {e}", exc_info=True)

    @staticmethod
    def get_memory_usage():
        """
        获取内存使用情况

        Returns:
            当前内存使用量和峰值内存使用量的元组
        """
        current, peak = tracemalloc.get_traced_memory()
        logger.debug(f"当前内存: {current / 10 ** 6:.2f}MB, 峰值内存: {peak / 10 ** 6:.2f}MB")
        return current, peak
