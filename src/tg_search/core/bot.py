import ast
import asyncio
import gc
from collections.abc import Awaitable
from typing import Any, cast

from telethon import Button, TelegramClient, events
from telethon.tl.functions.bots import SetBotCommandsRequest
from telethon.tl.types import BotCommand, BotCommandScopeDefault

from tg_search.config.settings import (
    APP_HASH,
    APP_ID,
    CACHE_EXPIRE_SECONDS,
    MAX_PAGE,
    OWNER_IDS,
    PROXY,
    RESULTS_PER_PAGE,
    SEARCH_CACHE,
    TOKEN,
    IPv6,
)
from tg_search.core.logger import setup_logger
from tg_search.services import DomainError
from tg_search.services.container import ServiceContainer, build_service_container
from tg_search.utils.formatters import sizeof_fmt

MAX_RESULTS = MAX_PAGE * RESULTS_PER_PAGE


# TODO
# 1. 加速未缓存时的搜索速度
# 3. 优化代码逻辑和结构


def set_permission(func):
    """装饰器：检查用户是否在白名单中"""

    async def wrapper(self, event, *args, **kwargs):
        user_id = event.sender_id
        if not OWNER_IDS or user_id in OWNER_IDS:
            await func(self, event, *args, **kwargs)
        else:
            await event.respond("你没有权限使用此指令。")
            self.logger.info(f"User {user_id} tried to use command {event.text}, but does not have permission.")

    return wrapper


