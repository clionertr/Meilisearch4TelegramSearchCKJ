"""
客户端控制 API 路由

提供 Telegram 客户端的启动和停止接口
"""

from fastapi import APIRouter, Depends, HTTPException

from tg_search.api.deps import get_app_state, get_runtime_control_service
from tg_search.api.models import ApiResponse, ClientControlResponse
from tg_search.api.state import AppState
from tg_search.core.logger import setup_logger
from tg_search.services import DomainError
from tg_search.services.runtime_control_service import RuntimeControlService

logger = setup_logger()

router = APIRouter()

_DOMAIN_ERROR_STATUS: dict[str, int] = {
    "runtime_api_only_mode": 400,
    "runtime_start_failed": 500,
    "runtime_stop_failed": 500,
    "runtime_cleanup_failed": 500,
}


def _to_http_error(exc: DomainError) -> HTTPException:
    status_code = _DOMAIN_ERROR_STATUS.get(exc.code, 400)
    return HTTPException(
        status_code=status_code,
        detail={
            "error_code": exc.code,
            "message": exc.message,
            "detail": exc.detail,
        },
    )


@router.post(
    "/start",
    response_model=ApiResponse[ClientControlResponse],
    summary="启动客户端",
    description="启动 Telegram 客户端（消息下载和监听）",
)
async def start_client(
    runtime_service: RuntimeControlService = Depends(get_runtime_control_service),
) -> ApiResponse[ClientControlResponse]:
    """
    启动 Telegram 客户端

    如果客户端已在运行，返回 already_running 状态
    """
    try:
        result = await runtime_service.start(source="api")
        response = ClientControlResponse(
            status=result.status,
            message=result.message,
        )
        return ApiResponse(data=response)
    except DomainError as exc:
        raise _to_http_error(exc) from exc


@router.post(
    "/stop",
    response_model=ApiResponse[ClientControlResponse],
    summary="停止客户端",
    description="停止 Telegram 客户端",
)
async def stop_client(
    runtime_service: RuntimeControlService = Depends(get_runtime_control_service),
) -> ApiResponse[ClientControlResponse]:
    """
    停止 Telegram 客户端

    取消正在运行的 Bot 任务
    """
    try:
        result = await runtime_service.stop(source="api")
        response = ClientControlResponse(
            status=result.status,
            message=result.message,
        )
        return ApiResponse(data=response)
    except DomainError as exc:
        raise _to_http_error(exc) from exc


@router.get(
    "/status",
    summary="客户端状态",
    description="获取 Telegram 客户端运行状态",
)
async def get_client_status(
    app_state: AppState = Depends(get_app_state),
    runtime_service: RuntimeControlService = Depends(get_runtime_control_service),
) -> ApiResponse[dict]:
    """获取客户端状态"""
    runtime_status = await runtime_service.status()
    status = {
        "is_running": runtime_status.is_running,
        "api_only_mode": runtime_status.api_only_mode,
        "state": runtime_status.state,
        "last_action_source": runtime_status.last_action_source,
        "last_error": runtime_status.last_error,
        "telegram_connected": app_state.telegram_client is not None,
        "bot_handler_initialized": app_state.bot_handler is not None,
    }
    return ApiResponse(data=status)
