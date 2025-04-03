#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
bot_handler.py - Telegram 机器人处理模块

该模块实现了 Telegram 机器人的核心功能，包括：
- 机器人命令处理
- 搜索功能
- 权限控制
- 配置管理
- 消息过滤

作者: clionertr
项目: Meilisearch4TelegramSearchCKJ
"""

# 标准库导入
import ast
import asyncio
import gc
from typing import Any, Callable, Coroutine, Dict, List, Optional

# 第三方库导入
from telethon import Button, TelegramClient, events
from telethon.tl.functions.bots import SetBotCommandsRequest
from telethon.tl.types import BotCommand, BotCommandScopeDefault

# 本地模块导入
from Meilisearch4TelegramSearchCKJ.src.config.env import (
    APP_HASH, APP_ID, BANNED_WORDS, BOT_TOKEN, CACHE_EXPIRE_SECONDS,
    IPv6, MAX_PAGE, MEILI_HOST, MEILI_PASS, OWNER_IDS, PROXY,
    RESULTS_PER_PAGE, SEARCH_CACHE
)
from Meilisearch4TelegramSearchCKJ.src.models.logger import setup_logger
from Meilisearch4TelegramSearchCKJ.src.models.meilisearch_handler import MeiliSearchClient
from Meilisearch4TelegramSearchCKJ.src.utils.fmt_size import sizeof_fmt
from Meilisearch4TelegramSearchCKJ.src.utils.record_lastest_msg_id import load_config, save_config

MAX_RESULTS = MAX_PAGE * RESULTS_PER_PAGE


def set_permission(func: Callable[..., Coroutine[Any, Any, None]]) -> Callable[..., Coroutine[Any, Any, None]]:
    """
    权限检查装饰器：仅允许 OWNER_IDS 中的用户使用

    Args:
        func: 需要进行权限检查的异步函数

    Returns:
        装饰后的异步函数
    """

    async def wrapper(self, event, *args, **kwargs):
        """装饰器内部函数"""
        user_id = event.sender_id
        if not OWNER_IDS or user_id in OWNER_IDS:
            try:
                await func(self, event, *args, **kwargs)
            except Exception as e:
                self.logger.error(f"执行 {func.__name__} 时出错: {e}", exc_info=True)
                await event.reply(f"执行命令时发生错误: {e}")
        else:
            self.logger.info(f"用户 {user_id} 无权使用指令 {event.text}")
            await event.reply("你没有权限使用此指令。")

    return wrapper


class BotHandler:
    """
    Telegram 机器人处理类

    负责处理机器人的命令、搜索请求和用户交互。
    同时管理下载任务和搜索结果缓存。
    """

    def __init__(self, main_callback: Callable[[], Coroutine[Any, Any, None]]):
        """
        初始化 BotHandler 实例

        Args:
            main_callback: 主回调函数，用于启动下载和监听任务
        """
        self.logger = setup_logger()
        self.bot_client = TelegramClient(
            'session/bot',
            APP_ID,
            APP_HASH,
            use_ipv6=IPv6,
            proxy=PROXY,
            auto_reconnect=True,
            connection_retries=5
        )
        self.meili = MeiliSearchClient(MEILI_HOST, MEILI_PASS)
        self.search_results_cache: Dict[str, List[Dict]] = {}
        self.main_callback = main_callback
        self.download_task: Optional[asyncio.Task] = None

    async def initialize(self) -> None:
        """
        初始化机器人，包括启动客户端、设置命令列表和注册事件处理器
        """
        # 启动机器人客户端
        await self.bot_client.start(bot_token=BOT_TOKEN)
        await self.set_commands_list()
        await self.auto_start_download_and_listening()

        # 注册各类事件处理器
        # 1. 基本命令处理器
        self.bot_client.add_event_handler(self.start_handler, events.NewMessage(pattern=r'^/start$'))
        self.bot_client.add_event_handler(self.help_handler, events.NewMessage(pattern=r'^/help$'))
        self.bot_client.add_event_handler(self.about_handler, events.NewMessage(pattern=r'^/about$'))
        self.bot_client.add_event_handler(self.ping_handler, events.NewMessage(pattern=r'^/ping$'))

        # 2. 下载和监听相关命令
        self.bot_client.add_event_handler(
            self.start_download_and_listening,
            events.NewMessage(pattern=r'^/(start_client)$')
        )
        self.bot_client.add_event_handler(
            self.stop_download_and_listening,
            events.NewMessage(pattern=r'^/(stop_client)$')
        )

        # 3. 搜索相关命令
        self.bot_client.add_event_handler(
            self.search_command_handler,
            events.NewMessage(pattern=r'^/search (.+)')
        )
        self.bot_client.add_event_handler(self.clean, events.NewMessage(pattern=r'^/cc$'))

        # 4. 消息处理器
        # 转发消息处理器（仅在私聊中，对转发消息询问是否添加阻止名单）
        self.bot_client.add_event_handler(
            self.forwarded_message_handler,
            events.NewMessage(func=lambda e: e.is_private and e.fwd_from is not None)
        )
        # 私聊消息处理器（非命令消息）
        self.bot_client.add_event_handler(
            self.message_handler,
            events.NewMessage(func=lambda e: e.is_private and e.fwd_from is None and not e.text.startswith('/'))
        )

        # 5. 配置和过滤相关命令
        # 处理 /ban 命令
        self.bot_client.add_event_handler(self.ban_command_handler, events.NewMessage(pattern=r'^/ban\b'))
        # 处理 /banlist 命令
        self.bot_client.add_event_handler(self.banlist_handler, events.NewMessage(pattern=r'^/banlist\b'))
        self.bot_client.add_event_handler(self.set_config, events.NewMessage(pattern=r'^/set\b'))
        self.bot_client.add_event_handler(self.delete_all_contain_keyword, events.NewMessage(pattern=r'^/delete\b'))
        self.bot_client.add_event_handler(self.list_part_config, events.NewMessage(pattern=r'^/list$'))

        # 6. 回调处理器（翻页和确认按钮）
        self.bot_client.add_event_handler(self.callback_handler, events.CallbackQuery)

    async def set_commands_list(self) -> None:
        """
        设置机器人命令列表，在 Telegram 中显示可用命令
        """
        commands = [
            # 基本命令
            BotCommand(command="start", description="开始使用机器人"),
            BotCommand(command="help", description="显示帮助信息"),
            BotCommand(command="about", description="关于本项目"),
            BotCommand(command="ping", description="检查搜索服务状态"),

            # 搜索相关命令
            BotCommand(command="search", description="关键词搜索（空格分隔多个词）"),
            BotCommand(command="cc", description="清除搜索历史消息缓存"),

            # 下载和监听相关命令
            BotCommand(command="start_client", description="启动消息监听与下载历史消息"),
            BotCommand(command="stop_client", description="停止消息监听与下载"),

            # 配置相关命令
            BotCommand(command="list", description="显示当前配置"),
            BotCommand(command="set", description="设置配置项，格式: /set <key> <value>"),

            # 过滤相关命令
            BotCommand(command="ban", description="添加阻止名单，格式: /ban <id/word> ..."),
            BotCommand(command="banlist", description="显示当前阻止名单"),
            BotCommand(command="delete", description="删除包含关键词的文档，格式: /delete <word/id> ...")
        ]

        await self.bot_client(SetBotCommandsRequest(
            scope=BotCommandScopeDefault(),
            lang_code="",
            commands=commands
        ))

    async def run(self) -> None:
        """
        启动机器人并运行直到断开连接
        """
        await self.initialize()
        self.logger.log(25, "Bot started")
        await self.bot_client.run_until_disconnected()

    @set_permission
    async def stop_download_and_listening(self, event) -> None:
        """
        停止下载和监听任务

        Args:
            event: Telegram 事件对象
        """
        if self.download_task and not self.download_task.done():
            self.download_task.cancel()
            await event.reply("下载任务已停止")
        else:
            await event.reply("没有正在运行的下载任务")

    @set_permission
    async def start_download_and_listening(self, event) -> None:
        """
        启动下载和监听任务

        Args:
            event: Telegram 事件对象
        """
        await event.reply("开始下载历史消息，监听新消息...")
        self.logger.info("启动下载与监听任务")
        if self.download_task is None or self.download_task.done():
            self.download_task = asyncio.create_task(self.main_callback())
        else:
            await event.reply("下载任务已经在运行中。")

    async def auto_start_download_and_listening(self) -> None:
        """
        自动启动下载和监听任务（在机器人启动时调用）
        """
        if self.download_task is None or self.download_task.done():
            self.download_task = asyncio.create_task(self.main_callback())
        else:
            self.logger.info("下载任务已在运行")

    async def search_handler(self, event, query: str) -> None:
        """
        处理搜索请求，从缓存或 MeiliSearch 获取结果

        Args:
            event: Telegram 事件对象
            query: 搜索关键词
        """
        try:
            # 先尝试从缓存中获取结果
            if SEARCH_CACHE and query in self.search_results_cache:
                results = self.search_results_cache[query]
                self.logger.info(f"从缓存中获取搜索结果: '{query}'")
            else:
                # 如果缓存中没有，从 MeiliSearch 获取
                results = await self.get_search_results(query, limit=MAX_RESULTS)
                if SEARCH_CACHE:
                    self.search_results_cache[query] = results
                    # 后台异步清理缓存，无需阻塞执行
                    asyncio.create_task(self.clean_cache(query))

            # 发送搜索结果
            if results:
                await self.send_results_page(event, results, 0, query)
            else:
                await event.reply("没有找到相关结果。")
        except Exception as e:
            self.logger.error(f"搜索出错: {e}", exc_info=True)
            await event.reply(f"搜索出错: {e}")

    async def get_search_results(self, query: str, limit: int = 10, offset: int = 0, index_name: str = 'telegram') -> List[Dict]:
        """
        从 MeiliSearch 获取搜索结果

        Args:
            query: 搜索关键词
            limit: 返回结果数量限制
            offset: 结果偏移量
            index_name: 索引名称

        Returns:
            搜索结果列表
        """
        try:
            results = self.meili.search(query, index_name, limit=limit, offset=offset)
            return results.get('hits', [])
        except Exception as e:
            self.logger.error(f"MeiliSearch 搜索错误: {e}", exc_info=True)
            return []

    async def start_handler(self, event) -> None:
        """
        处理 /start 命令，显示欢迎信息

        Args:
            event: Telegram 事件对象
        """
        text = (
            "🔍 **Telegram 消息搜索机器人**\n\n"
            "欢迎使用 Telegram 消息搜索机器人！本机器人可以帮助您搜索保存的 Telegram 消息，解决中文搜索的不足。\n\n"
            "**基本使用方法**：\n"
            "• 直接在对话框中输入文本即可进行搜索\n"
            "• 使用 /search 命令后跟关键词进行搜索\n"
            "• 搜索结果支持翻页导航\n\n"
            "**常用命令**：\n"
            "• /help - 显示详细帮助信息\n"
            "• /search <关键词1> <关键词2> - 搜索多个关键词\n"
            "• /about - 了解项目信息\n"
            "• /ping - 检查搜索服务状态\n\n"
            "输入 /help 获取更多命令和详细说明。"
        )
        await event.reply(text)

    async def help_handler(self, event) -> None:
        """
        处理 /help 命令，显示详细帮助信息

        Args:
            event: Telegram 事件对象
        """
        help_text = (
            "📖 **Telegram 消息搜索机器人帮助**\n\n"
            "**搜索命令**：\n"
            "• 直接输入文本 - 在私聊中直接输入文本即可搜索\n"
            "• /search <关键词1> <关键词2> - 搜索包含多个关键词的消息\n\n"

            "**管理命令**：\n"
            "• /start_client - 启动消息监听与下载历史消息\n"
            "• /stop_client - 停止消息监听与下载任务\n"
            "• /cc - 清除搜索结果缓存\n"
            "• /ping - 检查搜索服务状态和数据库信息\n\n"

            "**配置命令**：\n"
            "• /list - 显示当前配置信息\n"
            "• /set <key> <value> - 设置配置项，例如：/set inc {}\n\n"

            "**过滤命令**：\n"
            "• /ban <id/word> ... - 添加用户ID或关键词到阻止名单\n"
            "• /banlist - 查看当前阻止名单\n"
            "• /delete <word/id> ... - 删除包含指定关键词的文档\n\n"

            "**其他命令**：\n"
            "• /about - 关于本项目的详细信息\n\n"

            "**搜索技巧**：\n"
            "• 多个关键词之间用空格分隔，将搜索同时包含这些关键词的消息\n"
            "• 搜索结果支持翻页，使用底部的翻页按钮浏览更多结果\n"
            "• 点击搜索结果中的跳转链接可直接查看原始消息"
        )
        await event.reply(help_text)

    @set_permission
    async def search_command_handler(self, event) -> None:
        """
        处理 /search 命令，提取搜索关键词并调用搜索处理器

        Args:
            event: Telegram 事件对象
        """
        query = event.pattern_match.group(1)
        self.logger.info(f"收到搜索指令: {query}")
        await self.search_handler(event, query)

    @set_permission
    async def clean(self, event) -> None:
        """
        处理 /cc 命令，清除搜索结果缓存

        Args:
            event: Telegram 事件对象
        """
        self.search_results_cache.clear()
        await event.reply("缓存已清理。")
        self.logger.info("缓存清理完成")
        gc.collect()  # 手动触发垃圾回收

    async def clean_cache(self, key: str) -> None:
        """
        定时清理搜索结果缓存

        Args:
            key: 要清理的缓存键
        """
        await asyncio.sleep(CACHE_EXPIRE_SECONDS)
        try:
            self.search_results_cache.pop(key, None)
            self.logger.info(f"缓存 {key} 已过期并删除")
        except Exception as e:
            self.logger.error(f"删除缓存 {key} 出错: {e}", exc_info=True)

    async def about_handler(self, event) -> None:
        """
        处理 /about 命令，显示项目相关信息

        Args:
            event: Telegram 事件对象
        """
        about_text = (
            "**🔍 Meilisearch4TelegramSearchCKJ**\n\n"
            "本项目基于 MeiliSearch 和 Telethon 构建，专为解决 Telegram 中文搜索功能不足而设计，提供强大的全文搜索能力。\n\n"
            "**主要特点**：\n"
            "• 支持中日韩文字的高效搜索\n"
            "• 支持多关键词组合搜索\n"
            "• 自动下载和索引历史消息\n"
            "• 实时监听和索引新消息\n"
            "• 支持阻止名单和关键词过滤\n\n"
            "**项目地址**：[Meilisearch4TelegramSearchCKJ](https://github.com/clionertr/Meilisearch4TelegramSearchCKJ)\n\n"
            "得益于 Telethon 的优秀设计，本项目运行稳定且资源占用低。项目由 [SearchGram](https://github.com/tgbot-collection/SearchGram) 重构而来，感谢原作者的贡献。\n\n"
            "如果您觉得本项目有用，欢迎在 GitHub 上给我们一个 Star ⭐"
        )
        await event.reply(about_text)

    @set_permission
    async def ping_handler(self, event) -> None:
        """
        处理 /ping 命令，检查搜索服务状态并显示数据库信息

        Args:
            event: Telegram 事件对象
        """
        try:
            # 获取 MeiliSearch 统计信息
            stats = self.meili.client.get_all_stats()
            text = "Pong!\n"

            # 数据库大小
            size = stats.get("databaseSize", 0)
            text += f"Database size: {sizeof_fmt(size)}\n"

            # 索引信息
            for uid, index in stats.get("indexes", {}).items():
                text += f"Index {uid} 有 {index.get('numberOfDocuments', 0)} 条文档\n"

            await event.reply(text)
        except Exception as e:
            self.logger.error(f"Ping 出错: {e}", exc_info=True)
            await event.reply(f"Ping 出错: {e}")

    @set_permission
    async def message_handler(self, event) -> None:
        """
        处理私聊中的非命令消息，将其作为搜索关键词处理

        Args:
            event: Telegram 事件对象
        """
        await self.search_handler(event, event.raw_text)

    def format_search_result(self, hit: Dict) -> str:
        """
        格式化搜索结果，限制文字长度，并根据消息类型生成对应的跳转链接

        Args:
            hit: 搜索结果条目

        Returns:
            格式化后的搜索结果文本
        """
        # 获取消息文本并进行安全处理
        text = hit.get('text') or ''
        # 添加安全检查，去除可能导致格式化错误的字符
        text = text.replace('**', '').replace('__', '')  # 去除可能导致 markdown 解析错误的标记

        # 限制文本长度
        if len(text) > 360:
            # 确保不会在多字节字符中间截断
            text = text[:360].strip() + "..."

        # 获取聊天信息
        chat = hit.get('chat', {})
        chat_type = chat.get('type', 'private')

        # 根据聊天类型生成不同的链接和标题
        if chat_type == 'private':
            chat_title = f"Private: {chat.get('username', 'N/A')}"
            parts = hit.get('id', '').split('-')
            url = f"tg://openmessage?user_id={parts[0]}&message_id={parts[1]}" if len(parts) >= 2 else ""
        else:
            chat_title = f"{chat_type.capitalize()}: {chat.get('title', 'N/A')}"
            parts = hit.get('id', '').split('-')
            url = f"https://t.me/c/{parts[0]}/{parts[1]}" if len(parts) >= 2 else ""

        # 获取日期
        date = hit.get('date', '').split('T')[0]

        # 修改链接格式，使用更安全的格式化方式
        return f"- **{chat_title}** ({date})\n{text}\n{f'[🔗跳转]({url})' if url else ''}\n{'—' * 18}\n"

    def get_pagination_buttons(self, query: str, page_number: int, total_hits: int) -> List[Button]:
        """
        根据当前页码和总结果生成翻页按钮

        Args:
            query: 搜索关键词
            page_number: 当前页码
            total_hits: 总结果数

        Returns:
            翻页按钮列表
        """
        buttons = []
        # 如果不是第一页，添加上一页按钮
        if page_number > 0:
            buttons.append(Button.inline("上一页", data=f"page_{query}_{page_number - 1}"))
        # 如果还有更多结果，添加下一页按钮
        if (page_number + 1) * RESULTS_PER_PAGE < total_hits:
            buttons.append(Button.inline("下一页", data=f"page_{query}_{page_number + 1}"))
        return buttons

    async def send_results_page(self, event, hits: List[Dict], page_number: int, query: str) -> None:
        """
        发送搜索结果页面

        Args:
            event: Telegram 事件对象
            hits: 搜索结果列表
            page_number: 当前页码
            query: 搜索关键词
        """
        # 计算当前页的索引范围
        start_index = page_number * RESULTS_PER_PAGE
        end_index = min((page_number + 1) * RESULTS_PER_PAGE, len(hits))
        page_results = hits[start_index:end_index]

        # 如果没有结果，返回提示
        if not page_results:
            await event.reply("没有更多结果了。")
            return

        # 格式化搜索结果
        response = "".join(self.format_search_result(hit) for hit in page_results)
        buttons = self.get_pagination_buttons(query, page_number, len(hits))

        # 发送搜索结果消息
        await self.bot_client.send_message(
            event.chat_id,
            f"搜索结果 (第 {page_number + 1} 页):\n{response}",
            buttons=buttons if buttons else None
        )

    async def edit_results_page(self, event, hits: List[Dict], page_number: int, query: str) -> None:
        """
        编辑现有搜索结果页面（用于翻页）

        Args:
            event: Telegram 事件对象
            hits: 搜索结果列表
            page_number: 当前页码
            query: 搜索关键词
        """
        # 检查搜索结果是否有效
        if hits is None:
            await event.reply("搜索结果无效或过期，请重新搜索。")
            return

        try:
            # 计算当前页的索引范围
            start_index = page_number * RESULTS_PER_PAGE
            end_index = min((page_number + 1) * RESULTS_PER_PAGE, len(hits))
            page_results = hits[start_index:end_index]

            # 如果没有结果，返回提示
            if not page_results:
                await event.reply("没有更多结果了。")
                return

            # 格式化搜索结果
            response = "".join(self.format_search_result(hit) for hit in page_results)
            buttons = self.get_pagination_buttons(query, page_number, len(hits))
            new_message = f"搜索结果 (第 {page_number + 1} 页):\n{response}"

            # 编辑消息，添加解析模式参数，确保正确处理 markdown
            await event.edit(
                new_message,
                buttons=buttons if buttons else None,
                parse_mode='markdown'  # 明确指定解析模式
            )
        except Exception as e:
            # 处理各种编辑错误
            if "Content of the message was not modified" in str(e):
                # 消息内容无变化，不需要更新
                self.logger.info("消息内容无变化，不需要更新。")
            elif "EntityBoundsInvalidError" in str(e):
                # 如果遇到实体边界错误，尝试以纯文本方式发送
                try:
                    await event.edit(
                        new_message.replace('**', '').replace('[', '').replace(']', ''),
                        buttons=buttons if buttons else None
                    )
                except Exception as e2:
                    self.logger.error(f"尝试纯文本编辑也失败：{e2}", exc_info=True)
                    await event.reply("编辑消息时出现格式错误，请重试。")
            else:
                self.logger.error(f"编辑结果页出错：{e}", exc_info=True)
                await event.reply(f"编辑结果页时出错：{e}")

    async def callback_page_handler(self, data, event) -> None:
        """
        处理翻页按钮回调

        Args:
            data: 回调数据（格式：page_{query}_{page_number}）
            event: Telegram 事件对象
        """
        try:
            # 解析回调数据格式：page_{query}_{page_number}
            _, query, page_str = data.split('_')
            page_number = int(page_str)

            # 根据配置从缓存中获取或重新获取搜索结果
            results = None
            if SEARCH_CACHE:
                results = self.search_results_cache.get(query)

            # 如果缓存中没有结果，重新搜索
            if not results:
                results = await self.get_search_results(query, limit=MAX_RESULTS)
                if SEARCH_CACHE:
                    self.search_results_cache[query] = results
                    # 后台异步清理缓存，无需阻塞执行
                    asyncio.create_task(self.clean_cache(query))

            # 显示加载中提示并编辑结果页
            await event.edit(f"正在加载第 {page_number + 1} 页...")
            await self.edit_results_page(event, results, page_number, query)
        except Exception as e:
            self.logger.error(f"翻页搜索出错：{e}", exc_info=True)
            await event.answer(f"搜索出错：{e}", alert=True)

    async def callback_ban_handler(self, data, event) -> None:
        """
        处理添加阻止名单确认按钮回调

        Args:
            data: 回调数据（格式：ban_yes_{user_id}）
            event: Telegram 事件对象
        """
        try:
            # 从回调数据中提取用户ID
            user_id = int(data[len("ban_yes_"):])

            # 加载配置并获取当前阻止名单
            config = load_config()
            banned_ids = config['bot'].get('banned_ids', [])

            # 如果用户不在阻止名单中，添加并保存
            if user_id not in banned_ids:
                banned_ids.append(user_id)
                config['bot']['banned_ids'] = banned_ids
                save_config(config)
                await event.edit(f"用户 {user_id} 已添加到阻止名单中")
            else:
                await event.edit(f"用户 {user_id} 已经在阻止名单中")
        except Exception as e:
            self.logger.error(f"添加阻止名单中失败: {e}", exc_info=True)
            await event.answer(f"添加阻止名单中失败: {e}", alert=True)

    async def callback_delete_handler(self, data, event) -> None:
        """
        处理删除关键词确认按钮回调

        Args:
            data: 回调数据（格式：d`y`{delete_list}）
            event: Telegram 事件对象
        """
        try:
            # 从回调数据中提取删除列表
            delete_list = data[len("d`y`"):]
            delete_list = ast.literal_eval(delete_list)

            # 将关键词格式化为引号包围的字符串
            target_keyword_list = [f'"{keyword}"' for keyword in delete_list]

            # 删除包含关键词的文档
            for target_keyword in target_keyword_list:
                self.meili.delete_all_contain_keyword(target_keyword)

            await event.reply("已删除所有包含关键词的文档")
        except Exception as e:
            self.logger.error(f"删除关键词失败: {e}", exc_info=True)
            await event.answer(f"删除关键词失败: {e}", alert=True)

    async def callback_handler(self, event) -> None:
        """
        处理所有按钮回调事件

        Args:
            event: Telegram 事件对象
        """
        # 解码回调数据
        data = event.data.decode('utf-8')

        # 根据数据前缀分发到不同的处理器
        if data.startswith('page_'):
            # 翻页按钮
            await self.callback_page_handler(data, event)
        elif data.startswith("ban_yes_"):
            # 确认添加阻止名单
            await self.callback_ban_handler(data, event)
        elif data.startswith("ban_no_"):
            # 取消添加阻止名单
            await event.edit("已取消添加")
        elif data.startswith("d`y`"):
            # 确认删除关键词
            await self.callback_delete_handler(data, event)
        elif data.startswith("d`n"):
            # 取消删除关键词
            await event.edit("已取消删除")
        else:
            # 未知回调数据
            self.logger.info(f"未知回调数据: {data}")
            await event.answer("未知回调数据", alert=True)

    @set_permission
    async def ban_command_handler(self, event) -> None:
        """
        处理 /ban 命令，将用户ID或关键词添加到阻止名单

        格式：/ban 123 广告4 321
        将能转换为 int 的参数加入 banned_ids，将其他参数加入 banned_words

        Args:
            event: Telegram 事件对象
        """
        # 提取命令参数
        tokens = event.text.split()[1:]
        if not tokens:
            await event.reply("用法: /ban <id或关键词> ...")
            return

        # 加载配置
        config = load_config()
        banned_ids = config['bot'].get('banned_ids', [])
        banned_words = config['bot'].get('banned_words', [])
        new_ids = []
        new_words = []

        # 处理每个参数
        for token in tokens:
            try:
                # 尝试将参数转换为整数（用户ID）
                val = int(token)
                if val not in banned_ids:
                    banned_ids.append(val)
                    new_ids.append(val)
            except ValueError:
                # 非整数参数视为关键词
                if token not in banned_words:
                    banned_words.append(token)
                    new_words.append(token)

        # 保存更新后的配置
        config['bot']['banned_ids'] = banned_ids
        config['bot']['banned_words'] = banned_words
        save_config(config)

        # 生成响应消息
        reply_msg = "已添加：\n"
        if new_ids:
            reply_msg += f"阻止名单 ID: {new_ids}\n"
        if new_words:
            reply_msg += f"禁用关键词: {new_words}"
        await event.reply(reply_msg)

    @set_permission
    async def banlist_handler(self, event) -> None:
        """
        处理 /banlist 命令，显示当前阻止名单信息

        显示 banned_ids 与 banned_words 的当前值

        Args:
            event: Telegram 事件对象
        """
        # 加载配置
        config = load_config()
        banned_ids = config['bot'].get('banned_ids', [])
        banned_words = config['bot'].get('banned_words', [])

        # 格式化阻止名单内容
        banned_ids_str = '\n'.join(map(str, banned_ids)) if banned_ids else '无'
        banned_words_str = '\n'.join(banned_words) if banned_words else '无'

        # 生成响应消息
        reply_msg = (
            "当前阻止名单信息：\n"
            f"阻止名单 IDs:\n{banned_ids_str}\n\n"
            f"禁用关键词:\n{banned_words_str}"
        )
        await event.reply(reply_msg)

    async def forwarded_message_handler(self, event) -> None:
        """
        处理转发消息，询问是否将消息发送者添加到阻止名单

        Args:
            event: Telegram 事件对象
        """
        from telethon.tl.types import PeerUser

        # 确保存在转发信息
        if not event.fwd_from:
            return

        # 安全获取用户 ID
        try:
            # 获取转发消息的来源ID
            from_id = event.fwd_from.from_id
            if not isinstance(from_id, PeerUser):
                await event.reply("⚠️ 仅支持用户来源的转发消息")
                return

            # 提取用户ID
            from_user_id = from_id.user_id
        except AttributeError:
            await event.reply("❌ 无法获取来源用户信息")
            return

        # 创建确认按钮
        text = f"你是否要将用户 {from_user_id} 添加到阻止名单？"
        buttons = [
            Button.inline("是", data=f"ban_yes_{from_user_id}"),
            Button.inline("否", data=f"ban_no_{from_user_id}")
        ]
        await event.reply(text, buttons=buttons)

    @set_permission
    async def set_config(self, event) -> None:
        """
        处理 /set 命令，设置配置项

        格式：/set <key> <value>
        支持的配置项：
        - white_list/wl: 白名单
        - black_list: 黑名单
        - banned_words/bw: 禁用关键词
        - banned_ids/bi: 禁用用户ID
        - incremental/inc: 增量下载配置

        Args:
            event: Telegram 事件对象
        """
        # 提取命令参数
        tokens = event.text.split()[1:]
        try:
            self.logger.info(f"设置配置项: {tokens}")

            # 检查参数
            if not tokens:
                await event.reply("用法: /set <white_list|black_list|banned_words|banned_ids|incremental> <value:List>")
                return

            # 解析参数
            key, value = tokens
            config = load_config()

            # 根据配置项类型设置不同的值
            if key in {'white_list','wl'}:
                config['bot']['white_list'] = ast.literal_eval(value)
            elif key == 'black_list':
                config['bot']['black_list'] = ast.literal_eval(value)
            elif key in {'banned_words','bw'}:
                config['bot']['banned_words'] = ast.literal_eval(value)
            elif key in {'banned_ids', 'bi'}:
                config['bot']['banned_ids'] = ast.literal_eval(value)
            elif key in {'incremental','inc'}:
                config['download_incremental'] = ast.literal_eval(value)
            else:
                await event.reply("未知配置项")
                return

            # 保存配置并响应
            save_config(config)
            await event.reply(f"设置配置项 {key} 成功")
        except Exception as e:
            self.logger.error(f"设置配置出错: {e}", exc_info=True)
            await event.reply(f"设置配置出错: {e}")

    @set_permission
    async def list_part_config(self, event) -> None:
        """
        处理 /list 命令，显示当前配置信息

        Args:
            event: Telegram 事件对象
        """
        try:
            # 加载配置
            config = load_config()

            # 格式化并发送配置信息
            await event.reply(
                f"当前配置:\n"
                f"\n白名单: {config['bot']['white_list']}"
                f"\n黑名单: {config['bot']['black_list']}"
                f"\n禁用关键词: {config['bot']['banned_words']}"
                f"\n禁用用户: {config['bot']['banned_ids']}"
                f"\n增量下载: {config['download_incremental']}"
            )
        except Exception as e:
            self.logger.error(f"获取配置出错: {e}", exc_info=True)
            await event.reply(f"获取配置出错: {e}")

    @set_permission
    async def delete_all_contain_keyword(self, event) -> None:
        """
        处理 /delete 命令，删除包含指定关键词的文档

        格式：/delete <word1> <word2> ...
        如果没有提供关键词，则使用 BANNED_WORDS 中的关键词

        Args:
            event: Telegram 事件对象
        """
        try:
            # 获取关键词列表，如果没有提供，则使用禁用关键词
            target_keyword_list = event.text.split()[1:] or BANNED_WORDS

            # 创建确认按钮
            text = f"你是否要删除所有包含关键词{target_keyword_list}的文档？"
            buttons = [
                Button.inline("是", data=f"d`y`{target_keyword_list}"),
                Button.inline("否", data=f"d`n")
            ]
            await event.reply(text, buttons=buttons)
        except Exception as e:
            self.logger.error(f"删除关键词出错: {e}", exc_info=True)
            await event.reply(f"删除关键词出错: {e}")
