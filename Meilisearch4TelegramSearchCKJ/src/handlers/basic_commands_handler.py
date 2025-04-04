#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
basic_commands_handler.py - Handles basic informational commands
"""
from telethon import TelegramClient
from Meilisearch4TelegramSearchCKJ.src.models.meilisearch_handler import MeiliSearchClient
from Meilisearch4TelegramSearchCKJ.src.utils.fmt_size import sizeof_fmt
from Meilisearch4TelegramSearchCKJ.src.utils.permissions import set_permission

class BasicCommandsHandler:
    """Handles basic informational commands like /start, /help, /about, /ping."""

    def __init__(self, bot_client: TelegramClient, meili: MeiliSearchClient, logger):
        self.bot_client = bot_client
        self.meili = meili
        self.logger = logger

    async def handle_start(self, event) -> None:
        """Handles /start command."""
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
            "• /rs - 重启消息监听与下载任务\n"
            "• /about - 了解项目信息\n"
            "• /ping - 检查搜索服务状态\n\n"
            "输入 /help 获取更多命令和详细说明。"
        )
        await event.reply(text)

    async def handle_help(self, event) -> None:
        """Handles /help command."""
        help_text = (
            "📖 **Telegram 消息搜索机器人帮助**\n\n"
            "**搜索命令**：\n"
            "• 直接输入文本 - 在私聊中直接输入文本即可搜索\n"
            "• /search <关键词1> <关键词2> - 搜索包含多个关键词的消息\n\n"

            "**管理命令**：\n"
            "• /start_client - 启动消息监听与下载历史消息\n"
            "• /stop_client - 停止消息监听与下载任务\n"
            "• /rs - 重启消息监听与下载任务（3秒延迟）\n"
            "• /cc - 清除搜索结果缓存\n"
            "• /ping - 检查搜索服务状态和数据库信息\n\n"

            "**配置命令**：\n"
            "• /list - 显示当前配置信息\n"
            "• /set <key> <value> - 设置配置项，例如：/set inc {}\n"
            "  （配置更新后会自动重启以应用新配置）\n\n"

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

    async def handle_about(self, event) -> None:
        """Handles /about command."""
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
    async def handle_ping(self, event) -> None:
        """Handles /ping command."""
        try:
            stats = self.meili.client.get_all_stats()
            text = "Pong!\n"
            size = stats.get("databaseSize", 0)
            text += f"Database size: {sizeof_fmt(size)}\n"
            for uid, index in stats.get("indexes", {}).items():
                text += f"Index {uid} 有 {index.get('numberOfDocuments', 0)} 条文档\n"
            await event.reply(text)
        except Exception as e:
            self.logger.error(f"Ping 出错: {e}", exc_info=True)
            await event.reply(f"Ping 出错: {e}")
