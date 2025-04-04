#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
filter_handler.py - Handles banning, filtering, and deletion logic
"""
import ast
from telethon import Button, TelegramClient
from telethon.tl.types import PeerUser
from Meilisearch4TelegramSearchCKJ.src.config.env import BANNED_WORDS # Import default if needed
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
            keywords_repr = repr(target_keyword_list) # Safe representation for callback data

            text = f"❓ 确认删除所有包含以下任一关键词的文档？\n{', '.join(display_keywords)}"
            buttons = [
                Button.inline("是，删除", data=f"d`y`{keywords_repr}"), # Use repr for safe encoding
                Button.inline("否，取消", data=f"d`n`")
            ]
            await event.reply(text, buttons=buttons, parse_mode='markdown')

        except Exception as e:
            self.logger.error(f"准备 /delete 命令时出错: {e}", exc_info=True)
            await event.reply(f"处理 /delete 命令时出错: {e}")

    # --- Event Handlers ---

    async def handle_forwarded_message(self, event) -> None:
        """Handles forwarded messages to potentially ban the original sender."""
        if not event.is_private or not event.fwd_from or not event.fwd_from.from_id:
            return # Only handle private chats with valid forward info

        # Check if the sender is a user (not a channel)
        if not isinstance(event.fwd_from.from_id, PeerUser):
            # Optionally log or inform the user
            # self.logger.debug("Forwarded message is not from a user.")
            # await event.reply("⚠️ 仅支持对来自用户的转发消息执行操作。")
            return

        try:
            from_user_id = event.fwd_from.from_id.user_id
            # Maybe get user info for display?
            # user = await self.bot_client.get_entity(from_user_id)
            # display_name = user.first_name + (f" {user.last_name}" if user.last_name else "")

            # Check if already banned before asking
            config = load_config()
            if from_user_id in config['bot'].get('banned_ids', []):
                 await event.reply(f"ℹ️ 用户 `{from_user_id}` 已在阻止名单中。", parse_mode='markdown')
                 return

            text = f"❓ 是否将转发来源用户 `{from_user_id}` 添加到阻止名单？"
            buttons = [
                Button.inline("是", data=f"ban_yes_{from_user_id}"),
                Button.inline("否", data=f"ban_no_{from_user_id}")
            ]
            await event.reply(text, buttons=buttons, parse_mode='markdown')

        except AttributeError:
            # Should be caught by initial checks, but as safeguard
            self.logger.warning("无法从转发消息中获取 user_id。")
            # await event.reply("❌ 无法获取来源用户信息。")
        except Exception as e:
             self.logger.error(f"处理转发消息时出错: {e}", exc_info=True)
             # Avoid crashing, maybe just log


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


    async def handle_delete_callback(self, event, confirm: bool, keywords_repr: str) -> None:
        """Handles the delete confirmation callback."""
        if not confirm:
            await event.edit("已取消删除。")
            return

        try:
            # Safely evaluate the keyword list representation
            delete_list = ast.literal_eval(keywords_repr)
            if not isinstance(delete_list, list):
                 raise ValueError("Invalid format for delete list in callback")

            self.logger.info(f"开始删除包含关键词 {delete_list} 的文档")
            await event.edit(f"⏳ 正在删除包含以下关键词的文档：{', '.join(f'`{k}`' for k in delete_list)} ...", parse_mode='markdown')

            # Perform deletion (consider doing this in chunks or background task if large)
            # MeiliSearch delete is usually fast, but might block if deleting millions
            tasks = []
            total_deleted_count = 0 # Optional: track count

            # Note: Meilisearch `delete_documents_by_filter` might be more efficient
            # if you can construct a filter like `text CONTAINS 'word1' OR text CONTAINS 'word2'`
            # However, `delete_all_contain_keyword` seems to use search then delete IDs,
            # which might be okay. Let's stick to the original logic pattern.

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

            # Consider waiting for tasks if the delete method was async and returned tasks
            # await asyncio.gather(*tasks)

            await event.edit(f"✅ 已完成删除包含指定关键词的文档的任务。") # Edit confirmation

        except (SyntaxError, ValueError) as e:
             self.logger.error(f"解析删除回调数据出错: {keywords_repr} - {e}", exc_info=True)
             await event.answer("处理删除请求时出错 (数据格式无效)。", alert=True)
        except Exception as e:
            self.logger.error(f"处理 delete 回调出错: {e}", exc_info=True)
            await event.answer(f"删除文档时发生错误: {e}", alert=True)

