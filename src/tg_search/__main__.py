"""
tg_search 命令行入口

支持通过 `python -m tg_search` 运行应用

运行模式：
- all (默认): 同时运行 API 服务器和 Bot
- api-only: 仅运行 API 服务器
- bot-only: 仅运行 Bot（原有行为）
"""

import argparse
import asyncio
import os


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        prog="tg_search",
        description="Telegram CJK message search powered by MeiliSearch",
    )

    parser.add_argument(
        "--mode",
        choices=["all", "api-only", "bot-only"],
        default="all",
        help="运行模式: all (API+Bot), api-only (仅API), bot-only (仅Bot)",
    )

    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="API 服务器绑定地址 (默认: 0.0.0.0)",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="API 服务器端口 (默认: 8000)",
    )

    parser.add_argument(
        "--reload",
        action="store_true",
        help="启用热重载（开发模式）",
    )

    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="跳过配置验证",
    )

    return parser.parse_args()


def run_bot_only():
    """仅运行 Bot（原有行为）"""
    from tg_search.core.bot import BotHandler
    from tg_search.main import run
    from tg_search.services.container import build_service_container

    services = build_service_container()
    bot_handler = BotHandler(lambda: run(services=services), services=services)
    asyncio.run(bot_handler.run())


def run_api_only(host: str, port: int, reload: bool = False):
    """仅运行 API 服务器"""
    import uvicorn

    # 设置环境变量标记 API-only 模式
    os.environ["API_ONLY"] = "true"

    uvicorn.run(
        "tg_search.api.app:app",
        host=host,
        port=port,
        reload=reload,
        workers=1,  # 必须单 worker
        log_level="info",
    )


def run_all(host: str, port: int, reload: bool = False):
    """
    运行 API + Bot（默认模式）

    在 FastAPI lifespan 中启动 Bot 作为后台任务
    """
    import uvicorn

    # 设置环境变量
    os.environ["API_ONLY"] = "false"

    uvicorn.run(
        "tg_search.api.app:app",
        host=host,
        port=port,
        reload=reload,
        workers=1,  # 必须单 worker
        log_level="info",
    )


def main():
    """命令行入口函数"""
    args = parse_args()

    # 跳过配置验证
    if args.skip_validation:
        os.environ["SKIP_CONFIG_VALIDATION"] = "true"

    # 根据模式运行
    if args.mode == "bot-only":
        print("Starting in bot-only mode...")
        run_bot_only()
    elif args.mode == "api-only":
        print(f"Starting API server at http://{args.host}:{args.port} ...")
        print("API docs available at: /docs")
        run_api_only(args.host, args.port, args.reload)
    else:  # all
        print(f"Starting API server + Bot at http://{args.host}:{args.port} ...")
        print("API docs available at: /docs")
        print("Bot will start as background task...")
        run_all(args.host, args.port, args.reload)


if __name__ == "__main__":
    main()
