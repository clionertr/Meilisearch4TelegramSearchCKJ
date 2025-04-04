# app.py (部分关键代码)
import asyncio
import nest_asyncio
from concurrent.futures import ThreadPoolExecutor
from flask import Flask
import logging # 使用 logging 模块
import traceback # 用于打印完整错误堆栈

# 导入重构后的核心组件和实例
from Meilisearch4TelegramSearchCKJ.src.models.telegram_bot import TelegramBot
from Meilisearch4TelegramSearchCKJ.src.main import meili, download_and_listen_task, setup_logger # 导入 logger 设置函数

# 初始化 Flask 应用
app = Flask(__name__)

# 获取/设置 logger
# logger = logging.getLogger(__name__) # 或者使用 main.py 的 logger
logger = setup_logger() # 使用 main.py 的 logger

async def async_bot_task():
    """异步运行 Bot 的核心任务"""
    try:
        logger.info("async_bot_task: 开始...")
        logger.info("async_bot_task: 实例化 TelegramBot...")
        # 实例化新的 TelegramBot，传入 meili 实例和启动 UserBot 的函数
        telegram_bot = TelegramBot(meili, download_and_listen_task)
        logger.info("async_bot_task: TelegramBot 实例化完毕. 调用 run()...")
        # 运行 Bot (它会管理 UserBot 的启动)
        await telegram_bot.run()
        logger.info("async_bot_task: telegram_bot.run() 执行完毕 (如果 Bot 正常停止).") # 正常情况不应执行到这里
    except asyncio.CancelledError:
         logger.info("async_bot_task: 被取消.")
    except Exception as e:
        # 使用 logger 记录完整的错误信息和堆栈跟踪
        logger.error(f"async_bot_task: 运行 Bot 时出错: {str(e)}\n{traceback.format_exc()}")
    finally:
        logger.info("async_bot_task: 结束.")

def run_async_code():
    """在新线程中设置事件循环并运行异步代码"""
    logger.info("run_async_code: 进入后台线程.")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    logger.info("run_async_code: 应用 nest_asyncio.")
    nest_asyncio.apply()
    logger.info("run_async_code: 运行 async_bot_task...")
    try:
        loop.run_until_complete(async_bot_task())
    finally:
         logger.info("run_async_code: loop.run_until_complete 执行完毕.")
         # loop.close() # 在某些情况下需要关闭 loop


@app.route('/')
def health_check():
    """健康检查端点"""
    return {"status": "healthy"}, 200


def start_background_tasks():
    """启动后台任务"""
    logger.info("start_background_tasks: 启动后台线程执行 Bot...")
    executor = ThreadPoolExecutor(max_workers=1)
    executor.submit(run_async_code)
    # 注意: 这里的 executor 没有 shutdown，对于长时间运行的服务可能是期望行为，
    # 但在退出时可能需要处理。


if __name__ == "__main__":
    # 确保在启动 Flask 前启动后台任务
    start_background_tasks()

    # 启动 Flask 应用 (在主线程)
    logger.info("启动 Flask 应用...")
    # 注意: use_reloader=False 在生产环境中或调试多线程/进程时通常是必要的，
    # 因为 reloader 会启动两个进程，可能导致后台任务运行两次或出现问题。
    app.run(host="0.0.0.0", port=7860, use_reloader=False)