"""
配置 API 路由

提供配置查询和更新接口
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from tg_search.api.deps import MeiliSearchAsync, get_meili_async
from tg_search.api.models import ApiResponse, ConfigModel, ListUpdateRequest, ListUpdateResponse
from tg_search.config import settings

router = APIRouter()


@router.get(
    "",
    response_model=ApiResponse[ConfigModel],
    summary="获取配置",
    description="获取当前系统配置",
)
async def get_config() -> ApiResponse[ConfigModel]:
    """获取系统配置"""
    config = ConfigModel(
        white_list=settings.WHITE_LIST,
        black_list=settings.BLACK_LIST,
        owner_ids=settings.OWNER_IDS,
        batch_msg_num=settings.BATCH_MSG_UNM,
        results_per_page=settings.RESULTS_PER_PAGE,
        max_page=settings.MAX_PAGE,
        search_cache=settings.SEARCH_CACHE,
        cache_expire_seconds=settings.CACHE_EXPIRE_SECONDS,
    )
    return ApiResponse(data=config)


@router.post(
    "/whitelist",
    response_model=ApiResponse[ListUpdateResponse],
    summary="添加白名单",
    description="添加 ID 到白名单",
)
async def add_to_whitelist(
    request: ListUpdateRequest,
    meili: MeiliSearchAsync = Depends(get_meili_async),
) -> ApiResponse[ListUpdateResponse]:
    """添加 ID 到白名单"""
    added: List[int] = []
    for id_ in request.ids:
        if id_ not in settings.WHITE_LIST:
            settings.WHITE_LIST.append(id_)
            added.append(id_)

    # 持久化到 MeiliSearch（可选，根据项目实际需求）
    # await _persist_config_to_meili(meili, "white_list", settings.WHITE_LIST)

    response = ListUpdateResponse(
        updated_list=settings.WHITE_LIST.copy(),
        added=added,
    )
    return ApiResponse(data=response, message=f"Added {len(added)} IDs to whitelist")


@router.delete(
    "/whitelist",
    response_model=ApiResponse[ListUpdateResponse],
    summary="移除白名单",
    description="从白名单移除 ID",
)
async def remove_from_whitelist(
    request: ListUpdateRequest,
) -> ApiResponse[ListUpdateResponse]:
    """从白名单移除 ID"""
    removed: List[int] = []
    for id_ in request.ids:
        if id_ in settings.WHITE_LIST:
            settings.WHITE_LIST.remove(id_)
            removed.append(id_)

    response = ListUpdateResponse(
        updated_list=settings.WHITE_LIST.copy(),
        removed=removed,
    )
    return ApiResponse(data=response, message=f"Removed {len(removed)} IDs from whitelist")


@router.post(
    "/blacklist",
    response_model=ApiResponse[ListUpdateResponse],
    summary="添加黑名单",
    description="添加 ID 到黑名单",
)
async def add_to_blacklist(
    request: ListUpdateRequest,
) -> ApiResponse[ListUpdateResponse]:
    """添加 ID 到黑名单"""
    added: List[int] = []
    for id_ in request.ids:
        if id_ not in settings.BLACK_LIST:
            settings.BLACK_LIST.append(id_)
            added.append(id_)

    response = ListUpdateResponse(
        updated_list=settings.BLACK_LIST.copy(),
        added=added,
    )
    return ApiResponse(data=response, message=f"Added {len(added)} IDs to blacklist")


@router.delete(
    "/blacklist",
    response_model=ApiResponse[ListUpdateResponse],
    summary="移除黑名单",
    description="从黑名单移除 ID",
)
async def remove_from_blacklist(
    request: ListUpdateRequest,
) -> ApiResponse[ListUpdateResponse]:
    """从黑名单移除 ID"""
    removed: List[int] = []
    for id_ in request.ids:
        if id_ in settings.BLACK_LIST:
            settings.BLACK_LIST.remove(id_)
            removed.append(id_)

    response = ListUpdateResponse(
        updated_list=settings.BLACK_LIST.copy(),
        removed=removed,
    )
    return ApiResponse(data=response, message=f"Removed {len(removed)} IDs from blacklist")
