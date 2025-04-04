#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
config_handler.py - Handles configuration commands
"""
import ast
import asyncio
from telethon import TelegramClient
from Meilisearch4TelegramSearchCKJ.src.utils.record_lastest_msg_id import load_config, save_config
from Meilisearch4TelegramSearchCKJ.src.utils.permissions import set_permission
from Meilisearch4TelegramSearchCKJ.src.config.env import reload_config

class ConfigHandler:
    """Handles commands for viewing and modifying configuration."""

    def __init__(self, bot_client: TelegramClient, logger):
        self.bot_client = bot_client
        self.logger = logger
        self.telegram_bot = None  # 将在TelegramBot类中设置，用于调用重启方法

    @set_permission
    async def handle_set_config(self, event) -> None:
        """Handles the /set command."""
        tokens = event.text.split(maxsplit=2) # Split into 3 parts: /set, key, value
        if len(tokens) < 3:
            await event.reply("用法: /set <key> <value>\n支持的 Key: white_list(wl), black_list, banned_words(bw), banned_ids(bi), incremental(inc)\nValue 必须是有效的 Python list/dict literal.")
            return

        # 分解命令、键和值
        _, key, value_str = tokens
        key = key.lower() # Normalize key

        try:
            # Use ast.literal_eval for safer evaluation of list/dict strings
            parsed_value = ast.literal_eval(value_str)
            config = load_config()
            config_updated = False

            if key in {'white_list', 'wl'}:
                if isinstance(parsed_value, list):
                    config['bot']['white_list'] = parsed_value
                    config_updated = True
                else: raise ValueError("white_list 必须是 list")
            elif key == 'black_list':
                 if isinstance(parsed_value, list):
                    config['bot']['black_list'] = parsed_value
                    config_updated = True
                 else: raise ValueError("black_list 必须是 list")
            elif key in {'banned_words', 'bw'}:
                 if isinstance(parsed_value, list):
                    config['bot']['banned_words'] = parsed_value
                    config_updated = True
                 else: raise ValueError("banned_words 必须是 list")
            elif key in {'banned_ids', 'bi'}:
                 if isinstance(parsed_value, list):
                     # Ensure IDs are integers
                     config['bot']['banned_ids'] = [int(i) for i in parsed_value]
                     config_updated = True
                 else: raise ValueError("banned_ids 必须是 list (包含数字)")
            elif key in {'incremental', 'inc'}:
                if isinstance(parsed_value, dict):
                     # Ensure keys are strings and values are integers
                     config['download_incremental'] = {str(k): int(v) for k, v in parsed_value.items()}
                     config_updated = True
                else: raise ValueError("incremental 必须是 dict (key: str, value: int)")
            else:
                await event.reply(f"未知配置项: {key}")
                return

            if config_updated:
                save_config(config)
                self.logger.info(f"配置项 {key} 已更新为: {parsed_value}")
                
                # 发送成功消息并提示将自动重启
                await event.reply(f"✅ 配置项 {key} 设置成功。将在3秒后自动重启以应用新配置...")
                
                # 如果telegram_bot已设置，则调用重启方法
                if self.telegram_bot:
                    # 创建一个延迟任务来执行重启，这样可以先返回消息给用户
                    asyncio.create_task(self._delayed_restart(event))
                else:
                    self.logger.warning("无法自动重启：telegram_bot引用未设置")
                    await event.reply("⚠️ 无法自动重启，请手动使用 /rs 命令重启。")
            else:
                 # Should not happen if logic is correct, but as a safeguard
                 await event.reply(f"未更新配置项 {key}。")

        except (ValueError, SyntaxError) as e:
            self.logger.error(f"设置配置项 {key} 出错: 无效的值 '{value_str}' - {e}", exc_info=True)
            await event.reply(f"设置配置项 {key} 失败: 无效的值。请确保提供有效的 Python literal (例如列表 `[1, 2]` 或字典 `{{'a': 1}}`)。错误: {e}")
        except Exception as e:
            self.logger.error(f"设置配置项 {key} 时发生意外错误: {e}", exc_info=True)
            await event.reply(f"设置配置时发生意外错误: {e}")


    @set_permission
    async def handle_list_config(self, event) -> None:
        """Handles the /list command."""
        try:
            config = load_config()
            # Use pretty printing for better readability, especially for lists/dicts
            import json
            config_str = json.dumps(config, indent=2, ensure_ascii=False)

            # Truncate if too long for a Telegram message
            max_len = 4000 # Slightly less than max to be safe
            if len(config_str) > max_len:
                 config_str = config_str[:max_len] + "\n... (配置过长，已截断)"

            await event.reply(f"```json\n{config_str}\n```", parse_mode='markdown')
            # Alternative simpler format:
            # await event.reply(
            #     f"当前配置:\n"
            #     f"\n白名单: {config['bot'].get('white_list', [])}"
            #     f"\n黑名单: {config['bot'].get('black_list', [])}"
            #     f"\n禁用关键词: {config['bot'].get('banned_words', [])}"
            #     f"\n禁用用户 ID: {config['bot'].get('banned_ids', [])}"
            #     f"\n增量下载偏移量: {config.get('download_incremental', {})}"
            # )
        except Exception as e:
            self.logger.error(f"获取配置出错: {e}", exc_info=True)
            await event.reply(f"获取配置出错: {e}")

    async def _delayed_restart(self, event):
        """在短暂停后执行重启操作"""
        try:
            # 等待3秒后执行重启
            await asyncio.sleep(3)

            # 创建一个虚拟事件对象来模拟用户发送的/rs命令
            # 这样可以复用现有的restart_download_and_listening方法
            # 创建一个消息通知用户正在重启
            restart_msg = await self.bot_client.send_message(
                event.chat_id, "⚙️ 正在自动重启以应用新配置..."
            )

            # 创建一个包含必要属性的虚拟事件对象
            fake_event = type('obj', (object,), {
                'reply': restart_msg.reply,
                'chat_id': event.chat_id,
                'sender_id': event.sender_id,  # 添加sender_id以通过权限检查
                'text': '/rs'  # 添加text属性以便在日志中显示正确的命令
            })

            # 调用TelegramBot的重启方法
            await self.telegram_bot.restart_download_and_listening(fake_event)

        except Exception as e:
            self.logger.error(f"自动重启时出错: {e}", exc_info=True)
            try:
                await self.bot_client.send_message(
                    event.chat_id, f"❌ 自动重启失败: {e}\n请手动使用 /rs 命令重启。"
                )
            except Exception as send_err:
                self.logger.error(f"发送重启失败消息时出错: {send_err}")