class BotHandler:
    def __init__(
        self,
        main,
        *,
        services: ServiceContainer | None = None,
    ):
        self.logger = setup_logger()
        proxy: Any = PROXY
        self.bot_client = TelegramClient(
            "session/bot",
            APP_ID,
            APP_HASH,
            use_ipv6=IPv6,
            proxy=proxy,
            auto_reconnect=True,
            connection_retries=5,
        )
        self.services = services or build_service_container()
        self.meili = self.services.meili_client
        self.policy_service = self.services.config_policy_service
        self.runtime_control_service = self.services.runtime_control_service
        self.search_results_cache = {}
        self.main = main

    @staticmethod
    def _domain_error_to_text(exc: DomainError) -> str:
        if exc.code == "policy_invalid_ids":
            return "参数错误：请输入非空整数列表，如 [123, 456]"
        if exc.code == "policy_version_conflict":
            return "写入冲突，请稍后重试"
        if exc.code == "policy_store_unavailable":
            return "服务暂不可用，请稍后重试"
        if exc.code == "runtime_api_only_mode":
            return "当前为 API-only 模式，无法启动下载任务"
        if exc.code in {"runtime_start_failed", "runtime_stop_failed", "runtime_cleanup_failed"}:
            return "运行控制失败，请稍后重试"
        return f"操作失败：{exc.message}"

    async def initialize(self):
        await cast(Awaitable[Any], self.bot_client.start(bot_token=TOKEN))
        await self.set_commands_list()
        await self.auto_start_download_and_listening()
        self.bot_client.on(events.NewMessage(pattern=r"^/(start|help)$"))(self.start_handler)
        self.bot_client.on(events.NewMessage(pattern=r"^/(start_client)$"))(
            lambda event: self.start_download_and_listening(event)
        )
        self.bot_client.on(events.NewMessage(pattern=r"^/search (.+)"))(self.search_command_handler)
        self.bot_client.on(events.NewMessage(pattern=r"^/set_black_list2meili (.+)"))(self.set_black_list2meili)
        self.bot_client.on(events.NewMessage(pattern=r"^/set_white_list2meili (.+)"))(self.set_white_list2meili)
        self.bot_client.on(events.NewMessage(pattern=r"^/cc$"))(self.clean)
        self.bot_client.on(events.NewMessage(pattern=r"^/about$"))(self.about_handler)
        self.bot_client.on(events.NewMessage(pattern=r"^/ping$"))(self.ping_handler)
        self.bot_client.on(events.NewMessage(func=lambda e: e.is_private and not e.text.startswith("/")))(
            self.message_handler
        )
        callback_query_event: Any = events.CallbackQuery
        self.bot_client.on(callback_query_event)(self.callback_query_handler)
        self.bot_client.on(events.NewMessage(pattern=r"^/(stop_client)$"))(self.stop_download_and_listening)

    async def set_commands_list(self):
        commands = [
            BotCommand(command="start_client", description="启动消息监听与下载历史消息"),
            BotCommand(command="stop_client", description="停止消息监听与下载"),
            BotCommand(command="set_white_list2meili", description="配置Meili白名单，参数为列表"),
            BotCommand(command="set_black_list2meili", description="配置Meili黑名单，参数为列表"),
            BotCommand(command="cc", description="清除搜索历史消息缓存"),
            BotCommand(command="search", description="关键词搜索（空格分隔多个词）"),
            BotCommand(command="ping", description="检查搜索服务状态"),
            BotCommand(command="about", description="项目信息"),
        ]

        await cast(
            Awaitable[Any],
            self.bot_client(
                SetBotCommandsRequest(
                    scope=BotCommandScopeDefault(),
                    lang_code="",  # 空字符串表示默认语言
                    commands=commands,
                )
            ),
        )

    async def run(self):
        await self.initialize()
        self.logger.log(25, "Bot started")
        await cast(Awaitable[Any], self.bot_client.run_until_disconnected())

    @set_permission
    async def stop_download_and_listening(self, event):
        try:
            result = await self.runtime_control_service.stop(source="bot")
            if result.status == "stopped":
                await event.reply("下载任务已停止")
            else:
                await event.reply("没有正在运行的下载任务")
        except DomainError as exc:
            await event.reply(self._domain_error_to_text(exc))
            self.logger.error(f"Runtime stop command failed: {exc.code}: {exc.message}")

    @set_permission
    async def start_download_and_listening(self, event):
        try:
            result = await self.runtime_control_service.start(source="bot")
            if result.status == "started":
                await event.reply("开始下载历史消息,监听历史消息...")
                self.logger.info("Downloading and listening messages for dialogs")
            else:
                await event.reply("下载任务已经在运行中...")
        except DomainError as exc:
            await event.reply(self._domain_error_to_text(exc))
            self.logger.error(f"Runtime start command failed: {exc.code}: {exc.message}")

    async def auto_start_download_and_listening(self):
        try:
            result = await self.runtime_control_service.start(source="bot_auto")
            if result.status == "already_running":
                self.logger.info("Downloading task is already running...")
        except DomainError as exc:
            self.logger.error(f"Auto start runtime failed: {exc.code}: {exc.message}")

    async def search_handler(self, event, query):
        try:
            results = (
                await self.get_search_results(query, limit=MAX_RESULTS)
                if not SEARCH_CACHE
                else await self.get_search_results(query)
            )
            if results:
                if SEARCH_CACHE:
                    self.search_results_cache[query] = results
                    asyncio.create_task(self.clean_cache(query))
                    additional_cache = await self.get_search_results(query, limit=MAX_RESULTS - 10, offset=10)
                    if additional_cache:
                        self.search_results_cache[query].extend(additional_cache)
                await self.send_results_page(event, results, 0, query)
            else:
                await event.reply("没有找到相关结果。")
        except Exception as e:
            await event.reply(f"Search error: {e}")
            self.logger.error(f"Search error: {e}")

    async def get_search_results(self, query, limit=10, offset=0, index_name="telegram"):
        try:
            results = await asyncio.to_thread(self.meili.search, query, index_name, limit=limit, offset=offset)
            return results["hits"] if results["hits"] else None
        except Exception as e:
            self.logger.error(f"MeiliSearch query error: {e}")
            return None

    async def start_handler(self, event):
        await event.reply("""
🔍 Telegram 消息搜索机器人
这个机器人可以让你搜索保存的 Telegram 消息历史记录。
基本命令：
• 直接输入任何文本以搜索消息
• 结果将显示发送者、发送位置、时间及消息预览
/cc - 清理缓存
/start_client - 开始下载历史消息,监听历史消息
/stop_client - 停止下载历史消息,监听历史消息
/set_white_list2meili [1,2]- 设置白名单
/set_black_list2meili []- 设置黑名单
/search <关键词1> <关键词2>
/ping - 检查搜索服务是否运行
/about - 关于本项目

导航：
• 使用⬅️ 上一页和下一页 ➡️ 按钮浏览搜索结果
• 每页最多显示10条结果
""")

    @set_permission
    async def search_command_handler(self, event):
        self.logger.info(f"Received search command: {event.pattern_match.group(1)}")
        query = event.pattern_match.group(1)
        await self.search_handler(event, query)

    @set_permission
    async def set_white_list2meili(self, event):
        self.logger.info(f"Received set set_white_list2meili command: {event.pattern_match.group(1)}")
        try:
            query = ast.literal_eval(event.pattern_match.group(1))
            result = await self.policy_service.set_whitelist(query, source="bot")
            await event.reply(f"白名单设置为: {result.updated_list}")
        except DomainError as exc:
            await event.reply(self._domain_error_to_text(exc))
            self.logger.error(f"Policy command failed: {exc.code}: {exc.message}")
        except Exception as e:
            await event.reply(f"Error: {e}")
            self.logger.error(f"Error: {e}")
            return

    @set_permission
    async def set_black_list2meili(self, event):
        self.logger.info(f"Received set set_black_list2meili command: {event.pattern_match.group(1)}")
        try:
            query = ast.literal_eval(event.pattern_match.group(1))
            result = await self.policy_service.set_blacklist(query, source="bot")
            await event.reply(f"黑名单设置为: {result.updated_list}")
        except DomainError as exc:
            await event.reply(self._domain_error_to_text(exc))
            self.logger.error(f"Policy command failed: {exc.code}: {exc.message}")
        except Exception as e:
            await event.reply(f"Error: {e}")
            self.logger.error(f"Error: {e}")
            return

    @set_permission
    async def clean(self, event):
        self.search_results_cache.clear()
        await event.reply("缓存已清理。") if event else None
        self.logger.info("Cache cleared.")
        gc.collect()

    async def clean_cache(self, key):
        await asyncio.sleep(CACHE_EXPIRE_SECONDS)
        try:
            del self.search_results_cache[key]
            self.logger.info(f"Cache for {key} deleted.")
        except Exception as e:
            self.logger.error(f"Error deleting cache: {e}")

    async def about_handler(self, event):
        await event.reply(
            "本项目基于 MeiliSearch 和 Telethon 构建，用于搜索保存的 Telegram 消息历史记录。解决了 Telegram 中文搜索功能的不足，提供了更强大的搜索功能。\n   \n    本项目的github地址为：[Meilisearch4TelegramSearchCKJ](https://github.com/clionertr/Meilisearch4TelegramSearchCKJ)，如果觉得好用可以点个star\n\n    得益于telethon的优秀代码，相比使用pyrogram，本项目更加稳定，同时减少大量负载\n\n    项目由[SearchGram](https://github.com/tgbot-collection/SearchGram)重构而来，感谢原作者的贡献❤️\n\n    同时感谢Claude3.5s和GeminiExp的帮助\n\n    从这次的编程中，我学到了很多，也希望大家能够喜欢这个项目😘"
        )

    @set_permission
    async def ping_handler(self, event):
        text = "Pong!\n"
        stats = await asyncio.to_thread(self.meili.client.get_all_stats)
        size = stats["databaseSize"]
        last_update = stats["lastUpdate"]
        for uid, index in stats["indexes"].items():
            text += f"Index {uid} has {index['numberOfDocuments']} documents\n"
        text += f"\nDatabase size: {sizeof_fmt(size)}\nLast update: {last_update}\n"
        await event.reply(text)

    @set_permission
    async def message_handler(self, event):
        await self.search_handler(event, event.raw_text)

    def format_search_result(self, hit: dict[str, Any]) -> str:
        if len(hit["text"]) > 360:
            text = hit["text"][:360] + "..."
        else:
            text = hit["text"]

        chat_type = hit["chat"]["type"]
        if chat_type == "private":
            chat_title = f"Private: {hit['chat']['username']}"
            url = f"tg://openmessage?user_id={hit['id'].split('-')[0]}&message_id={hit['id'].split('-')[1]}"
        elif chat_type == "channel":
            chat_title = f"Channel: {hit['chat']['title']}"
            url = f"https://t.me/c/{hit['id'].split('-')[0]}/{hit['id'].split('-')[1]}"
        else:
            chat_title = f"Group: {hit['chat']['title']}"
            url = f"https://t.me/c/{hit['id'].split('-')[0]}/{hit['id'].split('-')[1]}"

        date = hit["date"].split("T")[0]
        return f"- **{chat_title}**  ({date})\n{text}\n  [🔗Jump]({url})\n" + "—" * 18 + "\n"

    def _build_results_page(
        self,
        hits: list[dict[str, Any]],
        page_number: int,
        query: str,
    ) -> tuple[str, list | None]:
        """构建结果页面内容和分页按钮（公共方法）

        Returns:
            (text, buttons)：text 为空字符串时表示无结果。
        """
        start_index = page_number * RESULTS_PER_PAGE
        end_index = min((page_number + 1) * RESULTS_PER_PAGE, len(hits))
        page_results = hits[start_index:end_index]

        if not page_results:
            return "", None

        response = "".join([self.format_search_result(hit) for hit in page_results])
        buttons: list = []
        if page_number > 0:
            buttons.append(Button.inline("上一页", data=f"page_{query}_{page_number - 1}"))
        if end_index < len(hits):
            buttons.append(Button.inline("下一页", data=f"page_{query}_{page_number + 1}"))

        text = f"搜索结果 (第 {page_number + 1} 页):\n{response}"
        return text, buttons or None

    async def send_results_page(self, event, hits, page_number, query):
        text, buttons = self._build_results_page(hits, page_number, query)
        if not text:
            await event.reply("没有更多结果了。")
            return
        await self.bot_client.send_message(event.chat_id, text, buttons=buttons)

    async def edit_results_page(self, event, hits, page_number, query):
        text, buttons = self._build_results_page(hits, page_number, query)
        if not text:
            await event.reply("没有更多结果了。")
            return
        await event.edit(text, buttons=buttons)

    async def callback_query_handler(self, event):
        data = event.data.decode("utf-8")
        if data.startswith("page_"):
            parts = data.split("_")
            query = parts[1]
            page_number = int(parts[2])
            try:
                # TODO  加速未缓存时的搜索速度
                results = (
                    await self.get_search_results(query, limit=MAX_RESULTS)
                    if not SEARCH_CACHE
                    else self.search_results_cache.get(query)
                )
                await event.edit(f"正在加载第 {page_number + 1} 页...")
                await self.edit_results_page(event, results, page_number, query)
            except Exception as e:
                await event.answer(f"搜索出错：{e}", alert=True)
                self.logger.error(f"搜索出错：{e}")
