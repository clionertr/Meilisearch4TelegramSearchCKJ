#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
callback_query_dispatcher.py - Dispatches callback queries to appropriate handlers
"""
import traceback # For logging callback errors more effectively

# Import handler types for type hinting (optional but good practice)
from .search_handler import SearchHandler
from .filter_handler import FilterHandler

class CallbackQueryDispatcher:
    """Dispatches callback queries based on their data prefix."""

    def __init__(self, logger, search_handler: SearchHandler, filter_handler: FilterHandler):
        self.logger = logger
        self.search_handler = search_handler
        self.filter_handler = filter_handler

    async def handle_callback(self, event) -> None:
        """Handles all button callback events."""
        try:
            data = event.data.decode('utf-8')
            self.logger.debug(f"收到回调数据: {data}")

            # --- Dispatching Logic ---
            if data.startswith('page_'):
                # Format: page_{query}_{page_number}
                parts = data.split('_', 2) # Split max 2 times
                if len(parts) == 3:
                    _, query, page_str = parts
                    try:
                        page_number = int(page_str)
                        await self.search_handler.handle_page_callback(event, query, page_number)
                    except ValueError:
                         self.logger.warning(f"无效的页码: {page_str} in callback data: {data}")
                         await event.answer("无效的翻页请求。", alert=True)
                else:
                     self.logger.warning(f"格式错误的翻页回调数据: {data}")
                     await event.answer("无效的翻页请求。", alert=True)

            elif data.startswith("ban_"):
                # Format: ban_yes_{user_id} or ban_no_{user_id}
                parts = data.split('_', 2)
                if len(parts) == 3:
                    _, confirm_str, user_id_str = parts
                    try:
                        user_id = int(user_id_str)
                        confirm = (confirm_str == "yes")
                        await self.filter_handler.handle_ban_callback(event, confirm, user_id)
                    except ValueError:
                        self.logger.warning(f"无效的用户 ID: {user_id_str} in callback data: {data}")
                        await event.answer("无效的用户ID。", alert=True)
                else:
                    self.logger.warning(f"格式错误的阻止回调数据: {data}")
                    await event.answer("无效的阻止请求。", alert=True)

            elif data.startswith("wl_add_"):
                # Format: wl_add_{chat_id}
                parts = data.split('_', 2)
                if len(parts) == 3:
                    _, _, chat_id_str = parts
                    try:
                        chat_id = int(chat_id_str)
                        await self.filter_handler.handle_whitelist_callback(event, chat_id)
                    except ValueError:
                        self.logger.warning(f"无效的聊天 ID: {chat_id_str} in callback data: {data}")
                        await event.answer("无效的聊天ID。", alert=True)
                else:
                    self.logger.warning(f"格式错误的白名单回调数据: {data}")
                    await event.answer("无效的白名单请求。", alert=True)

            elif data.startswith("bl_add_"):
                # Format: bl_add_{chat_id}
                parts = data.split('_', 2)
                if len(parts) == 3:
                    _, _, chat_id_str = parts
                    try:
                        chat_id = int(chat_id_str)
                        await self.filter_handler.handle_blacklist_callback(event, chat_id)
                    except ValueError:
                        self.logger.warning(f"无效的聊天 ID: {chat_id_str} in callback data: {data}")
                        await event.answer("无效的聊天ID。", alert=True)
                else:
                    self.logger.warning(f"格式错误的黑名单回调数据: {data}")
                    await event.answer("无效的黑名单请求。", alert=True)

            elif data.startswith("list_no_"):
                # Format: list_no_{chat_id}
                parts = data.split('_', 2)
                if len(parts) == 3:
                    _, _, chat_id_str = parts
                    try:
                        chat_id = int(chat_id_str)
                        await self.filter_handler.handle_list_no_callback(event, chat_id)
                    except ValueError:
                        self.logger.warning(f"无效的聊天 ID: {chat_id_str} in callback data: {data}")
                        await event.answer("无效的聊天ID。", alert=True)
                else:
                    self.logger.warning(f"格式错误的名单拒绝回调数据: {data}")
                    await event.answer("无效的名单拒绝请求。", alert=True)

            elif data.startswith("d`"): # Using ` as delimiter from filter_handler
                 # Format: d`y`{repr_list} or d`n`
                 confirm_char = data[2] # 'y' or 'n'
                 if confirm_char == 'y' and len(data) > 3:
                      keywords_repr = data[3:]
                      await self.filter_handler.handle_delete_callback(event, confirm=True, keywords_repr=keywords_repr)
                 elif confirm_char == 'n':
                      await self.filter_handler.handle_delete_callback(event, confirm=False, keywords_repr="") # No keywords needed for 'no'
                 else:
                     self.logger.warning(f"格式错误的删除回调数据: {data}")
                     await event.answer("无效的删除请求。", alert=True)

            # elif data == "noop": # Example for handling no-operation buttons like page display
            #     await event.answer() # Just acknowledge

            else:
                self.logger.info(f"未处理的回调数据: {data}")
                await event.answer("此按钮没有关联的操作或已过期。", alert=True)

        except Exception as e:
             # Log detailed traceback for callback errors
             self.logger.error(f"处理回调查询时发生意外错误: {e}\nData: {event.data.decode('utf-8', errors='ignore')}\n{traceback.format_exc()}")
             # Try to inform the user without revealing internal details
             try:
                  await event.answer("处理您的请求时发生内部错误。", alert=True)
             except Exception:
                  pass # Ignore if answering fails

