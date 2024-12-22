import asyncio
import gc
from telethon import TelegramClient, events, Button
from Meilisearch4TelegramSearchCKJ.src.config.env import TOKEN, MEILI_HOST, MEILI_PASS, APP_ID, APP_HASH, \
    RESULTS_PER_PAGE, SEARCH_CACHE, PROXY, IPv6, OWNER_IDS, CACHE_EXPIRE_SECONDS
from Meilisearch4TelegramSearchCKJ.src.models.meilisearch_handler import MeiliSearchClient
from Meilisearch4TelegramSearchCKJ.src.utils.fmt_size import sizeof_fmt
from Meilisearch4TelegramSearchCKJ.src.models.logger import setup_logger


def set_permission(func):
    """装饰器：检查用户是否在白名单中"""

    async def wrapper(self, event, *args, **kwargs):
        user_id = event.sender_id
        if not OWNER_IDS or user_id in OWNER_IDS:
            await func(self, event, *args, **kwargs)
        else:
            await event.respond('你没有权限使用此指令。')
            self.logger.info(f"User {user_id} tried to use command {event.text}, but does not have permission.")

    return wrapper


class BotHandler:
    def __init__(self, main):
        self.logger = setup_logger()
        self.bot_client = TelegramClient('bot', APP_ID, APP_HASH, use_ipv6=IPv6, proxy=PROXY, auto_reconnect=True,
                                         connection_retries=5)
        self.meili = MeiliSearchClient(MEILI_HOST, MEILI_PASS)
        self.search_results_cache = {}
        self.main = main
        self.download_task = None  # Used to store the download task

    async def initialize(self):
        await self.bot_client.start(bot_token=TOKEN)
        self.bot_client.on(events.NewMessage(pattern=r'^/(start|help)$'))(self.start_handler)
        self.bot_client.on(events.NewMessage(pattern=r'^/(start_client)$'))(
            lambda event: self.start_download_and_listening(event))
        self.bot_client.on(events.NewMessage(pattern=r'^/search (.+)'))(self.search_command_handler)
        self.bot_client.on(events.NewMessage(pattern=r'^/cc$'))(self.clean)
        self.bot_client.on(events.NewMessage(pattern=r'^/about$'))(self.about_handler)
        self.bot_client.on(events.NewMessage(pattern=r'^/ping$'))(self.ping_handler)
        self.bot_client.on(events.NewMessage(func=lambda e: e.is_private and not e.text.startswith('/')))(
            self.message_handler)
        self.bot_client.on(events.CallbackQuery)(self.callback_query_handler)
        self.bot_client.on(events.NewMessage(pattern=r'^/(stop_client)$'))(self.stop_download_and_listening)

    async def run(self):
        await self.initialize()
        self.logger.log(25, "Bot started")
        await self.bot_client.run_until_disconnected()

    @set_permission
    async def stop_download_and_listening(self, event):
        if self.download_task and not self.download_task.done():
            self.download_task.cancel()
            await event.reply("下载任务已停止")
        else:
            await event.reply("没有正在运行的下载任务")

    @set_permission
    async def start_download_and_listening(self, event):
        neo_msg = await event.reply("开始下载历史消息,监听历史消息...")
        self.logger.info("Downloading and listening messages for dialogs")
        if self.download_task is None or self.download_task.done():
            self.download_task = asyncio.create_task(self.main())
        else:
            await event.reply("下载任务已经在运行中...")

    async def search_handler(self, event, query):
        try:
            results = await self.get_search_results(query, limit=50) if not SEARCH_CACHE else await self.get_search_results(query)
            if results:
                if SEARCH_CACHE:
                    self.search_results_cache[query] = results
                    asyncio.create_task(self.clean_cache(query))
                    additional_cache = await self.get_search_results(query, limit=40, offset=10)
                    if additional_cache:
                        self.search_results_cache[query].extend(additional_cache)
                await self.send_results_page(event, results, 0, query)
            else:
                await event.reply("没有找到相关结果。")
        except Exception as e:
            await event.reply(f"Search error: {e}")
            self.logger.error(f"Search error: {e}")

    async def get_search_results(self, query, limit=10, offset=0, index_name='telegram'):
        try:
            results = self.meili.search(query, index_name, limit=limit, offset=offset)
            return results['hits'] if results['hits'] else None
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
/search <关键词1> <关键词2>
/ping - 检查搜索服务是否运行
/about - 关于本项目
/cc - 清理缓存
/start_client - 开始下载历史消息,监听历史消息
/stop_client - 停止下载历史消息,监听历史消息

