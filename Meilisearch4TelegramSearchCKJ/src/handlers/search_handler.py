#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
search_handler.py - Handles search functionality
"""
import asyncio
import gc
from typing import Dict, List, Optional

from telethon import Button, TelegramClient, events
from Meilisearch4TelegramSearchCKJ.src.config.env import (
    CACHE_EXPIRE_SECONDS, MAX_PAGE, RESULTS_PER_PAGE, SEARCH_CACHE
)
from Meilisearch4TelegramSearchCKJ.src.models.meilisearch_handler import MeiliSearchClient
from Meilisearch4TelegramSearchCKJ.src.utils.permissions import set_permission

MAX_RESULTS = MAX_PAGE * RESULTS_PER_PAGE

class SearchHandler:
    """Handles search commands, direct message searches, caching, and results display."""

    def __init__(self, bot_client: TelegramClient, meili: MeiliSearchClient, logger):
        self.bot_client = bot_client
        self.meili = meili
        self.logger = logger
        self.search_results_cache: Dict[str, Optional[List[Dict]]] = {} # Use Optional for clarity

    # --- Command Handlers ---

    @set_permission
    async def handle_search_command(self, event) -> None:
        """Handles the /search command."""
        query = event.pattern_match.group(1)
        self.logger.info(f"收到搜索指令: {query}")
        await self._perform_search(event, query)

    @set_permission
    async def handle_message_search(self, event) -> None:
        """Handles non-command private messages as search queries."""
        self.logger.info(f"收到消息搜索: {event.raw_text}")
        await self._perform_search(event, event.raw_text)

    @set_permission
    async def handle_clean_cache_command(self, event) -> None:
        """Handles the /cc command to clear the search cache."""
        self.search_results_cache.clear()
        await event.reply("缓存已清理。")
        self.logger.info("缓存清理完成")
        gc.collect()

    # --- Core Search Logic ---

    async def _perform_search(self, event, query: str) -> None:
        """Performs the search, using cache if enabled, and sends results."""
        try:
            results = None
            cache_hit = False
            if SEARCH_CACHE and query in self.search_results_cache:
                results = self.search_results_cache[query]
                # Check if cache entry might be None due to previous error or cleanup race condition
                if results is not None:
                    self.logger.info(f"从缓存中获取搜索结果: '{query}'")
                    cache_hit = True

            if not cache_hit:
                results = await self._get_search_results_from_meili(query, limit=MAX_RESULTS)
                if SEARCH_CACHE:
                    self.search_results_cache[query] = results # Store even if empty to cache "no results"
                    # Schedule cleanup only if results were successfully fetched
                    if results is not None:
                         asyncio.create_task(self._schedule_cache_cleanup(query))

            if results: # Check if results is not None and not empty
                await self._send_results_page(event, results, 0, query)
            elif results == []: # Explicitly check for empty list (successful search, no hits)
                 await event.reply("没有找到相关结果。")
            else: # results is None (indicates an error during fetch)
                await event.reply("搜索时发生错误，请稍后重试。") # More specific error handled in _get_search_results

        except Exception as e:
            self.logger.error(f"搜索处理出错 for query '{query}': {e}", exc_info=True)
            await event.reply(f"处理搜索请求时发生意外错误: {e}")

    async def _get_search_results_from_meili(self, query: str, limit: int = 10, offset: int = 0, index_name: str = 'telegram') -> Optional[List[Dict]]:
        """Fetches search results from MeiliSearch, returns None on error."""
        try:
            results = self.meili.search(query, index_name, limit=limit, offset=offset)
            # Ensure 'hits' exists, default to empty list if not
            return results.get('hits', [])
        except Exception as e:
            self.logger.error(f"MeiliSearch 搜索错误 for query '{query}': {e}", exc_info=True)
            # Return None to indicate an error occurred during the search itself
            return None

    # --- Cache Management ---

    async def _schedule_cache_cleanup(self, key: str) -> None:
        """Schedules the removal of a specific cache key after a delay."""
        await asyncio.sleep(CACHE_EXPIRE_SECONDS)
        try:
            if key in self.search_results_cache:
                del self.search_results_cache[key]
                self.logger.info(f"缓存 {key} 已过期并删除")
                gc.collect() # Optional: collect garbage after removing potentially large item
        except KeyError:
             self.logger.debug(f"试图删除缓存 {key} 时，它已不存在。") # Already deleted or cleaned
        except Exception as e:
            self.logger.error(f"删除缓存 {key} 出错: {e}", exc_info=True)

    # --- Results Formatting and Display ---

    def _format_result(self, hit: Dict) -> str:
        """Formats a single search hit for display."""
        text = hit.get('text', '')
        text = text.replace('**', '').replace('__', '').replace('[', '').replace(']', '').replace('`', '') # Basic sanitization
        text = (text[:360].strip() + "...") if len(text) > 360 else text

        chat = hit.get('chat', {})
        chat_type = chat.get('type', 'private')
        chat_title_prefix = "Private" if chat_type == 'private' else chat_type.capitalize()
        chat_identifier = chat.get('username') or chat.get('title') or 'N/A'
        chat_title = f"{chat_title_prefix}: {chat_identifier}"

        parts = hit.get('id', '').split('-')
        url = ""
        if len(parts) >= 2:
            try:
                # Validate parts are numeric before formatting URL
                numeric_part0 = int(str(parts[0]).replace('-100','')) # Handle channel/supergroup ID format
                numeric_part1 = int(parts[1])
                if chat_type == 'private':
                    url = f"tg://openmessage?user_id={numeric_part0}&message_id={numeric_part1}"
                else:
                    # Use the channel/supergroup ID format for c/ link
                     url = f"https://t.me/c/{numeric_part0}/{numeric_part1}"
            except ValueError:
                 self.logger.warning(f"Invalid ID parts for URL generation: {parts}")


        date = hit.get('date', '').split('T')[0]

        # Ensure URL is properly formatted for Markdown only if it exists
        link_md = f'[🔗跳转]({url})' if url else ''
        return f"- **{chat_title}** ({date})\n{text}\n{link_md}\n{'—' * 18}\n"


    def _get_pagination_buttons(self, query: str, page_number: int, total_hits: int) -> List[Button]:
        """Generates pagination buttons."""
        buttons = []
        has_prev = page_number > 0
        has_next = (page_number + 1) * RESULTS_PER_PAGE < total_hits

        # Optimization: only add buttons if needed
        if has_prev:
            buttons.append(Button.inline("⬅️ 上一页", data=f"page_{query}_{page_number - 1}"))
        if has_next:
            buttons.append(Button.inline("下一页 ➡️", data=f"page_{query}_{page_number + 1}"))

        # Consider adding a close button or page number display if complex
        # if buttons:
        #     buttons.append(Button.inline(f"📄 {page_number + 1}", data="noop")) # Example: display page number

        return buttons

    async def _send_results_page(self, event, hits: List[Dict], page_number: int, query: str) -> None:
        """Sends a new message with a page of search results."""
        start_index = page_number * RESULTS_PER_PAGE
        end_index = start_index + RESULTS_PER_PAGE # No need for min with slicing
        page_results = hits[start_index:end_index]

        if not page_results:
            # This case should ideally be handled before calling send/edit
            self.logger.warning(f"Attempted to send empty page {page_number} for query '{query}'")
            # Avoid sending an empty message, maybe reply?
            # await event.reply("没有更多结果了。") # Or just log and do nothing
            return

        response_text = "".join(self._format_result(hit) for hit in page_results)
        total_pages = (len(hits) + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE
        message_header = f"🔍 搜索 \"{query}\" (第 {page_number + 1}/{total_pages} 页):\n"
        buttons = self._get_pagination_buttons(query, page_number, len(hits))

        try:
            await self.bot_client.send_message(
                event.chat_id,
                message_header + response_text,
                buttons=buttons or None, # Explicitly pass None if empty
                parse_mode='markdown' # Enable markdown parsing
            )
        except Exception as e:
             self.logger.error(f"发送结果页失败 for query '{query}', page {page_number}: {e}", exc_info=True)
             # Fallback or inform user
             try:
                 await event.reply(f"发送结果时出错。请尝试缩小搜索范围。错误: {e}")
             except Exception:
                 pass # Ignore reply error


    async def _edit_results_page(self, event, hits: List[Dict], page_number: int, query: str) -> None:
        """Edits an existing message to show a different page of results."""
        if hits is None:
             # This might happen if cache expired between initial send and pagination click
             self.logger.warning(f"Attempted to edit page for query '{query}' but results were None (likely cache expiry).")
             try:
                await event.edit("搜索结果已过期，请重新搜索。")
             except Exception:
                 pass # Ignore edit error
             return

        start_index = page_number * RESULTS_PER_PAGE
        end_index = start_index + RESULTS_PER_PAGE
        page_results = hits[start_index:end_index]

        if not page_results:
            # This might happen if the user clicks 'next' on the very last page somehow
            # or if the total hits changed.
            self.logger.warning(f"Attempted to edit to empty page {page_number} for query '{query}'")
            try:
                # Keep the last known good page or inform user?
                await event.answer("没有更多结果了。") # Use answer for callbacks
            except Exception:
                pass
            return

        response_text = "".join(self._format_result(hit) for hit in page_results)
        total_pages = (len(hits) + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE
        new_message = f"🔍 搜索 \"{query}\" (第 {page_number + 1}/{total_pages} 页):\n{response_text}"
        buttons = self._get_pagination_buttons(query, page_number, len(hits))

        try:
            await event.edit(
                new_message,
                buttons=buttons or None,
                parse_mode='markdown'
            )
        except Exception as e:
            if "Message not modified" in str(e):
                self.logger.debug(f"消息未修改 for query '{query}', page {page_number}.")
                # Optionally answer the callback to remove the loading state
                try: await event.answer()
                except Exception: pass
            elif "MESSAGE_ID_INVALID" in str(e):
                 self.logger.warning(f"编辑消息失败 (ID 无效) for query '{query}', page {page_number}. 可能已被删除。")
                 # Cannot edit, maybe send a new message? Or just fail silently.
                 try: await event.answer("无法编辑原消息，可能已被删除。", alert=True)
                 except Exception: pass
            else:
                self.logger.error(f"编辑结果页出错 for query '{query}', page {page_number}: {e}", exc_info=True)
                # Try editing without markdown as a fallback
                try:
                     await event.edit(
                        new_message.replace('**','').replace('*','').replace('`','').replace('[','').replace(']',''), # Basic plain text
                        buttons=buttons or None
                    )
                except Exception as fallback_e:
                    self.logger.error(f"纯文本编辑也失败: {fallback_e}", exc_info=True)
                    try:
                        await event.answer(f"编辑结果页时出错: {e}", alert=True)
                    except Exception:
                        pass # Ignore answer error

    # --- Callback Handling (Specific to Search) ---

    async def handle_page_callback(self, event, query: str, page_number: int) -> None:
        """Handles pagination button clicks."""
        try:
            results = None
            cache_hit = False
            # 1. Try cache first
            if SEARCH_CACHE and query in self.search_results_cache:
                results = self.search_results_cache.get(query)
                if results is not None:
                    cache_hit = True
                    self.logger.info(f"翻页: 从缓存获取 '{query}'")


            # 2. If not in cache or cache disabled, fetch fresh
            if not cache_hit:
                 self.logger.info(f"翻页: 缓存未命中或禁用，重新获取 '{query}'")
                 results = await self._get_search_results_from_meili(query, limit=MAX_RESULTS)
                 if SEARCH_CACHE and results is not None: # Only cache if fetch succeeded
                     self.search_results_cache[query] = results
                     asyncio.create_task(self._schedule_cache_cleanup(query))

            # 3. Edit the message
            if results is not None:
                 # Show loading state (optional but good UX)
                 try: await event.edit(f"正在加载 \"{query}\" 第 {page_number + 1} 页...")
                 except Exception: pass # Ignore if edit fails here

                 await self._edit_results_page(event, results, page_number, query)
            else:
                 # Fetch failed
                  await event.answer("无法获取搜索结果，请重试。", alert=True)

        except ValueError:
             self.logger.warning(f"无效的翻页数据 received: {event.data.decode('utf-8')}")
             await event.answer("无效的翻页请求。", alert=True)
        except Exception as e:
            self.logger.error(f"处理翻页回调出错 for query '{query}', page {page_number}: {e}", exc_info=True)
            await event.answer(f"处理翻页时发生错误: {e}", alert=True)