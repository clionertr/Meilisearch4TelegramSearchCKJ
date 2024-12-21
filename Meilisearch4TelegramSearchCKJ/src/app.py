from concurrent.futures import ThreadPoolExecutor

import nest_asyncio
from flask import Flask

from Meilisearch4TelegramSearchCKJ.src.main import *

app = Flask(__name__)


def run_async_code():
    """在新线程中运行异步代码"""
    # 创建新的事件循环
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # 应用nest_asyncio以允许嵌套使用事件循环
    nest_asyncio.apply()

    async def async_bot_task():
        try:
            bot_handler = BotHandler(run)
            await bot_handler.run()
        except Exception as e:
            print(f"Error running bot: {str(e)}")
    # 运行异步任务
    loop.run_until_complete(async_bot_task())


@app.route('/')
def health_check():
    """健康检查端点"""
    return {"status": "healthy"}, 200


def start_background_tasks():
    """启动后台任务"""
    # 创建线程池
    executor = ThreadPoolExecutor(max_workers=1)
    # 在新线程中运行异步代码
    executor.submit(run_async_code)


if __name__ == "__main__":
    # 启动后台任务
    start_background_tasks()

    # 启动Flask应用
    app.run(host="0.0.0.0", port=7860)