"""
tg_search 命令行入口

支持通过 `python -m tg_search` 运行应用
"""

import asyncio

from tg_search.core.bot import BotHandler
from tg_search.main import run


def main():
    """命令行入口函数"""
    bot_handler = BotHandler(run)
    asyncio.run(bot_handler.run())


if __name__ == "__main__":
    main()
