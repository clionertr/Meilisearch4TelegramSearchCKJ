# bot_handler.py
import ast
import asyncio
import gc
from typing import Callable, Any, Coroutine, Dict, List, Optional

# 导入配置读写函数
from Meilisearch4TelegramSearchCKJ.src.utils.record_lastest_msg_id import save_config, load_config
from telethon import TelegramClient, events, Button
from telethon.tl.functions.bots import SetBotCommandsRequest
from telethon.tl.types import BotCommand, BotCommandScopeDefault

from Meilisearch4TelegramSearchCKJ.src.config.env import (
    BOT_TOKEN, MEILI_HOST, MEILI_PASS, APP_ID, APP_HASH,
    RESULTS_PER_PAGE, SEARCH_CACHE, PROXY, IPv6, OWNER_IDS,
    CACHE_EXPIRE_SECONDS, MAX_PAGE, BANNED_WORDS
)
from Meilisearch4TelegramSearchCKJ.src.models.logger import setup_logger
from Meilisearch4TelegramSearchCKJ.src.models.meilisearch_handler import MeiliSearchClient
from Meilisearch4TelegramSearchCKJ.src.utils.fmt_size import sizeof_fmt

MAX_RESULTS = MAX_PAGE * RESULTS_PER_PAGE


def set_permission(func: Callable[..., Coroutine[Any, Any, None]]) -> Callable[..., Coroutine[Any, Any, None]]:
    """
    权限检查装饰器：仅允许 OWNER_IDS 中的用户使用
    """

    async def wrapper(self, event, *args, **kwargs):
        user_id = event.sender_id
        if not OWNER_IDS or user_id in OWNER_IDS:
            try:
                await func(self, event, *args, **kwargs)
            except Exception as e:
                self.logger.error(f"执行 {func.__name__} 时出错: {e}", exc_info=True)
                await event.reply(f"执行命令时发生错误: {e}")
        else:
            self.logger.info(f"用户 {user_id} 无权使用指令 {event.text}")
            await event.reply('你没有权限使用此指令。')

    return wrapper


