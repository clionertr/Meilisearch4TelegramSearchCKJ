#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
telegram_bot.py - Main Telegram Bot Orchestrator Class

Initializes clients, handlers, registers events, and manages the bot lifecycle.
"""

# Standard library imports
import asyncio
from typing import Any, Callable, Coroutine, Optional

# Third-party imports
from telethon import TelegramClient, events
from telethon.tl.functions.bots import SetBotCommandsRequest
from telethon.tl.types import BotCommand, BotCommandScopeDefault

# Local module imports
from Meilisearch4TelegramSearchCKJ.src.config.env import (
    APP_HASH, APP_ID, BOT_TOKEN, IPv6, PROXY, reload_config
)
from Meilisearch4TelegramSearchCKJ.src.models.logger import setup_logger
from Meilisearch4TelegramSearchCKJ.src.models.meilisearch_handler import MeiliSearchClient

# Import Handlers (adjust path if you created a handlers directory)
from Meilisearch4TelegramSearchCKJ.src.handlers.basic_commands_handler import BasicCommandsHandler
from Meilisearch4TelegramSearchCKJ.src.handlers.search_handler import SearchHandler
from Meilisearch4TelegramSearchCKJ.src.handlers.config_handler import ConfigHandler
from Meilisearch4TelegramSearchCKJ.src.handlers.filter_handler import FilterHandler
from Meilisearch4TelegramSearchCKJ.src.handlers.callback_query_dispatcher import CallbackQueryDispatcher
from Meilisearch4TelegramSearchCKJ.src.utils.permissions import set_permission # For task management commands


class TelegramBot:
    """
    Main orchestrator for the Telegram Bot.
    Initializes clients, handlers, registers events, and manages lifecycle.
    """

    def __init__(self, meili_client: MeiliSearchClient, main_callback: Callable[[], Coroutine[Any, Any, None]]):
        """
        Initializes the TelegramBot instance.

        Args:
            meili_client: An instance of MeiliSearchClient.
            main_callback: Async function to start download/listening task.
        """
        self.logger = setup_logger()
        self.meili = meili_client
        self.main_callback = main_callback
        self.download_task: Optional[asyncio.Task] = None

        # Initialize Telegram Bot Client
        self.bot_client = TelegramClient(
            'session/bot',
            APP_ID,
            APP_HASH,
            use_ipv6=IPv6,
            proxy=PROXY,
            auto_reconnect=True,
            connection_retries=5
        )
        self.logger.info("Telegram Bot Client initialized.")

        # Initialize Handlers
        self.basic_cmds_handler = BasicCommandsHandler(self.bot_client, self.meili, self.logger)
        self.search_handler = SearchHandler(self.bot_client, self.meili, self.logger)
        self.config_handler = ConfigHandler(self.bot_client, self.logger)
        self.filter_handler = FilterHandler(self.bot_client, self.meili, self.logger)
        self.callback_dispatcher = CallbackQueryDispatcher(self.logger, self.search_handler, self.filter_handler)
        self.logger.info("All handlers initialized.")

    async def _set_commands_list(self) -> None:
        """Sets the bot command list visible in Telegram clients."""
        commands = [
            BotCommand(command="start", description="开始使用机器人"),
            BotCommand(command="help", description="显示帮助信息"),
            BotCommand(command="about", description="关于本项目"),
            BotCommand(command="ping", description="检查搜索服务状态"),
            BotCommand(command="search", description="关键词搜索（空格分隔）"),
            BotCommand(command="cc", description="清除搜索历史消息缓存"),
            BotCommand(command="start_client", description="启动消息监听与下载"),
            BotCommand(command="stop_client", description="停止消息监听与下载"),
            BotCommand(command="list", description="显示当前配置"),
            BotCommand(command="set", description="设置配置项 (格式: /set <key> <value>)"),
            BotCommand(command="ban", description="添加阻止名单 (格式: /ban <id/word> ...)"),
            BotCommand(command="banlist", description="显示当前阻止名单"),
            BotCommand(command="delete", description="删除含关键词文档 (格式: /delete <word/id> ...)")
        ]
        try:
            await self.bot_client(SetBotCommandsRequest(
                scope=BotCommandScopeDefault(),
                lang_code="",
                commands=commands
            ))
            self.logger.info("Bot commands list updated.")
        except Exception as e:
            self.logger.error(f"Failed to set bot commands: {e}", exc_info=True)

    def _register_event_handlers(self) -> None:
        """Registers all event handlers with the Telethon client."""
        # 1. Basic Commands
        self.bot_client.add_event_handler(
            self.basic_cmds_handler.handle_start, events.NewMessage(pattern=r'^/start$')
        )
        self.bot_client.add_event_handler(
            self.basic_cmds_handler.handle_help, events.NewMessage(pattern=r'^/help$')
        )
        self.bot_client.add_event_handler(
            self.basic_cmds_handler.handle_about, events.NewMessage(pattern=r'^/about$')
        )
        self.bot_client.add_event_handler(
            self.basic_cmds_handler.handle_ping, events.NewMessage(pattern=r'^/ping$')
        )

        # 2. Download/Listen Task Management Commands (handled by this class)
        self.bot_client.add_event_handler(
            self.start_download_and_listening, events.NewMessage(pattern=r'^/(start_client)$')
        )
        self.bot_client.add_event_handler(
            self.stop_download_and_listening, events.NewMessage(pattern=r'^/(stop_client)$')
        )

        # 3. Search Commands & Messages
        self.bot_client.add_event_handler(
            self.search_handler.handle_search_command, events.NewMessage(pattern=r'^/search (.+)')
        )
        self.bot_client.add_event_handler(
            self.search_handler.handle_clean_cache_command, events.NewMessage(pattern=r'^/cc$')
        )
        # Private non-command/non-forward messages -> Search
        self.bot_client.add_event_handler(
            self.search_handler.handle_message_search,
            events.NewMessage(func=lambda e: e.is_private and e.fwd_from is None and not e.text.startswith('/'))
        )

        # 4. Configuration Commands
        self.bot_client.add_event_handler(
            self.config_handler.handle_set_config, events.NewMessage(pattern=r'^/set\b')
        )
        self.bot_client.add_event_handler(
            self.config_handler.handle_list_config, events.NewMessage(pattern=r'^/list$')
        )

        # 5. Filtering Commands & Events
        self.bot_client.add_event_handler(
            self.filter_handler.handle_ban_command, events.NewMessage(pattern=r'^/ban\b')
        )
        self.bot_client.add_event_handler(
            self.filter_handler.handle_banlist_command, events.NewMessage(pattern=r'^/banlist\b')
        )
        self.bot_client.add_event_handler(
            self.filter_handler.handle_delete_command, events.NewMessage(pattern=r'^/delete\b')
        )
        # Forwarded messages (Private only) -> Filter Handler
        self.bot_client.add_event_handler(
            self.filter_handler.handle_forwarded_message,
            events.NewMessage(func=lambda e: e.is_private and e.fwd_from is not None)
        )

        # 6. Callback Query Handler (Dispatcher)
        self.bot_client.add_event_handler(
            self.callback_dispatcher.handle_callback, events.CallbackQuery
        )

        self.logger.info("All event handlers registered.")

    async def initialize(self) -> None:
        """Initializes the bot: connect, set commands, register handlers, start tasks."""
        self.logger.info("Initializing Telegram Bot...")
        await self.bot_client.start(bot_token=BOT_TOKEN)
        self.logger.info("Bot client started.")
        await self._set_commands_list()
        self._register_event_handlers()
        await self._auto_start_download_and_listening() # Start task automatically
        self.logger.info("Bot initialization complete.")

    async def run(self) -> None:
        """Starts the bot, registers handlers, and runs until disconnected."""
        await self.initialize()
        try:
            # --- 修改开始 ---
            # 1. 先 await get_me() 获取 User 对象
            me = await self.bot_client.get_me()
            # 2. 从 User 对象获取 username
            bot_username = me.username if me else "Unknown" # 安全起见，检查 me 是否为 None
            # 3. 使用获取到的 username 记录日志
            self.logger.log(25, f"Bot '{bot_username}' is running...")
            # --- 修改结束 ---
        except Exception as e:
            # 如果获取机器人信息失败，记录错误但继续尝试运行
            self.logger.error(f"启动时获取机器人信息失败: {e}", exc_info=True)
            self.logger.log(25, "Bot is running (获取用户名失败)...")

        # 运行直到断开连接
        await self.bot_client.run_until_disconnected()
        self.logger.info("Bot client disconnected.")

    # --- Download/Listen Task Management ---

    @set_permission
    async def stop_download_and_listening(self, event) -> None:
        """Stops the background download/listening task."""
        if self.download_task and not self.download_task.done():
            self.download_task.cancel()
            try:
                # Wait briefly for cancellation to complete
                await asyncio.wait_for(self.download_task, timeout=5.0)
            except asyncio.CancelledError:
                self.logger.info("Download task successfully cancelled.")
                await event.reply("✅ 消息监听与下载任务已停止。")
            except asyncio.TimeoutError:
                 self.logger.warning("Download task did not cancel within timeout.")
                 await event.reply("⚠️ 请求停止任务，但可能仍在后台运行。")
            except Exception as e:
                 self.logger.error(f"Error while stopping download task: {e}", exc_info=True)
                 await event.reply(f"❌ 停止任务时出错: {e}")
            self.download_task = None # Clear the task reference
        else:
            await event.reply("ℹ️ 当前没有正在运行的消息监听与下载任务。")

    @set_permission
    async def start_download_and_listening(self, event) -> None:
        """Starts the background download/listening task."""
        if self.download_task and not self.download_task.done():
            await event.reply("ℹ️ 消息监听与下载任务已经在运行中。")
        else:
            self.logger.info("收到启动下载与监听任务的指令...")
            # 保存初始消息的引用，以便后续更新
            initial_message = await event.reply("⏳ 正在启动消息监听与下载任务...")

            # 重新加载配置文件，确保使用最新的配置
            try:
                self.logger.info("重新加载配置文件...")
                reload_config()
                self.logger.info("配置文件重新加载成功")
            except Exception as e:
                self.logger.error(f"重新加载配置文件失败: {e}", exc_info=True)
                await self._safe_edit_or_reply(initial_message, f"⚠️ 重新加载配置文件失败: {e}，将使用旧配置继续")

            # 启动下载任务
            self.download_task = asyncio.create_task(self.main_callback())
            # 添加延迟以允许任务启动或立即失败
            await asyncio.sleep(1)

            # 检查任务状态
            if self.download_task and self.download_task.done():
                # 任务已完成，检查是否有异常
                try:
                    if self.download_task.exception():
                        err = self.download_task.exception()
                        self.logger.error(f"下载任务启动失败: {err}", exc_info=True)
                        await self._safe_edit_or_reply(initial_message, f"❌ 启动任务失败: {err}") # 更新消息
                        self.download_task = None
                    else:
                        # 任务完成但没有异常（可能是正常完成）
                        await self._safe_edit_or_reply(initial_message, "✅ 消息监听与下载任务已完成。")
                        self.download_task = None
                except Exception as e:
                    self.logger.error(f"检查下载任务状态时出错: {e}", exc_info=True)
                    await self._safe_edit_or_reply(initial_message, f"⚠️ 检查任务状态时出错: {e}")
                    self.download_task = None
            elif self.download_task:
                # 任务仍在运行中
                await self._safe_edit_or_reply(initial_message, "✅ 消息监听与下载任务已启动。") # 更新消息
            else:
                # 任务可能已被取消或未正确创建
                await self._safe_edit_or_reply(initial_message, "⚠️ 启动任务时遇到问题，请检查日志。")


    async def _auto_start_download_and_listening(self) -> None:
        """Automatically starts the download/listening task on bot startup if not running."""
        if self.download_task is None or self.download_task.done():
            self.logger.info("自动启动下载与监听任务...")

            # 启动时也重新加载配置文件，确保使用最新的配置
            try:
                self.logger.info("重新加载配置文件...")
                reload_config()
                self.logger.info("配置文件重新加载成功")
            except Exception as e:
                self.logger.error(f"重新加载配置文件失败: {e}", exc_info=True)

            self.download_task = asyncio.create_task(self.main_callback())
            # 添加延迟以允许任务启动或立即失败
            await asyncio.sleep(2)

            # 检查任务状态
            if self.download_task and self.download_task.done():
                # 任务已完成，检查是否有异常
                try:
                    if self.download_task.exception():
                        err = self.download_task.exception()
                        self.logger.error(f"自动启动下载任务失败: {err}", exc_info=True)
                        self.download_task = None # 如果立即失败，重置任务
                    else:
                        # 任务完成但没有异常（可能是正常完成）
                        self.logger.info("下载与监听任务已完成。")
                        self.download_task = None
                except Exception as e:
                    self.logger.error(f"检查自动下载任务状态时出错: {e}", exc_info=True)
                    self.download_task = None
            elif self.download_task:
                # 任务仍在运行中
                self.logger.info("下载与监听任务已自动启动。")
        else:
            self.logger.info("下载与监听任务已在运行中，无需自动启动。")

    async def _safe_edit_or_reply(self, message, text):
        """安全地编辑消息，如果编辑失败则发送新消息

        Args:
            message: 要编辑的消息对象
            text: 要设置的新文本

        Returns:
            编辑后的消息或新发送的消息
        """
        try:
            # 尝试编辑消息
            return await message.edit(text)
        except Exception as e:
            # 如果编辑失败，记录错误并发送新消息
            self.logger.warning(f"无法编辑消息: {e}，将发送新消息")
            try:
                # 尝试回复原始消息
                return await message.reply(text)
            except Exception as reply_err:
                # 如果回复也失败，记录错误
                self.logger.error(f"无法回复消息: {reply_err}")
                return None

    async def cleanup(self):
        """Perform cleanup actions before shutdown."""
        self.logger.info("Performing cleanup...")
        if self.download_task and not self.download_task.done():
            self.logger.info("Cancelling active download task...")
            self.download_task.cancel()
            try:
                await asyncio.wait_for(self.download_task, timeout=5.0)
                self.logger.info("Download task cancelled during cleanup.")
            except (asyncio.CancelledError, asyncio.TimeoutError):
                self.logger.warning("Download task did not fully stop during cleanup.")
            except Exception as e:
                 self.logger.error(f"Error cancelling download task during cleanup: {e}")
        if self.bot_client and self.bot_client.is_connected():
            self.logger.info("Disconnecting bot client...")
            await self.bot_client.disconnect()
            self.logger.info("Bot client disconnected.")
        self.logger.info("Cleanup complete.")
