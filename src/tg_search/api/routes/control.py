"""
客户端控制 API 路由

提供 Telegram 客户端的启动和停止接口
"""

import asyncio

from fastapi import APIRouter, Depends, HTTPException

from tg_search.api.deps import get_app_state
from tg_search.api.models import ApiResponse, ClientControlResponse
from tg_search.api.state import AppState
from tg_search.core.logger import setup_logger

logger = setup_logger()

router = APIRouter()


@router.post(
    "/start",
    response_model=ApiResponse[ClientControlResponse],
    summary="启动客户端",
    description="启动 Telegram 客户端（消息下载和监听）",
)
async def start_client(
    app_state: AppState = Depends(get_app_state),
) -> ApiResponse[ClientControlResponse]:
    """
    启动 Telegram 客户端

    如果客户端已在运行，返回 already_running 状态
    """
    if app_state.is_bot_running:
        response = ClientControlResponse(
            status="already_running",
            message="Telegram client is already running",
        )
        return ApiResponse(data=response)

    if app_state.api_only:
        raise HTTPException(
            status_code=400,
            detail="Cannot start client in API-only mode. Restart server without API_ONLY=true",
        )

    try:
        # 导入并启动主函数
        from tg_search.main import run

        if app_state.service_container is None:
            raise HTTPException(status_code=503, detail="ServiceContainer not initialized")

        # 在后台任务中运行
        app_state.bot_task = asyncio.create_task(
            run(
                progress_registry=app_state.progress_registry,
                services=app_state.service_container,
            )
        )
        logger.info("Telegram client started via API")

        response = ClientControlResponse(
            status="started",
            message="Telegram client started successfully",
        )
        return ApiResponse(data=response)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start Telegram client: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start client: {str(e)}")


@router.post(
    "/stop",
    response_model=ApiResponse[ClientControlResponse],
    summary="停止客户端",
    description="停止 Telegram 客户端",
)
async def stop_client(
    app_state: AppState = Depends(get_app_state),
) -> ApiResponse[ClientControlResponse]:
    """
    停止 Telegram 客户端

    取消正在运行的 Bot 任务
    """
    if not app_state.is_bot_running:
        response = ClientControlResponse(
            status="already_stopped",
            message="Telegram client is not running",
        )
        return ApiResponse(data=response)

    try:
        # 取消任务
        if app_state.bot_task:
            app_state.bot_task.cancel()
            try:
                await app_state.bot_task
            except asyncio.CancelledError:
                pass
            app_state.bot_task = None

        # 清理 Telegram 客户端
        if app_state.telegram_client:
            await app_state.telegram_client.cleanup()
            app_state.telegram_client = None

        logger.info("Telegram client stopped via API")

        response = ClientControlResponse(
            status="stopped",
            message="Telegram client stopped successfully",
        )
        return ApiResponse(data=response)

    except Exception as e:
        logger.error(f"Failed to stop Telegram client: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop client: {str(e)}")


@router.get(
    "/status",
    summary="客户端状态",
    description="获取 Telegram 客户端运行状态",
)
async def get_client_status(
    app_state: AppState = Depends(get_app_state),
) -> ApiResponse[dict]:
    """获取客户端状态"""
    status = {
        "is_running": app_state.is_bot_running,
        "api_only_mode": app_state.api_only,
        "telegram_connected": app_state.telegram_client is not None,
        "bot_handler_initialized": app_state.bot_handler is not None,
    }
    return ApiResponse(data=status)