class BotHandler:
    def __init__(self, main_callback: Callable[[], Coroutine[Any, Any, None]]):
        self.logger = setup_logger()
        self.bot_client = TelegramClient('session/bot', APP_ID, APP_HASH, use_ipv6=IPv6, proxy=PROXY,
                                         auto_reconnect=True, connection_retries=5)
        self.meili = MeiliSearchClient(MEILI_HOST, MEILI_PASS)
        self.search_results_cache: Dict[str, List[Dict]] = {}
        self.main_callback = main_callback
        self.download_task: Optional[asyncio.Task] = None

    async def initialize(self) -> None:
        await self.bot_client.start(bot_token=BOT_TOKEN)
        await self.set_commands_list()
        await self.auto_start_download_and_listening()
        # 注册各类事件处理器
        self.bot_client.add_event_handler(self.start_handler, events.NewMessage(pattern=r'^/start$'))
        self.bot_client.add_event_handler(self.help_handler, events.NewMessage(pattern=r'^/help$'))
        self.bot_client.add_event_handler(self.start_download_and_listening,
                                          events.NewMessage(pattern=r'^/(start_client)$'))
        self.bot_client.add_event_handler(self.stop_download_and_listening,
                                          events.NewMessage(pattern=r'^/(stop_client)$'))
        self.bot_client.add_event_handler(self.search_command_handler,
                                          events.NewMessage(pattern=r'^/search (.+)'))
        self.bot_client.add_event_handler(self.clean, events.NewMessage(pattern=r'^/cc$'))
        self.bot_client.add_event_handler(self.about_handler, events.NewMessage(pattern=r'^/about$'))
        self.bot_client.add_event_handler(self.ping_handler, events.NewMessage(pattern=r'^/ping$'))
        # 新增：转发消息处理器（仅在私聊中，对转发消息询问是否添加阻止名单）
        self.bot_client.add_event_handler(self.forwarded_message_handler,
                                          events.NewMessage(func=lambda e: e.is_private and e.fwd_from is not None))
        self.bot_client.add_event_handler(self.message_handler,
                                          events.NewMessage(func=lambda
                                              e: e.is_private and e.fwd_from is None and not e.text.startswith('/')))
        # 新增：处理 /ban 命令
        self.bot_client.add_event_handler(self.ban_command_handler, events.NewMessage(pattern=r'^/ban\b'))
        # 新增：处理 /banlist 命令
        self.bot_client.add_event_handler(self.banlist_handler, events.NewMessage(pattern=r'^/banlist\b'))
        self.bot_client.add_event_handler(self.set_config, events.NewMessage(pattern=r'^/set\b'))
        self.bot_client.add_event_handler(self.delete_all_contain_keyword, events.NewMessage(pattern=r'^/delete\b'))
        # 处理按钮回调，包括翻页和阻止名单确认
        self.bot_client.add_event_handler(self.list_part_config, events.NewMessage(pattern=r'^/list$'))
        self.bot_client.add_event_handler(self.callback_handler, events.CallbackQuery)

    async def set_commands_list(self) -> None:
        commands = [
            BotCommand(command='start', description='开始使用机器人'),
            BotCommand(command='help', description='显示帮助信息'),
            BotCommand(command='search', description='关键词搜索（空格分隔多个词）'),
            BotCommand(command='about', description='关于本项目'),
            BotCommand(command='ping', description='检查搜索服务状态'),
            BotCommand(command='cc', description='清除搜索历史消息缓存'),
            BotCommand(command='start_client', description='启动消息监听与下载历史消息'),
            BotCommand(command='stop_client', description='停止消息监听与下载'),
            BotCommand(command='list', description='显示当前配置'),
            BotCommand(command='set', description='设置配置项，格式: /set <key> <value>'),
            BotCommand(command='ban', description='添加阻止名单，格式: /ban <id/word> ...'),
            BotCommand(command='banlist', description='显示当前阻止名单'),
            BotCommand(command='delete', description='删除包含关键词的文档，格式: /delete <word/id> ...')
        ]
        await self.bot_client(SetBotCommandsRequest(
            scope=BotCommandScopeDefault(),
            lang_code='',
            commands=commands)
        )

    async def run(self) -> None:
        await self.initialize()
        self.logger.log(25, "Bot started")
        await self.bot_client.run_until_disconnected()

    @set_permission
    async def stop_download_and_listening(self, event) -> None:
        if self.download_task and not self.download_task.done():
            self.download_task.cancel()
            await event.reply("下载任务已停止")
        else:
            await event.reply("没有正在运行的下载任务")

    @set_permission
    async def start_download_and_listening(self, event) -> None:
        await event.reply("开始下载历史消息，监听新消息...")
        self.logger.info("启动下载与监听任务")
        if self.download_task is None or self.download_task.done():
            self.download_task = asyncio.create_task(self.main_callback())
        else:
            await event.reply("下载任务已经在运行中。")

    async def auto_start_download_and_listening(self) -> None:
        if self.download_task is None or self.download_task.done():
            self.download_task = asyncio.create_task(self.main_callback())
        else:
            self.logger.info("下载任务已在运行")

    async def search_handler(self, event, query: str) -> None:
        try:
            if SEARCH_CACHE and query in self.search_results_cache:
                results = self.search_results_cache[query]
            else:
                results = await self.get_search_results(query, limit=MAX_RESULTS)
                if SEARCH_CACHE:
                    self.search_results_cache[query] = results
                    # 后台异步清理缓存，无需阻塞执行
                    asyncio.create_task(self.clean_cache(query))
            if results:
                await self.send_results_page(event, results, 0, query)
            else:
                await event.reply("没有找到相关结果。")
        except Exception as e:
            self.logger.error(f"搜索出错: {e}", exc_info=True)
            await event.reply(f"搜索出错: {e}")

    async def get_search_results(self, query: str, limit: int = 10, offset: int = 0, index_name: str = 'telegram') -> \
    List[Dict]:
        try:
            results = self.meili.search(query, index_name, limit=limit, offset=offset)
            return results.get('hits', [])
        except Exception as e:
            self.logger.error(f"MeiliSearch 搜索错误: {e}", exc_info=True)
            return []

    async def start_handler(self, event) -> None:
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
            "• /about - 了解项目信息\n"
            "• /ping - 检查搜索服务状态\n\n"
            "输入 /help 获取更多命令和详细说明。"
        )
        await event.reply(text)

    async def help_handler(self, event) -> None:
        help_text = (
            "📖 **Telegram 消息搜索机器人帮助**\n\n"
            "**搜索命令**：\n"
            "• 直接输入文本 - 在私聊中直接输入文本即可搜索\n"
            "• /search <关键词1> <关键词2> - 搜索包含多个关键词的消息\n\n"

            "**管理命令**：\n"
            "• /start_client - 启动消息监听与下载历史消息\n"
            "• /stop_client - 停止消息监听与下载任务\n"
            "• /cc - 清除搜索结果缓存\n"
            "• /ping - 检查搜索服务状态和数据库信息\n\n"

            "**配置命令**：\n"
            "• /list - 显示当前配置信息\n"
            "• /set <key> <value> - 设置配置项，例如：/set inc {}\n\n"

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

    @set_permission
    async def search_command_handler(self, event) -> None:
        query = event.pattern_match.group(1)
        self.logger.info(f"收到搜索指令: {query}")
        await self.search_handler(event, query)

    @set_permission
    async def clean(self, event) -> None:
        self.search_results_cache.clear()
        await event.reply("缓存已清理。")
        self.logger.info("缓存清理完成")
        gc.collect()

    async def clean_cache(self, key: str) -> None:
        await asyncio.sleep(CACHE_EXPIRE_SECONDS)
        try:
            self.search_results_cache.pop(key, None)
            self.logger.info(f"缓存 {key} 删除")
        except Exception as e:
            self.logger.error(f"删除缓存 {key} 出错: {e}", exc_info=True)

    async def about_handler(self, event) -> None:
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
    async def ping_handler(self, event) -> None:
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

    @set_permission
    async def message_handler(self, event) -> None:
        # 当私聊中非命令消息时也尝试搜索
        await self.search_handler(event, event.raw_text)

    def format_search_result(self, hit: Dict) -> str:
        """
        格式化搜索结果，限制文字长度，并根据消息类型生成对应的跳转链接
        """
        text = hit.get('text') or ''
        # 添加安全检查，去除可能导致格式化错误的字符
        text = text.replace('**', '').replace('__', '')  # 去除可能导致 markdown 解析错误的标记

        if len(text) > 360:
            # 确保不会在多字节字符中间截断
            text = text[:360].strip() + "..."

        chat = hit.get('chat', {})
        chat_type = chat.get('type', 'private')
        if chat_type == 'private':
            chat_title = f"Private: {chat.get('username', 'N/A')}"
            parts = hit.get('id', '').split('-')
            url = f"tg://openmessage?user_id={parts[0]}&message_id={parts[1]}" if len(parts) >= 2 else ""
        else:
            chat_title = f"{chat_type.capitalize()}: {chat.get('title', 'N/A')}"
            parts = hit.get('id', '').split('-')
            url = f"https://t.me/c/{parts[0]}/{parts[1]}" if len(parts) >= 2 else ""

        date = hit.get('date', '').split('T')[0]

        # 修改链接格式，使用更安全的格式化方式
        return f"- **{chat_title}** ({date})\n{text}\n{f'[🔗跳转]({url})' if url else ''}\n{'—' * 18}\n"

    def get_pagination_buttons(self, query: str, page_number: int, total_hits: int) -> List[Button]:
        """
        根据当前页码和总结果生成翻页按钮
        """
        buttons = []
        if page_number > 0:
            buttons.append(Button.inline("上一页", data=f"page_{query}_{page_number - 1}"))
        if (page_number + 1) * RESULTS_PER_PAGE < total_hits:
            buttons.append(Button.inline("下一页", data=f"page_{query}_{page_number + 1}"))
        return buttons

    async def send_results_page(self, event, hits: List[Dict], page_number: int, query: str) -> None:
        start_index = page_number * RESULTS_PER_PAGE
        end_index = min((page_number + 1) * RESULTS_PER_PAGE, len(hits))
        page_results = hits[start_index:end_index]
        if not page_results:
            await event.reply("没有更多结果了。")
            return
        response = "".join(self.format_search_result(hit) for hit in page_results)
        buttons = self.get_pagination_buttons(query, page_number, len(hits))
        await self.bot_client.send_message(
            event.chat_id,
            f"搜索结果 (第 {page_number + 1} 页):\n{response}",
            buttons=buttons if buttons else None
        )

    async def edit_results_page(self, event, hits: List[Dict], page_number: int, query: str) -> None:
        if hits is None:
            await event.reply("搜索结果无效或过期，请重新搜索。")
            return

        try:
            start_index = page_number * RESULTS_PER_PAGE
            end_index = min((page_number + 1) * RESULTS_PER_PAGE, len(hits))
            page_results = hits[start_index:end_index]

            if not page_results:
                await event.reply("没有更多结果了。")
                return

            response = "".join(self.format_search_result(hit) for hit in page_results)
            buttons = self.get_pagination_buttons(query, page_number, len(hits))
            new_message = f"搜索结果 (第 {page_number + 1} 页):\n{response}"

            # 添加解析模式参数，确保正确处理 markdown
            await event.edit(
                new_message,
                buttons=buttons if buttons else None,
                parse_mode='markdown'  # 明确指定解析模式
            )
        except Exception as e:
            if "Content of the message was not modified" in str(e):
                self.logger.info("消息内容无变化，不需要更新。")
            elif "EntityBoundsInvalidError" in str(e):
                # 如果遇到实体边界错误，尝试以纯文本方式发送
                try:
                    await event.edit(
                        new_message.replace('**', '').replace('[', '').replace(']', ''),
                        buttons=buttons if buttons else None
                    )
                except Exception as e2:
                    self.logger.error(f"尝试纯文本编辑也失败：{e2}", exc_info=True)
                    await event.reply("编辑消息时出现格式错误，请重试。")
            else:
                self.logger.error(f"编辑结果页出错：{e}", exc_info=True)
                await event.reply(f"编辑结果页时出错：{e}")

    async def callback_page_handler(self, data, event) -> None:
        try:
            # 解析格式：page_{query}_{page_number}
            _, query, page_str = data.split('_')
            page_number = int(page_str)
            # 根据配置从缓存中获取或重新获取搜索结果
            results = None
            if SEARCH_CACHE:
                results = self.search_results_cache.get(query)
            if not results:
                results = await self.get_search_results(query, limit=MAX_RESULTS)
                self.search_results_cache[query] = results
                # 后台异步清理缓存，无需阻塞执行
                asyncio.create_task(self.clean_cache(query))
            await event.edit(f"正在加载第 {page_number + 1} 页...")
            await self.edit_results_page(event, results, page_number, query)
        except Exception as e:
            self.logger.error(f"翻页搜索出错：{e}", exc_info=True)
            await event.answer(f"搜索出错：{e}", alert=True)

    async def callback_ban_handler(self, data, event) -> None:
        try:
            user_id = int(data[len("ban_yes_"):])
            config = load_config()
            banned_ids = config['bot'].get('banned_ids', [])
            if user_id not in banned_ids:
                banned_ids.append(user_id)
                config['bot']['banned_ids'] = banned_ids
                save_config(config)
                await event.edit(f"用户 {user_id} 已添加到阻止名单中")
            else:
                await event.edit(f"用户 {user_id} 已经在阻止名单中")
        except Exception as e:
            self.logger.error(f"添加阻止名单中失败: {e}", exc_info=True)
            await event.answer(f"添加阻止名单中失败: {e}", alert=True)

    async def callback_delete_handler(self, data, event) -> None:
        try:
            delete_list = data[len("d`y`"):]
            delete_list = ast.literal_eval(delete_list)
            target_keyword_list = [f'"{keyword}"' for keyword in delete_list]
            for target_keyword in target_keyword_list:
                self.meili.delete_all_contain_keyword(target_keyword)
            await event.reply("已删除所有包含关键词的文档")
        except Exception as e:
            self.logger.error(f"删除关键词失败: {e}", exc_info=True)
            await event.answer(f"删除关键词失败: {e}", alert=True)

    async def callback_handler(self, event) -> None:
        data = event.data.decode('utf-8')
        if data.startswith('page_'):
            await self.callback_page_handler(data, event)
        elif data.startswith("ban_yes_"):
            await self.callback_ban_handler(data, event)
        elif data.startswith("ban_no_"):
            await event.edit("已取消添加")
        elif data.startswith("d`y`"):
            await self.callback_delete_handler(data, event)
        elif data.startswith("d`n"):
            await event.edit("已取消删除")
        else:
            self.logger.info(f"未知回调数据: {data}")
            await event.answer("未知回调数据", alert=True)

    @set_permission
    async def ban_command_handler(self, event) -> None:
        """
        处理 /ban 命令，格式：/ban 123 广告4 321
        将能转换为 int 的参数加入 banned_ids，将其他参数加入 banned_words
        """
        tokens = event.text.split()[1:]
        if not tokens:
            await event.reply("用法: /ban <id或关键词> ...")
            return
        config = load_config()
        banned_ids = config['bot'].get('banned_ids', [])
        banned_words = config['bot'].get('banned_words', [])
        new_ids = []
        new_words = []
        for token in tokens:
            try:
                val = int(token)
                if val not in banned_ids:
                    banned_ids.append(val)
                    new_ids.append(val)
            except ValueError:
                if token not in banned_words:
                    banned_words.append(token)
                    new_words.append(token)
        config['bot']['banned_ids'] = banned_ids
        config['bot']['banned_words'] = banned_words
        save_config(config)
        reply_msg = "已添加：\n"
        if new_ids:
            reply_msg += f"阻止名单 ID: {new_ids}\n"
        if new_words:
            reply_msg += f"禁用关键词: {new_words}"
        await event.reply(reply_msg)

    @set_permission
    async def banlist_handler(self, event) -> None:
        """
        处理 /banlist 命令，显示当前 banned_ids 与 banned_words
        """
        config = load_config()
        banned_ids = config['bot'].get('banned_ids', [])
        banned_words = config['bot'].get('banned_words', [])

        banned_ids_str = '\n'.join(map(str, banned_ids)) if banned_ids else '无'
        banned_words_str = '\n'.join(banned_words) if banned_words else '无'

        reply_msg = (
            "当前阻止名单信息：\n"
            f"阻止名单 IDs:\n{banned_ids_str}\n\n"
            f"禁用关键词:\n{banned_words_str}"
        )
        await event.reply(reply_msg)

    async def forwarded_message_handler(self, event) -> None:
        from telethon.tl.types import PeerUser

        # 确保存在转发信息
        if not event.fwd_from:
            return

        # 安全获取用户 ID
        try:
            from_id = event.fwd_from.from_id
            if not isinstance(from_id, PeerUser):
                await event.reply("⚠️ 仅支持用户来源的转发消息")
                return

            from_user_id = from_id.user_id
        except AttributeError:
            await event.reply("❌ 无法获取来源用户信息")
            return

        text = f"你是否要将用户 {from_user_id} 添加到阻止名单？"
        buttons = [
            Button.inline("是", data=f"ban_yes_{from_user_id}"),
            Button.inline("否", data=f"ban_no_{from_user_id}")
        ]
        await event.reply(text, buttons=buttons)

    @set_permission
    async def set_config(self, event) -> None:
        tokens = event.text.split()[1:]
        try:
            self.logger.info(f"设置配置项: {tokens}")
            if not tokens:
                await event.reply("用法: /set <white_list|black_list|banned_words|banned_ids|incremental> <value:List>")
                return
            key, value = tokens
            config = load_config()
            if key in {'white_list','wl'}:
                config['bot']['white_list'] = ast.literal_eval(value)
            elif key == 'black_list':
                config['bot']['black_list'] = ast.literal_eval(value)
            elif key in {'banned_words','bw'}:
                config['bot']['banned_words'] = ast.literal_eval(value)
            elif key in {'banned_ids', 'bi'}:
                config['bot']['banned_ids'] = ast.literal_eval(value)
            elif key in {'incremental','inc'}:
                config['download_incremental'] = ast.literal_eval(value)
            else:
                await event.reply("未知配置项")
                return
            save_config(config)
            await event.reply(f"设置配置项 {key} 成功")
        except Exception as e:
            self.logger.error(f"设置配置出错: {e}", exc_info=True)
            await event.reply(f"设置配置出错: {e}")

    @set_permission
    async def list_part_config(self, event) -> None:
        try:
            config = load_config()
            await event.reply(f"当前配置:"
                              f"\n白名单: {config['bot']['white_list']}"
                              f"\n黑名单: {config['bot']['black_list']}"
                              f"\n禁用关键词: {config['bot']['banned_words']}"
                              f"\n禁用用户: {config['bot']['banned_ids']}"
                              f"\n增量下载: {config['download_incremental']}"
                              )
        except Exception as e:
            self.logger.error(f"获取配置出错: {e}", exc_info=True)
            await event.reply(f"获取配置出错: {e}")

    @set_permission
    async def delete_all_contain_keyword(self, event) -> None:
        try:
            target_keyword_list = event.text.split()[1:] or BANNED_WORDS
            text = f"你是否要删除所有包含关键词{target_keyword_list}的文档？"
            buttons = [
                Button.inline("是", data=f"d`y`{target_keyword_list}"),
                Button.inline("否", data=f"d`n")
            ]
            await event.reply(text, buttons=buttons)

        except Exception as e:
            self.logger.error(f"删除包含关键词的文档失败: {e}", exc_info=True)
            await event.edit(f"删除包含关键词的文档失败: {e}")
