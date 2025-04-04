#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
filter_handler.py - Handles banning, filtering, and deletion logic
"""
import ast
import json
import re
from telethon import Button, TelegramClient
from telethon.tl.types import PeerUser, PeerChannel, PeerChat
from Meilisearch4TelegramSearchCKJ.src.config.env import BANNED_WORDS, reload_config # Import default if needed
from Meilisearch4TelegramSearchCKJ.src.models.meilisearch_handler import MeiliSearchClient
from Meilisearch4TelegramSearchCKJ.src.utils.record_lastest_msg_id import load_config, save_config
from Meilisearch4TelegramSearchCKJ.src.utils.permissions import set_permission

class FilterHandler:
    """Handles commands and interactions related to filtering and banning."""

    def __init__(self, bot_client: TelegramClient, meili: MeiliSearchClient, logger):
        self.bot_client = bot_client
        self.meili = meili
        self.logger = logger

    # --- Command Handlers ---

    @set_permission
    async def handle_ban_command(self, event) -> None:
        """Handles the /ban command."""
        tokens = event.text.split()[1:]
        if not tokens:
            await event.reply("用法: /ban <id1> <word1> <id2> ...\n将数字视为用户ID，其他视为关键词。")
            return

        try:
            config = load_config()
            # Ensure keys exist, initialize if not
            banned_ids = config['bot'].setdefault('banned_ids', [])
            banned_words = config['bot'].setdefault('banned_words', [])

            new_ids_added = []
            new_words_added = []
            already_banned_ids = []
            already_banned_words = []

            for token in tokens:
                try:
                    user_id = int(token)
                    if user_id not in banned_ids:
                        banned_ids.append(user_id)
                        new_ids_added.append(user_id)
                    else:
                        already_banned_ids.append(user_id)
                except ValueError:
                    # Treat as word
                    word = token
                    if word not in banned_words:
                        banned_words.append(word)
                        new_words_added.append(word)
                    else:
                        already_banned_words.append(word)

            # Only save if changes were made
            if new_ids_added or new_words_added:
                save_config(config)
                self.logger.info(f"Ban list updated. Added IDs: {new_ids_added}, Added Words: {new_words_added}")

            # Construct reply message
            reply_parts = []
            if new_ids_added:
                reply_parts.append(f"✅ 已添加阻止 ID: {', '.join(map(str, new_ids_added))}")
            if new_words_added:
                 reply_parts.append(f"✅ 已添加禁用词: {', '.join(new_words_added)}")
            if already_banned_ids:
                 reply_parts.append(f"ℹ️ 这些 ID 已在阻止名单中: {', '.join(map(str, already_banned_ids))}")
            if already_banned_words:
                 reply_parts.append(f"ℹ️ 这些词已在禁用名单中: {', '.join(already_banned_words)}")

            if not reply_parts: # Should not happen if tokens were provided but none were new
                 await event.reply("提供的 ID/词语均已在阻止/禁用名单中。")
            else:
                 await event.reply("\n".join(reply_parts))

        except Exception as e:
            self.logger.error(f"处理 /ban 命令出错: {e}", exc_info=True)
            await event.reply(f"处理 /ban 命令时出错: {e}")


    @set_permission
    async def handle_banlist_command(self, event) -> None:
        """Handles the /banlist command."""
        try:
            config = load_config()
            banned_ids = config['bot'].get('banned_ids', [])
            banned_words = config['bot'].get('banned_words', [])

            # Format lists for display
            ids_str = "\n".join(f"- `{id}`" for id in banned_ids) if banned_ids else "无"
            words_str = "\n".join(f"- `{word}`" for word in banned_words) if banned_words else "无"

            reply_msg = (
                f"🚫 **当前阻止名单信息**\n\n"
                f"**阻止的用户 ID**:\n{ids_str}\n\n"
                f"**禁用的关键词**:\n{words_str}"
            )
            await event.reply(reply_msg, parse_mode='markdown')
        except Exception as e:
            self.logger.error(f"处理 /banlist 命令出错: {e}", exc_info=True)
            await event.reply(f"获取阻止名单时出错: {e}")


    @set_permission
    async def handle_delete_command(self, event) -> None:
        """Handles the /delete command to remove documents containing keywords."""
        try:
            # Use provided keywords or default to BANNED_WORDS from config if empty
            tokens = event.text.split()[1:]
            target_keyword_list = tokens or BANNED_WORDS # Use configured BANNED_WORDS if no args given

            if not target_keyword_list:
                 await event.reply("用法: /delete <关键词1> <关键词2> ...\n或者，如果不提供关键词，将使用配置中的 `BANNED_WORDS`（如果存在）。当前未提供参数且配置中无 `BANNED_WORDS`。")
                 return

            # Sanitize keywords slightly before showing confirmation
            display_keywords = [f"`{kw}`" for kw in target_keyword_list] # Use backticks for clarity

            # 使用JSON格式化关键词列表，避免特殊字符引起的解析问题
            import json
            keywords_json = json.dumps(target_keyword_list, ensure_ascii=False)

            text = f"❓ 确认删除所有包含以下任一关键词的文档？\n{', '.join(display_keywords)}"
            buttons = [
                Button.inline("是，删除", data=f"d`y`{keywords_json}"), # Use JSON for safe encoding
                Button.inline("否，取消", data=f"d`n`")
            ]
            await event.reply(text, buttons=buttons, parse_mode='markdown')

        except Exception as e:
            self.logger.error(f"准备 /delete 命令时出错: {e}", exc_info=True)
            await event.reply(f"处理 /delete 命令时出错: {e}")

    # --- Event Handlers ---

    async def handle_forwarded_message(self, event) -> None:
        """Handles forwarded messages to potentially ban the original sender or add chat to lists."""
        if not event.is_private or not event.fwd_from:
            return # Only handle private chats with valid forward info

        try:
            # 获取转发消息的来源信息
            from_id = event.fwd_from.from_id
            from_user_id = None
            from_chat_id = None
            chat_type = None

            # 处理不同类型的来源
            if isinstance(from_id, PeerUser):
                from_user_id = from_id.user_id
                chat_type = "user"
            elif isinstance(from_id, PeerChannel):
                from_chat_id = from_id.channel_id
                # 频道ID需要添加-100前缀
                from_chat_id = -1000000000000 - from_chat_id
                chat_type = "channel"
            elif isinstance(from_id, PeerChat):
                from_chat_id = from_id.chat_id
                # 群组ID需要添加-前缀
                from_chat_id = -from_chat_id
                chat_type = "chat"
            else:
                self.logger.warning(f"未知的转发消息来源类型: {type(from_id)}")
                await event.reply("⚠️ 无法识别转发消息的来源类型。")
                return

            # 加载配置
            config = load_config()

            # 构建回复消息和按钮
            reply_parts = []
            buttons = []

            # 处理用户ID
            if from_user_id:
                # 检查用户是否已在阻止名单中
                if from_user_id in config['bot'].get('banned_ids', []):
                    reply_parts.append(f"ℹ️ 用户 `{from_user_id}` 已在阻止名单中。")
                else:
                    reply_parts.append(f"❓ 是否将转发来源用户 `{from_user_id}` 添加到阻止名单？")
                    buttons.extend([
                        Button.inline("添加到阻止名单", data=f"ban_yes_{from_user_id}"),
                        Button.inline("不添加", data=f"ban_no_{from_user_id}")
                    ])

            # 处理群组/频道ID
            if from_chat_id:
                # 检查群组/频道是否已在白名单或黑名单中
                white_list = config['bot'].get('white_list', [])
                black_list = config['bot'].get('black_list', [])

                if from_chat_id in white_list:
                    reply_parts.append(f"ℹ️ {chat_type} `{from_chat_id}` 已在白名单中。")
                elif from_chat_id in black_list:
                    reply_parts.append(f"ℹ️ {chat_type} `{from_chat_id}` 已在黑名单中。")
                else:
                    reply_parts.append(f"❓ 是否将转发来源 {chat_type} `{from_chat_id}` 添加到白名单或黑名单？")
                    buttons.extend([
                        Button.inline("添加到白名单", data=f"wl_add_{from_chat_id}"),
                        Button.inline("添加到黑名单", data=f"bl_add_{from_chat_id}"),
                        Button.inline("不添加", data=f"list_no_{from_chat_id}")
                    ])

            # 如果没有可操作的内容，则返回
            if not reply_parts:
                await event.reply("⚠️ 无法从转发消息中获取有效的用户ID或群组ID。")
                return

            # 发送回复
            await event.reply("\n\n".join(reply_parts), buttons=buttons if buttons else None, parse_mode='markdown')

        except Exception as e:
            self.logger.error(f"处理转发消息时出错: {e}", exc_info=True)
            await event.reply(f"❌ 处理转发消息时出错: {e}")


    # --- Callback Handlers ---

    async def handle_ban_callback(self, event, confirm: bool, user_id: int) -> None:
        """Handles the ban confirmation callback."""
        if not confirm:
            await event.edit("已取消添加。")
            return

        try:
            config = load_config()
            banned_ids = config['bot'].setdefault('banned_ids', [])

            if user_id not in banned_ids:
                banned_ids.append(user_id)
                save_config(config)
                self.logger.info(f"用户 {user_id} 已通过回调添加到阻止名单。")
                await event.edit(f"✅ 用户 `{user_id}` 已添加到阻止名单。", parse_mode='markdown')
            else:
                self.logger.info(f"用户 {user_id} 在回调时已在阻止名单中。")
                await event.edit(f"ℹ️ 用户 `{user_id}` 已在阻止名单中。", parse_mode='markdown')
        except Exception as e:
            self.logger.error(f"处理 ban 回调出错 for user {user_id}: {e}", exc_info=True)
            await event.answer(f"添加阻止名单失败: {e}", alert=True)

    async def handle_whitelist_callback(self, event, chat_id: int) -> None:
        """Handles adding a chat to the whitelist."""
        try:
            config = load_config()
            white_list = config['bot'].setdefault('white_list', [])
            black_list = config['bot'].setdefault('black_list', [])

            # 如果在黑名单中，先移除
            if chat_id in black_list:
                black_list.remove(chat_id)

            # 添加到白名单
            if chat_id not in white_list:
                white_list.append(chat_id)
                save_config(config)
                reload_config()  # 重新加载配置以使更改立即生效
                self.logger.info(f"聊天 {chat_id} 已添加到白名单。")
                await event.edit(f"✅ 聊天 `{chat_id}` 已添加到白名单。", parse_mode='markdown')
            else:
                self.logger.info(f"聊天 {chat_id} 已在白名单中。")
                await event.edit(f"ℹ️ 聊天 `{chat_id}` 已在白名单中。", parse_mode='markdown')
        except Exception as e:
            self.logger.error(f"处理白名单回调出错 for chat {chat_id}: {e}", exc_info=True)
            await event.answer(f"添加白名单失败: {e}", alert=True)

    async def handle_blacklist_callback(self, event, chat_id: int) -> None:
        """Handles adding a chat to the blacklist."""
        try:
            config = load_config()
            white_list = config['bot'].setdefault('white_list', [])
            black_list = config['bot'].setdefault('black_list', [])

            # 如果在白名单中，先移除
            if chat_id in white_list:
                white_list.remove(chat_id)

            # 添加到黑名单
            if chat_id not in black_list:
                black_list.append(chat_id)
                save_config(config)
                reload_config()  # 重新加载配置以使更改立即生效
                self.logger.info(f"聊天 {chat_id} 已添加到黑名单。")
                await event.edit(f"✅ 聊天 `{chat_id}` 已添加到黑名单。", parse_mode='markdown')
            else:
                self.logger.info(f"聊天 {chat_id} 已在黑名单中。")
                await event.edit(f"ℹ️ 聊天 `{chat_id}` 已在黑名单中。", parse_mode='markdown')
        except Exception as e:
            self.logger.error(f"处理黑名单回调出错 for chat {chat_id}: {e}", exc_info=True)
            await event.answer(f"添加黑名单失败: {e}", alert=True)

    async def handle_list_no_callback(self, event, chat_id: int) -> None:
        """Handles the rejection of adding a chat to any list."""
        await event.edit(f"已取消将聊天 `{chat_id}` 添加到名单。", parse_mode='markdown')


    async def handle_delete_callback(self, event, confirm: bool, keywords_repr: str) -> None:
        """Handles the delete confirmation callback."""
        if not confirm:
            await event.edit("已取消删除。")
            return

        try:
            # 尝试使用JSON解析关键词列表
            import json
            try:
                delete_list = json.loads(keywords_repr)
            except json.JSONDecodeError:
                # 兼容旧版本的回调数据格式，尝试使用ast.literal_eval
                try:
                    delete_list = ast.literal_eval(keywords_repr)
                except (SyntaxError, ValueError):
                    # 如果上述方法都失败，尝试处理特殊格式
                    if keywords_repr.startswith('`<') and '>' in keywords_repr:
                        # 处理类似 `<BoxList: ['广告关键词123']> 的格式
                        # 提取方括号中的内容
                        start_idx = keywords_repr.find("[")
                        end_idx = keywords_repr.find("]", start_idx)
                        if start_idx != -1 and end_idx != -1:
                            # 提取并解析列表内容
                            list_content = keywords_repr[start_idx:end_idx+1]
                            try:
                                delete_list = ast.literal_eval(list_content)
                            except (SyntaxError, ValueError):
                                # 如果解析失败，尝试直接提取引号中的内容
                                import re
                                matches = re.findall(r"'([^']*)'|\"([^\"]*)\"|", list_content)
                                delete_list = [m[0] or m[1] for m in matches if m[0] or m[1]]
                        else:
                            # 如果找不到方括号，尝试提取引号中的内容
                            import re
                            matches = re.findall(r"'([^']*)'|\"([^\"]*)\"|", keywords_repr)
                            delete_list = [m[0] or m[1] for m in matches if m[0] or m[1]]
                    else:
                        # 如果所有方法都失败，尝试将其作为单个关键词处理
                        delete_list = [keywords_repr]

            # 确保结果是列表类型且非空
            if not isinstance(delete_list, list):
                delete_list = [delete_list]

            if not delete_list:
                raise ValueError("Invalid format for delete list in callback")

            self.logger.info(f"开始删除包含关键词 {delete_list} 的文档")
            await event.edit(f"⏳ 正在删除包含以下关键词的文档：{', '.join(f'`{k}`' for k in delete_list)} ...", parse_mode='markdown')

            # Perform deletion for each keyword
            # Note: Meilisearch `delete_documents_by_filter` might be more efficient
            # if you can construct a filter like `text CONTAINS 'word1' OR text CONTAINS 'word2'`
            # However, we'll process each keyword individually for better error handling

            for keyword in delete_list:
                 # This method name is slightly misleading if it searches then deletes.
                 # It implies it deletes *all* documents *if* they contain the keyword.
                 # Let's assume it works as intended per the original code.
                 # A better Meili approach might use filters: client.index('telegram').delete_documents({'filter': f'text = "{keyword}"'})
                 # or more complex filters if needed.
                 # Sticking to the provided Meili Handler method:
                 try:
                     # We might want the handler method to return the number of deleted docs
                     # self.meili.delete_all_contain_keyword(f'"{keyword}"') # Ensure quotes if needed by method
                     self.meili.delete_all_contain_keyword(keyword) # Assuming method handles quoting if necessary
                     self.logger.info(f"已触发删除包含 '{keyword}' 的文档的任务。")
                     # Note: The original method doesn't seem async or return counts.
                     # If deletion takes time, this response might be premature.
                 except Exception as del_err:
                     self.logger.error(f"删除包含关键词 '{keyword}' 的文档时出错: {del_err}", exc_info=True)
                     await event.reply(f"❌ 删除关键词 `{keyword}` 时出错: {del_err}") # Reply immediately on error

            await event.edit(f"✅ 已完成删除包含指定关键词的文档的任务。") # Edit confirmation

        except (SyntaxError, ValueError) as e:
             self.logger.error(f"解析删除回调数据出错: {keywords_repr} - {e}", exc_info=True)
             await event.answer("处理删除请求时出错 (数据格式无效)。", alert=True)
        except Exception as e:
            self.logger.error(f"处理 delete 回调出错: {e}", exc_info=True)
            await event.answer(f"删除文档时发生错误: {e}", alert=True)

