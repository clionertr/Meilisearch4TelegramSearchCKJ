"""
Storage API 路由 (P1-ST)

提供存储统计与轻量清理接口
"""

from fastapi import APIRouter, Depends, Request

from tg_search.api.deps import (
    MeiliSearchAsync,
    get_app_state,
    get_config_store,
    get_meili_async,
)
from tg_search.api.models import (
    ApiResponse,
    AutoCleanData,
    AutoCleanRequest,
    CacheCleanupData,
    MediaCleanupData,
    StorageStatsData,
)

router = APIRouter()


@router.get(
    "/stats",
    response_model=ApiResponse[StorageStatsData],
    summary="存储统计",
    description="获取当前存储统计信息（index_bytes 来自 MeiliSearch databaseSize）",
)
async def get_storage_stats(
    meili: MeiliSearchAsync = Depends(get_meili_async),
) -> ApiResponse[StorageStatsData]:
    """
    AC-2: 返回 200 且包含 index_bytes/total_bytes。
    AC-3: media_bytes=null 且 media_supported=false。
    """
    notes = ["media storage is disabled in current architecture"]

    try:
        all_stats = await meili.get_all_stats()
        index_bytes = all_stats.get("databaseSize")
    except Exception:
        index_bytes = None
        notes.append("failed to retrieve databaseSize from MeiliSearch")

    data = StorageStatsData(
        total_bytes=index_bytes,
        index_bytes=index_bytes,
        media_supported=False,
        cache_supported=False,
        notes=notes,
    )
    return ApiResponse(data=data)


@router.patch(
    "/auto-clean",
    response_model=ApiResponse[AutoCleanData],
    summary="配置自动清理",
    description="启用/禁用自动清理并设置保留天数，配置持久化到 ConfigStore",
)
async def patch_auto_clean(
    body: AutoCleanRequest,
    request: Request,
    config_store=Depends(get_config_store),
) -> ApiResponse[AutoCleanData]:
    """
    AC-4: 返回 200 且配置持久化。
    """
    config_store.update_section(
        "storage",
        {
            "auto_clean_enabled": body.enabled,
            "media_retention_days": body.media_retention_days,
        },
    )

    data = AutoCleanData(
        enabled=body.enabled,
        media_retention_days=body.media_retention_days,
    )
    return ApiResponse(data=data)


@router.post(
    "/cleanup/cache",
    response_model=ApiResponse[CacheCleanupData],
    summary="清理缓存",
    description="清理 API 进程内缓存（dialog available cache、config cache）",
)
async def cleanup_cache(
    request: Request,
) -> ApiResponse[CacheCleanupData]:
    """
    AC-5: 返回 200 且返回 targets_cleared。
    ADR-ST-002: 清理范围限定在 API 进程可控缓存。
    """
    targets: list[str] = []

    app_state = await get_app_state(request)

    # 清理 dialog available 缓存
    if app_state.dialog_available_cache is not None:
        app_state.dialog_available_cache.invalidate()
        targets.append("dialogs_cache")

    # 清理 ConfigStore 内部缓存
    if app_state.config_store is not None:
        app_state.config_store._cache.invalidate()
        targets.append("config_cache")

    data = CacheCleanupData(targets_cleared=targets)
    return ApiResponse(data=data)


@router.post(
    "/cleanup/media",
    response_model=ApiResponse[MediaCleanupData],
    summary="清理媒体",
    description="当前版本媒体清理未启用，固定返回 not_applicable",
)
async def cleanup_media() -> ApiResponse[MediaCleanupData]:
    """
    AC-6: 返回 200 且 not_applicable=true。
    ADR-ST-001: P1 阶段不虚构媒体存储能力。
    """
    data = MediaCleanupData()
    return ApiResponse(data=data)
