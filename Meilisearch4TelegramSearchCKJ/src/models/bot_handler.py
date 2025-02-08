# bot_handler.py
import ast
import asyncio
import gc

from telethon import TelegramClient, events, Button
from telethon.tl.functions.bots import SetBotCommandsRequest
from telethon.tl.types import BotCommand, BotCommandScopeDefault

from Meilisearch4TelegramSearchCKJ.src.config.env import TOKEN, MEILI_HOST, MEILI_PASS, APP_ID, APP_HASH, \
    RESULTS_PER_PAGE, SEARCH_CACHE, PROXY, IPv6, OWNER_IDS, CACHE_EXPIRE_SECONDS, MAX_PAGE
from Meilisearch4TelegramSearchCKJ.src.models.logger import setup_logger
from Meilisearch4TelegramSearchCKJ.src.models.meilisearch_handler import MeiliSearchClient
from Meilisearch4TelegramSearchCKJ.src.utils.fmt_size import sizeof_fmt
from Meilisearch4TelegramSearchCKJ.src.utils.record_lastest_msg_id import read_config_from_meili

MAX_RESULTS = MAX_PAGE * RESULTS_PER_PAGE


def set_permission(func):
    """权限检查装饰器：仅允许 OWNER_IDS 中的用户使用"""

    async def wrapper(self, event, *args, **kwargs):
        user_id = event.sender_id
        if not OWNER_IDS or user_id in OWNER_IDS:
            try:
                await func(self, event, *args, **kwargs)
            except Exception as e:
                self.logger.error(f"执行 {func.__name__} 时出错: {e}")
                await event.reply(f"执行命令时发生错误: {e}")
        else:
            await event.reply('你没有权限使用此指令。')
            self.logger.info(f"用户 {user_id} 无权使用指令 {event.text}")

    return wrapper


