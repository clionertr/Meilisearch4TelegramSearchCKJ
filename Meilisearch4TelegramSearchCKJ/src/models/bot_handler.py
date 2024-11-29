import os
from telethon import TelegramClient, events, Button
from meilisearch import Client
from Meilisearch4TelegramSearchCKJ.src.config.env import TOKEN, MEILI_HOST, MEILI_PASS, APP_ID, APP_HASH
import asyncio

# 初始化 Telegram 客户端
client = TelegramClient('bot', APP_ID, APP_HASH).start(bot_token=TOKEN)

# 初始化 MeiliSearch 客户端
meiliclent1 = Client(MEILI_HOST, MEILI_PASS)

# 每页显示的结果数量
RESULTS_PER_PAGE = 5

# 全局缓存，存储每个搜索词的结果
search_results_cache = {}

# 搜索命令处理器
async def search_handler(event, query):
    try:
        results = await get_search_results(query)
        if results:
            search_results_cache[query] = results  # 缓存结果
            await send_results_page(event, results, 0, query)
        else:
            await event.reply("没有找到相关结果。")
    except Exception as e:
        await event.reply(f"搜索出错：{e}")
        print(f"搜索出错：{e}")

async def get_search_results(query):
    """从 MeiliSearch 获取搜索结果"""
    try:
        results = meiliclent1.index('telegram').search(query, {'limit': 100})  # 限制单次查询数量，避免一次性返回过多结果
        return results['hits'] if results['hits'] else None
    except Exception as e:
        print(f"MeiliSearch 查询出错：{e}")
        return None

# 定义指令处理器
@client.on(events.NewMessage(pattern=r'^/start$'))
async def start_handler(event):
    await event.reply("欢迎使用！\n\n"
                      "可用命令：\n"
                      "/start - 显示帮助信息\n"
                      "/search <关键词> - 搜索消息\n"
                      "/about - 关于 Bot")

@client.on(events.NewMessage(pattern=r'^/search (.+)'))
async def search_command_handler(event):
    query = event.pattern_match.group(1)
    await search_handler(event, query)

@client.on(events.NewMessage(pattern=r'^/about$'))
async def about_handler(event):
    await event.reply("这是一个基于 MeiliSearch 的 Telegram 消息搜索 Bot。\n"
                      "版本：v1.0\n"
                      "作者：Your Name")

@client.on(events.NewMessage(func=lambda e: e.is_private and not e.text.startswith('/')))
async def message_handler(event):
    await search_handler(event, event.raw_text)

def format_search_result(hit):
    """格式化搜索结果"""
    text = hit['text']
    chat_title = hit['chat']['title']
    chat_username = hit['chat'].get('username', 'N/A')
    date = hit['date'].split('T')[0]  # 只显示日期部分
    url = f"https://t.me/{chat_username}/{hit['id'].split('-')[1]}" if chat_username != 'N/A' else 'N/A'
    return f"- **{chat_title}**  ({date})\n  `{text[:50]}...`\n  [🔗链接]({url})\n" + "—" * 20 + "\n"

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
    await client.send_message(event.chat_id, f"搜索结果 (第 {page_number + 1} 页):\n{response}", buttons=buttons)

@client.on(events.CallbackQuery)
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
            await send_results_page(event, results, page_number, query)
        except Exception as e:
            await event.answer(f"搜索出错：{e}", alert=True)
            print(f"搜索出错：{e}")

# 启动客户端
print("Bot started!")
client.run_until_disconnected()