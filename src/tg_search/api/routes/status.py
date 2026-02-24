"""
状态 API 路由

提供系统状态和对话列表接口
"""

import tracemalloc
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, Request

from tg_search.api.deps import MeiliSearchAsync, get_app_state, get_meili_async
from tg_search.api.models import ApiResponse, DialogInfo, DialogListResponse, SystemStatus
from tg_search.api.state import AppState

router = APIRouter()


@router.get(
    "",
    response_model=ApiResponse[SystemStatus],
    summary="系统状态",
    description="获取系统运行状态",
)
async def get_system_status(
    app_state: AppState = Depends(get_app_state),
    meili: MeiliSearchAsync = Depends(get_meili_async),
) -> ApiResponse[SystemStatus]:
    """获取系统状态"""
    # 检查 MeiliSearch 连接
    meili_connected = True
    indexed_messages = 0
    try:
        stats = await meili.get_index_stats()
        indexed_messages = stats.number_of_documents
    except Exception:
        meili_connected = False

    # 获取内存使用
    memory_usage_mb = 0.0
    if tracemalloc.is_tracing():
        current, peak = tracemalloc.get_traced_memory()
        memory_usage_mb = current / (1024 * 1024)
    else:
        try:
            import resource

            usage = resource.getrusage(resource.RUSAGE_SELF)
            memory_usage_mb = usage.ru_maxrss / 1024  # Linux: KB -> MB
        except (ImportError, AttributeError):
            pass

    status = SystemStatus(
        uptime_seconds=app_state.uptime_seconds,
        meili_connected=meili_connected,
        bot_connected=app_state.is_bot_running,
        telegram_connected=app_state.telegram_client is not None,
        indexed_messages=indexed_messages,
        memory_usage_mb=round(memory_usage_mb, 2),
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
    app_state: AppState = Depends(get_app_state),
) -> ApiResponse[dict]:
    """获取所有下载进度"""
    all_progress = app_state.progress_registry.get_all_progress()
    progress_data = {str(k): v.to_dict() for k, v in all_progress.items()}
    active_count = sum(1 for v in all_progress.values() if v.status == "downloading")

    return ApiResponse(data={"progress": progress_data, "count": active_count})