class BotHandler:
    def __init__(self, main_callback):
        self.logger = setup_logger()
        self.bot_client = TelegramClient('session/bot', APP_ID, APP_HASH, use_ipv6=IPv6, proxy=PROXY,
                                         auto_reconnect=True,
                                         connection_retries=5)
        self.meili = MeiliSearchClient(MEILI_HOST, MEILI_PASS)
        self.search_results_cache = {}
        self.main_callback = main_callback
        self.download_task = None

    async def initialize(self):
        await self.bot_client.start(bot_token=TOKEN)
        await self.set_commands_list()
        await self.auto_start_download_and_listening()
        # 注册指令
        self.bot_client.add_event_handler(self.start_handler, events.NewMessage(pattern=r'^/(start|help)$'))
        self.bot_client.add_event_handler(self.start_download_and_listening,
                                          events.NewMessage(pattern=r'^/(start_client)$'))
        self.bot_client.add_event_handler(self.stop_download_and_listening,
                                          events.NewMessage(pattern=r'^/(stop_client)$'))
        self.bot_client.add_event_handler(self.search_command_handler, events.NewMessage(pattern=r'^/search (.+)'))
        self.bot_client.add_event_handler(self.set_black_list2meili,
                                          events.NewMessage(pattern=r'^/set_black_list2meili (.+)'))
        self.bot_client.add_event_handler(self.set_white_list2meili,
                                          events.NewMessage(pattern=r'^/set_white_list2meili (.+)'))
        self.bot_client.add_event_handler(self.clean, events.NewMessage(pattern=r'^/cc$'))
        self.bot_client.add_event_handler(self.about_handler, events.NewMessage(pattern=r'^/about$'))
        self.bot_client.add_event_handler(self.ping_handler, events.NewMessage(pattern=r'^/ping$'))
        self.bot_client.add_event_handler(self.message_handler,
                                          events.NewMessage(func=lambda e: e.is_private and not e.text.startswith('/')))
        self.bot_client.add_event_handler(self.callback_query_handler, events.CallbackQuery)

    async def set_commands_list(self):
        commands = [
            BotCommand(command='start_client', description='启动消息监听与下载历史消息'),
            BotCommand(command='stop_client', description='停止消息监听与下载'),
            BotCommand(command='set_white_list2meili', description='配置Meili白名单，参数为列表'),
            BotCommand(command='set_black_list2meili', description='配置Meili黑名单，参数为列表'),
            BotCommand(command='cc', description='清除搜索历史消息缓存'),
            BotCommand(command='search', description='关键词搜索（空格分隔多个词）'),
            BotCommand(command='ping', description='检查搜索服务状态'),
            BotCommand(command='about', description='项目信息'),
            BotCommand(command='help', description='显示帮助信息'),
        ]
        await self.bot_client(SetBotCommandsRequest(
            scope=BotCommandScopeDefault(),
            lang_code='',
            commands=commands))

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
        await event.reply("开始下载历史消息，监听新消息...")
        self.logger.info("启动下载与监听任务")
        if self.download_task is None or self.download_task.done():  # ?done
            self.download_task = asyncio.create_task(self.main_callback())
        else:
            await event.reply("下载任务已经在运行中。")

    async def auto_start_download_and_listening(self):
        if self.download_task is None or self.download_task.done():
            self.download_task = asyncio.create_task(self.main_callback())
        else:
            self.logger.info("下载任务已在运行")

    async def search_handler(self, event, query):
        try:
            results = None
            if SEARCH_CACHE and query in self.search_results_cache:
                results = self.search_results_cache[query]
            else:
                results = await self.get_search_results(query, limit=MAX_RESULTS)
                if SEARCH_CACHE:
                    self.search_results_cache[query] = results
                    asyncio.create_task(self.clean_cache(query)) #?await
            if results:
                await self.send_results_page(event, results, 0, query)
            else:
                await event.reply("没有找到相关结果。")
        except Exception as e:
            await event.reply(f"搜索出错: {e}")
            self.logger.error(f"搜索出错: {e}")

    async def get_search_results(self, query, limit=10, offset=0, index_name='telegram'):
        try:
            results = self.meili.search(query, index_name, limit=limit, offset=offset)
            return results.get('hits', [])
        except Exception as e:
            self.logger.error(f"MeiliSearch 搜索错误: {e}")
            return None

    async def start_handler(self, event):
        text = (
            "🔍 Telegram 消息搜索机器人\n"
            "基本命令：\n"
            "• 直接输入文本进行搜索\n"
            "• /cc 清理缓存\n"
            "• /start_client 启动消息监听与历史下载\n"
            "• /stop_client 停止下载任务\n"
            "• /set_white_list2meili [1,2,...] 设置白名单\n"
            "• /set_black_list2meili [1,2,...] 设置黑名单\n"
            "• /search <关键词1> <关键词2>\n"
            "• /ping 检查搜索服务状态\n"
            "• /about 关于项目\n"
            "使用按钮进行翻页导航。"
        )
        await event.reply(text)

    @set_permission
    async def search_command_handler(self, event):
        query = event.pattern_match.group(1)
        self.logger.info(f"收到搜索指令: {query}")
        await self.search_handler(event, query)

    @set_permission
    async def set_white_list2meili(self, event):
        try:
            whitelist = ast.literal_eval(event.pattern_match.group(1))
            config = read_config_from_meili(self.meili)
            config['WHITE_LIST'] = whitelist
            self.meili.add_documents([config], "config")
            await event.reply(f"白名单已设置为: {whitelist}")
        except Exception as e:
            await event.reply(f"设置白名单出错: {e}")
            self.logger.error(f"设置白名单出错: {e}")

    @set_permission
    async def set_black_list2meili(self, event):
        try:
            blacklist = ast.literal_eval(event.pattern_match.group(1))
            config = read_config_from_meili(self.meili)
            config['BLACK_LIST'] = blacklist
            self.meili.add_documents([config], "config")
            await event.reply(f"黑名单已设置为: {blacklist}")
        except Exception as e:
            await event.reply(f"设置黑名单出错: {e}")
            self.logger.error(f"设置黑名单出错: {e}")

    @set_permission
    async def clean(self, event):
        self.search_results_cache.clear()
        await event.reply("缓存已清理。")
        self.logger.info("缓存清理完成")
        gc.collect()

    async def clean_cache(self, key):
        await asyncio.sleep(CACHE_EXPIRE_SECONDS)
        try:
            self.search_results_cache.pop(key, None)
            self.logger.info(f"缓存 {key} 删除")
        except Exception as e:
            self.logger.error(f"删除缓存 {key} 出错: {e}")

    async def about_handler(self, event):
        await event.reply(
            "本项目基于 MeiliSearch 和 Telethon 构建，用于搜索保存的 Telegram 消息历史记录。解决了 Telegram 中文搜索功能的不足，提供了更强大的搜索功能。\n   \n    本项目的github地址为：[Meilisearch4TelegramSearchCKJ](https://github.com/clionertr/Meilisearch4TelegramSearchCKJ)，如果觉得好用可以点个star\n\n    得益于telethon的优秀代码，相比使用pyrogram，本项目更加稳定，同时减少大量负载\n\n    项目由[SearchGram](https://github.com/tgbot-collection/SearchGram)重构而来，感谢原作者的贡献❤️\n\n    同时感谢Claude3.5s和GeminiExp的帮助\n\n    从这次的编程中，我学到了很多，也希望大家能够喜欢这个项目😘")

    @set_permission
    async def ping_handler(self, event):
        try:
            stats = self.meili.client.get_all_stats()
            text = "Pong!\n"
            size = stats.get("databaseSize", 0)
            text += f"Database size: {sizeof_fmt(size)}\n"
            for uid, index in stats.get("indexes", {}).items():
                text += f"Index {uid} 有 {index.get('numberOfDocuments', 0)} 条文档\n"
            await event.reply(text)
        except Exception as e:
            await event.reply(f"Ping 出错: {e}")
            self.logger.error(f"Ping 出错: {e}")

    @set_permission
    async def message_handler(self, event):
        # 当私聊非命令消息时也尝试搜索
        await self.search_handler(event, event.raw_text)

    # TODO 优化抬头
    def format_search_result(self, hit):
        text = hit.get('text', '')
        if len(text) > 360:
            text = text[:360] + "..."
        chat = hit.get('chat', {})
        chat_type = chat.get('type', 'private')
        if chat_type == 'private':
            chat_title = f"Private: {chat.get('username', 'N/A')}"
            url = f"tg://openmessage?user_id={hit['id'].split('-')[0]}&message_id={hit['id'].split('-')[1]}"
        else:
            chat_title = f"{chat_type.capitalize()}: {chat.get('title', 'N/A')}"
            url = f"https://t.me/c/{hit['id'].split('-')[0]}/{hit['id'].split('-')[1]}"
        date = hit.get('date', '').split('T')[0]
        return f"- **{chat_title}** ({date})\n{text}\n[🔗跳转]({url})\n{'—' * 18}\n"

    async def send_results_page(self, event, hits, page_number, query):
        start_index = page_number * RESULTS_PER_PAGE
        end_index = min((page_number + 1) * RESULTS_PER_PAGE, len(hits))
        page_results = hits[start_index:end_index]
        if not page_results:
            await event.reply("没有更多结果了。")
            return
        response = "".join(self.format_search_result(hit) for hit in page_results)
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
        response = "".join(self.format_search_result(hit) for hit in page_results)
        buttons = []
        if page_number > 0:
            buttons.append(Button.inline("上一页", data=f"page_{query}_{page_number - 1}"))
        if end_index < len(hits):
            buttons.append(Button.inline("下一页", data=f"page_{query}_{page_number + 1}"))
        await event.edit(f"搜索结果 (第 {page_number + 1} 页):\n{response}", buttons=buttons if buttons else None)

    async def callback_query_handler(self, event):
        data = event.data.decode('utf-8')
        if data.startswith('page_'):
            try:
                _, query, page_str = data.split('_')
                page_number = int(page_str)
                # 从缓存或重新获取搜索结果
                results = self.search_results_cache.get(query) if SEARCH_CACHE else await self.get_search_results(query,
                                                                                                                  limit=MAX_RESULTS)
                await event.edit(f"正在加载第 {page_number + 1} 页...")
                await self.edit_results_page(event, results, page_number, query)
            except Exception as e:
                await event.answer(f"搜索出错：{e}", alert=True)
                self.logger.error(f"翻页搜索出错：{e}")
