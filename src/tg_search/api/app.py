"""
FastAPI 应用构建模块

提供 FastAPI 应用实例的创建和配置
"""

import os
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from tg_search.api.models import ErrorResponse
from tg_search.api.routes import api_router
from tg_search.api.state import AppState
from tg_search.core.logger import setup_logger
from tg_search.core.meilisearch import (
    MeiliSearchAPIError,
    MeiliSearchClient,
    MeiliSearchConnectionError,
    MeiliSearchTimeoutError,
)

logger = setup_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    应用生命周期管理

    在启动时初始化共享资源，在关闭时清理
    """
    import asyncio

    from tg_search.config.settings import MEILI_HOST, MEILI_PASS

    # 创建应用状态
    app_state = AppState()
    app_state.start_time = datetime.utcnow()

    # 初始化 MeiliSearch 客户端
    try:
        app_state.meili_client = MeiliSearchClient(MEILI_HOST, MEILI_PASS)
        logger.info("MeiliSearch client initialized successfully")
    except (MeiliSearchConnectionError, MeiliSearchAPIError) as e:
        logger.error(f"Failed to initialize MeiliSearch client: {e}")
        # 允许 API 启动，但 meili_client 为 None

    # 检查是否为 API-only 模式
    app_state.api_only = os.getenv("API_ONLY", "false").lower() == "true"

    # 存储到 app.state
    app.state.app_state = app_state

    # 如果不是 API-only 模式，启动 Bot 作为后台任务
    if not app_state.api_only:
        try:
            from tg_search.core.bot import BotHandler
            from tg_search.main import run

            async def run_bot():
                """运行 Bot 的包装函数"""
                try:
                    bot_handler = BotHandler(run)
                    await bot_handler.run()
                except asyncio.CancelledError:
                    logger.info("Bot task was cancelled")
                except Exception as e:
                    logger.error(f"Bot error: {e}")

            app_state.bot_task = asyncio.create_task(run_bot())
            logger.info("Bot started as background task")
        except Exception as e:
            logger.error(f"Failed to start Bot: {e}")

    logger.info("API server started")
    yield

    # 清理资源
    if app_state.bot_task is not None and not app_state.bot_task.done():
        app_state.bot_task.cancel()
        try:
            await app_state.bot_task
        except asyncio.CancelledError:
            pass
        logger.info("Bot task cancelled")

    logger.info("API server shutdown")


def build_app() -> FastAPI:
    """
    构建 FastAPI 应用实例

    Returns:
        配置好的 FastAPI 应用
    """
    app = FastAPI(
        title="Telegram Search API",
        description="MeiliSearch powered Telegram message search backend",
        version="0.2.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS 配置
    cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    app.include_router(api_router)

    # 健康检查端点
    @app.get("/health", tags=["Health"])
    async def health_check():
        return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

    # 根端点
    @app.get("/", tags=["Root"])
    async def root():
        return {
            "name": "Telegram Search API",
            "version": "0.2.0",
            "docs": "/docs",
        }

    # 异常处理器
    @app.exception_handler(MeiliSearchConnectionError)
    async def meili_connection_exception_handler(request: Request, exc: MeiliSearchConnectionError):
        return JSONResponse(
            status_code=503,
            content=ErrorResponse(
                error_code="MEILI_CONNECTION_ERROR",
                message="MeiliSearch service unavailable",
                details=str(exc),
            ).model_dump(mode="json"),
        )

    @app.exception_handler(MeiliSearchTimeoutError)
    async def meili_timeout_exception_handler(request: Request, exc: MeiliSearchTimeoutError):
        return JSONResponse(
            status_code=504,
            content=ErrorResponse(
                error_code="MEILI_TIMEOUT_ERROR",
                message="MeiliSearch request timed out",
                details=str(exc),
            ).model_dump(mode="json"),
        )

    @app.exception_handler(MeiliSearchAPIError)
    async def meili_api_exception_handler(request: Request, exc: MeiliSearchAPIError):
        return JSONResponse(
            status_code=502,
            content=ErrorResponse(
                error_code="MEILI_API_ERROR",
                message="MeiliSearch API error",
                details=str(exc),
            ).model_dump(mode="json"),
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {type(exc).__name__}: {exc}")
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error_code="INTERNAL_ERROR",
                message="Internal server error",
                details=str(exc) if os.getenv("DEBUG", "false").lower() == "true" else None,
            ).model_dump(mode="json"),
        )

    return app


# 用于 uvicorn 直接运行
app = build_app()
