import gc

from telethon import TelegramClient, events, Button
from Meilisearch4TelegramSearchCKJ.src.config.env import TOKEN, MEILI_HOST, MEILI_PASS, APP_ID, APP_HASH, RESULTS_PER_PAGE
from Meilisearch4TelegramSearchCKJ.src.models.meilisearch_handler import MeiliSearchClient
from Meilisearch4TelegramSearchCKJ.src.utils.fmt_size import sizeof_fmt
from Meilisearch4TelegramSearchCKJ.src.models.logger import setup_logger

logger = setup_logger()

# 初始化 Telegram 客户端
bot_client = TelegramClient('bot', APP_ID, APP_HASH).start(bot_token=TOKEN)

# 初始化 MeiliSearch 客户端
meili = MeiliSearchClient(MEILI_HOST, MEILI_PASS)



# 全局缓存，存储每个搜索词的结果
search_results_cache = {}

# 搜索命令处理器
async def search_handler(event, query):
    try:
        results = await get_search_results(query)
        if results:
            search_results_cache[query] = results  # 缓存结果
            await send_results_page(event, results, 0, query)
            search_results_cache[query].extend(await get_search_results(query, limit=40, offset=10))
        else:
            await event.reply("没有找到相关结果。")
    except Exception as e:
        await event.reply(f"搜索出错：{e}")
        print(f"搜索出错：{e}")


async def get_search_results(query, limit=10, offset=0,index_name='telegram'):
    """从 MeiliSearch 获取搜索结果"""
    try:
        results = meili.search(query,index_name,limit=limit,offset=offset)  # 限制单次查询数量，避免一次性返回过多结果
        return results['hits'] if results['hits'] else None
    except Exception as e:
        print(f"MeiliSearch 查询出错：{e}")
        return None

# 定义指令处理器
@bot_client.on(events.NewMessage(pattern=r'^/(start|help)$'))
async def start_handler(event):
    await event.reply("""
🔍 Telegram 消息搜索机器人
这个机器人可以让你搜索保存的 Telegram 消息历史记录。

基本命令：
• 直接输入任何文本以搜索消息
• 结果将显示发送者、发送位置、时间及消息预览

管理员命令：
/ping - 检查搜索服务是否运行
/delete - 从数据库中删除消息
• /delete - 删除所有消息（需要确认）
• /delete chat <chat_id> - 从特定聊天删除所有消息
• /delete user <user_id> - 从特定用户删除所有消息

同步管理：
/add_sync <chat_id> - 将聊天添加到同步列表并进行白名单处理
/remove_sync <chat_id> - 从同步列表中移除聊天
/list_sync - 显示所有在同步列表中的聊天
/list - 显示完整的同步配置

客户端管理：
/start_client - 启动消息同步客户端
/stop_client - 停止消息同步客户端
/restart_client - 重启消息同步客户端
/live - 检查客户端状态
/view_client_log - 查看客户端日志的最后50行

搜索过滤器：
/filter 或 /f - 设置搜索过滤器
示例： /f ["chat.type": "ChatType.PRIVATE"]

导航：
• 使用⬅️ 上一页和下一页 ➡️ 按钮浏览搜索结果
• 每页最多显示10条结果

注意事项：
• 消息会自动从白名单聊天中同步
• 搜索结果包括消息文本、发送者信息、聊天信息及直接链接
• 对于较长的搜索结果，机器人会将其作为文本文件发送
""")

@bot_client.on(events.NewMessage(pattern=r'^/search (.+)'))
async def search_command_handler(event):
    logger.info(f"Received search command: {event.pattern_match.group(1)}")
    query = event.pattern_match.group(1)
    await search_handler(event, query)


@bot_client.on(events.NewMessage(pattern=r'^/cc$'))
async def clean(event):
    global search_results_cache
    await event.reply("正在清理缓存...")
    search_results_cache.clear()
    await event.reply("缓存已清理。")
    gc.collect()



@bot_client.on(events.NewMessage(pattern=r'^/about$'))
async def about_handler(event):
    await event.reply("本项目基于 MeiliSearch 和 Telethon 构建，用于搜索保存的 Telegram 消息历史记录。解决了 Telegram 中文搜索功能的不足，提供了更强大的搜索功能。\n   \n    本项目的github地址为：[Meilisearch4TelegramSearchCKJ](https://github.com/clionertr/Meilisearch4TelegramSearchCKJ)，如果觉得好用可以点个star\n\n    得益于telethon的优秀代码，相比使用pyrogram，本项目更加稳定，同时减少大量负载\n\n    项目由[SearchGram](https://github.com/tgbot-collection/SearchGram)重构而来，感谢原作者的贡献❤️\n\n    同时感谢Claude3.5s和GeminiExp的帮助\n\n    从这次的编程中，我学到了很多，也希望大家能够喜欢这个项目😘")


