"""
状态 API 路由

提供系统状态和对话列表接口
"""

from typing import List

from fastapi import APIRouter, Depends

from tg_search.api.deps import get_app_state, get_observability_service
from tg_search.api.models import ApiResponse, DialogInfo, DialogListResponse, SystemStatus
from tg_search.api.state import AppState
from tg_search.core.logger import setup_logger
from tg_search.services.observability_service import ObservabilityService

router = APIRouter()
logger = setup_logger()


async def _resolve_runtime_connected(app_state: AppState) -> bool:
    """
    Resolve Telegram runtime connectivity from the canonical runtime controller.

    Fallback to legacy AppState flags for compatibility with older bootstrap paths.
    """
    runtime = getattr(app_state, "runtime_control_service", None)
    if runtime is None and app_state.service_container is not None:
        runtime = getattr(app_state.service_container, "runtime_control_service", None)

    if runtime is not None:
        try:
            runtime_status = await runtime.status()
            return bool(runtime_status.is_running)
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.warning(
                "[status] runtime status probe failed, fallback to legacy flags: %s: %s",
                type(exc).__name__,
                exc,
            )

    return bool(app_state.telegram_client is not None or app_state.is_bot_running)


@router.get(
    "",
    response_model=ApiResponse[SystemStatus],
    summary="系统状态",
    description="获取系统运行状态",
)
async def get_system_status(
    app_state: AppState = Depends(get_app_state),
    observability: ObservabilityService = Depends(get_observability_service),
) -> ApiResponse[SystemStatus]:
    """获取系统状态"""
    runtime_connected = await _resolve_runtime_connected(app_state)

    snapshot = await observability.system_snapshot(
        uptime_seconds=app_state.uptime_seconds,
        bot_running=runtime_connected or app_state.is_bot_running,
        telegram_connected=runtime_connected,
        source="api.status",
    )

    status = SystemStatus(
        uptime_seconds=snapshot.uptime_seconds,
        meili_connected=snapshot.meili_connected,
        bot_connected=snapshot.bot_running,
        telegram_connected=snapshot.telegram_connected,
        indexed_messages=snapshot.indexed_messages,
        memory_usage_mb=snapshot.memory_usage_mb,
        notes=snapshot.notes,
    )

    return ApiResponse(data=status)


@router.get(
    "/dialogs",
    response_model=ApiResponse[DialogListResponse],
    summary="对话列表",
    description="获取已同步的对话列表",
)
async def get_dialogs(
    app_state: AppState = Depends(get_app_state),
) -> ApiResponse[DialogListResponse]:
    """
    获取对话列表

    返回已同步的 Telegram 对话列表
    """
    dialogs: List[DialogInfo] = []

    # 从进度注册表获取对话信息
    all_progress = app_state.progress_registry.get_all_progress()
    for dialog_id, progress in all_progress.items():
        dialogs.append(
            DialogInfo(
                id=dialog_id,
                title=progress.dialog_title,
                type="unknown",  # 从进度信息无法获取类型
                message_count=progress.current,
                last_synced=progress.updated_at,
                is_syncing=progress.status == "downloading",
            )
        )

    response = DialogListResponse(
        dialogs=dialogs,
        total=len(dialogs),
    )

    return ApiResponse(data=response)


@router.get(
    "/progress",
    summary="下载进度",
    description="获取当前所有下载任务的进度",
)
async def get_download_progress(
    observability: ObservabilityService = Depends(get_observability_service),
) -> ApiResponse[dict]:
    """获取所有下载进度"""
    snapshot = await observability.progress_snapshot(source="api.status.progress")

    return ApiResponse(data={"progress": snapshot.all_progress, "count": snapshot.active_count})