你使用以下代码设置机器人命令
```
search - <关键词1 关键词2>
ping - 检查搜索服务是否运行
about - 关于本项目
cc - 清理缓存
start_client - 开始下载历史消息,监听历史消息
stop_client - 停止下载历史消息,监听历史消息
```
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
    async def clean(self, event):
        self.search_results_cache.clear()
        await event.reply("缓存已清理。") if event else None
        self.logger.info("Cache cleared.")
        gc.collect()

    async def clean_cache(self,key):
        await asyncio.sleep(CACHE_EXPIRE_SECONDS)
        try:
            del self.search_results_cache[key]
            self.logger.info(f"Cache for {key} deleted.")
        except Exception as e:
            self.logger.error(f"Error deleting cache: {e}")

    
    async def about_handler(self, event):
        await event.reply(
            "本项目基于 MeiliSearch 和 Telethon 构建，用于搜索保存的 Telegram 消息历史记录。解决了 Telegram 中文搜索功能的不足，提供了更强大的搜索功能。\n   \n    本项目的github地址为：[Meilisearch4TelegramSearchCKJ](https://github.com/clionertr/Meilisearch4TelegramSearchCKJ)，如果觉得好用可以点个star\n\n    得益于telethon的优秀代码，相比使用pyrogram，本项目更加稳定，同时减少大量负载\n\n    项目由[SearchGram](https://github.com/tgbot-collection/SearchGram)重构而来，感谢原作者的贡献❤️\n\n    同时感谢Claude3.5s和GeminiExp的帮助\n\n    从这次的编程中，我学到了很多，也希望大家能够喜欢这个项目😘")

    @set_permission
    async def ping_handler(self, event):
        text = "Pong!\n"
        stats = self.meili.client.get_all_stats()
        size = stats["databaseSize"]
        last_update = stats["lastUpdate"]
        for uid, index in stats["indexes"].items():
            text += f"Index {uid} has {index['numberOfDocuments']} documents\n"
        text += f"\nDatabase size: {sizeof_fmt(size)}\nLast update: {last_update}\n"
        await event.reply(text)


    @set_permission
    async def message_handler(self, event):
        await self.search_handler(event, event.raw_text)

    def format_search_result(self, hit):
        if len(hit['text']) > 360:
            text = hit['text'][:360] + "..."
        else:
            text = hit['text']

        chat_type = hit['chat']['type']
        if chat_type == 'private':
            chat_title = f"Private: {hit['chat']['username']}"
            url = f"tg://openmessage?user_id={hit['id'].split('-')[0]}&message_id={hit['id'].split('-')[1]}"
        elif chat_type == 'channel':
            chat_title = f"Channel: {hit['chat']['title']}"
            url = f"https://t.me/c/{hit['id'].split('-')[0]}/{hit['id'].split('-')[1]}"
        else:
            chat_title = f"Group: {hit['chat']['title']}"
            url = f"https://t.me/c/{hit['id'].split('-')[0]}/{hit['id'].split('-')[1]}"

        chat_username = hit['chat'].get('username', 'N/A')
        date = hit['date'].split('T')[0]
        return f"- **{chat_title}**  ({date})\n{text}\n  [🔗Jump]({url})\n" + "—" * 18 + "\n"

    async def send_results_page(self, event, hits, page_number, query):
        start_index = page_number * RESULTS_PER_PAGE
        end_index = min((page_number + 1) * RESULTS_PER_PAGE, len(hits))
        page_results = hits[start_index:end_index]

        if not page_results:
            await event.reply("没有更多结果了。")
            return

        response = "".join([self.format_search_result(hit) for hit in page_results])
        buttons = []
        if page_number > 0:
            buttons.append(Button.inline("上一页", data=f"page_{query}_{page_number - 1}"))
        if end_index < len(hits):
            buttons.append(Button.inline("下一页", data=f"page_{query}_{page_number + 1}"))

        await self.bot_client.send_message(event.chat_id, f"搜索结果 (第 {page_number + 1} 页):\n{response}",
                                           buttons=buttons if buttons else None)

    async def edit_results_page(self, event, hits, page_number, query):
        start_index = page_number * RESULTS_PER_PAGE
        end_index = min((page_number + 1) * RESULTS_PER_PAGE, len(hits))
        page_results = hits[start_index:end_index]

        if not page_results:
            await event.reply("没有更多结果了。")
            return

        response = "".join([self.format_search_result(hit) for hit in page_results])
        buttons = []
        if page_number > 0:
            buttons.append(Button.inline("上一页", data=f"page_{query}_{page_number - 1}"))
        if end_index < len(hits):
            buttons.append(Button.inline("下一页", data=f"page_{query}_{page_number + 1}"))

        await event.edit(f"搜索结果 (第 {page_number + 1} 页):\n{response}", buttons=buttons if buttons else None)

    async def callback_query_handler(self, event):
        data = event.data.decode('utf-8')
        if data.startswith('page_'):
            parts = data.split('_')
            query = parts[1]
            page_number = int(parts[2])
            try:
                results = self.search_results_cache.get(query)
                if results is None:
                    results = await self.get_search_results(query)
                    if results:
                        self.search_results_cache[query] = results
                    else:
                        await event.answer("没有找到相关结果。", alert=True)
                        return
                await event.edit(f"正在加载第 {page_number + 1} 页...")
                await self.edit_results_page(event, results, page_number, query)
            except Exception as e:
                await event.answer(f"搜索出错：{e}", alert=True)
                self.logger.error(f"搜索出错：{e}")