@bot_client.on(events.NewMessage(pattern=r'^/ping$'))
async def ping_handler(event):
    text = "Pong!\n"
    stats = meili.client.get_all_stats()
    size = stats["databaseSize"]
    last_update = stats["lastUpdate"]
    for uid, index in stats["indexes"].items():
        text += f"Index {uid} has {index['numberOfDocuments']} documents\n"
    text += f"\nDatabase size: {sizeof_fmt(size)}\nLast update: {last_update}\n"
    await event.reply(text)

@bot_client.on(events.NewMessage(func=lambda e: e.is_private and not e.text.startswith('/')))
async def message_handler(event):
    await search_handler(event, event.raw_text)

def format_search_result(hit):
    """格式化搜索结果"""
    text = hit['text']

    chat_type = hit['chat']['type']
    if chat_type == 'private':
        chat_title = f"Private：{hit['chat']['username']}"
    elif chat_type == 'channel':
        chat_title = f"Channel：{hit['chat']['title']}"
    else:
        chat_title = f"Group：{hit['chat']['title']}"



    chat_username = hit['chat'].get('username', 'N/A')
    date = hit['date'].split('T')[0]  # 只显示日期部分
    url = f"https://t.me/{chat_username}/{hit['id'].split('-')[1]}" if chat_username != 'N/A' else 'N/A'
    return f"- **{chat_title}**  ({date})\n{text}\n  [🔗Jump]({url})\n" + "—" * 18 + "\n"

async def send_results_page(event, hits, page_number, query):
    """发送指定页码的搜索结果"""
    start_index = page_number * RESULTS_PER_PAGE
    end_index = min((page_number + 1) * RESULTS_PER_PAGE, len(hits))
    page_results = hits[start_index:end_index]

    if not page_results:
        await event.reply("没有更多结果了。")
        return

    response = "".join([format_search_result(hit) for hit in page_results])
    buttons = []
    if page_number > 0:
        buttons.append(Button.inline("上一页", data=f"page_{query}_{page_number - 1}"))
    if end_index < len(hits):
        buttons.append(Button.inline("下一页", data=f"page_{query}_{page_number + 1}"))

    # 异步发送消息，避免阻塞
    await bot_client.send_message(event.chat_id, f"搜索结果 (第 {page_number + 1} 页):\n{response}", buttons=buttons)

async def edit_results_page(event, hits, page_number, query):
    """编辑指定页码的搜索结果"""
    start_index = page_number * RESULTS_PER_PAGE
    end_index = min((page_number + 1) * RESULTS_PER_PAGE, len(hits))
    page_results = hits[start_index:end_index]

    if not page_results:
        await event.reply("没有更多结果了。")
        return

    response = "".join([format_search_result(hit) for hit in page_results])
    buttons = []
    if page_number > 0:
        buttons.append(Button.inline("上一页", data=f"page_{query}_{page_number - 1}"))
    if end_index < len(hits):
        buttons.append(Button.inline("下一页", data=f"page_{query}_{page_number + 1}"))

    # 异步发送消息，避免阻塞
    await event.edit(f"搜索结果 (第 {page_number + 1} 页):\n{response}", buttons=buttons)


# noinspection PyTypeChecker
@bot_client.on(events.CallbackQuery)
async def callback_query_handler(event):
    """处理内联按钮回调"""
    data = event.data.decode('utf-8')
    if data.startswith('page_'):
        parts = data.split('_')
        query = parts[1]
        page_number = int(parts[2])
        try:
            # 尝试从缓存中获取结果
            results = search_results_cache.get(query)
            if results is None:
                # 如果缓存中没有，则重新查询
                results = await get_search_results(query)
                if results:
                    search_results_cache[query] = results
                else:
                    await event.answer("没有找到相关结果。", alert=True)
                    return
            await event.edit(f"正在加载第 {page_number + 1} 页...")
            #await send_results_page(event, results, page_number, query)
            await edit_results_page(event, results, page_number, query)
        except Exception as e:
            await event.answer(f"搜索出错：{e}", alert=True)
            print(f"搜索出错：{e}")

# 启动客户端
logger.log(25, "Bot started")
bot_client.run_until_disconnected()