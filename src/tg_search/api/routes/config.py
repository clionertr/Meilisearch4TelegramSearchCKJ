"""
配置 API 路由

提供配置查询和更新接口
"""

from fastapi import APIRouter, Depends, HTTPException

from tg_search.api.deps import get_config_policy_service
from tg_search.api.models import ApiResponse, ConfigModel, ListUpdateRequest, ListUpdateResponse
from tg_search.config import settings
from tg_search.services import DomainError
from tg_search.services.config_policy_service import ConfigPolicyService

router = APIRouter()


_DOMAIN_ERROR_STATUS: dict[str, int] = {
    "policy_invalid_ids": 422,
    "policy_version_conflict": 409,
    "policy_store_unavailable": 503,
    "policy_invalid_action": 400,
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


@router.get(
    "",
    response_model=ApiResponse[ConfigModel],
    summary="获取配置",
    description="获取当前系统配置",
)
async def get_config(
    policy_service: ConfigPolicyService = Depends(get_config_policy_service),
) -> ApiResponse[ConfigModel]:
    """获取系统配置"""
    policy = await policy_service.get_policy()
    config = ConfigModel(
        white_list=policy.white_list,
        black_list=policy.black_list,
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
    policy_service: ConfigPolicyService = Depends(get_config_policy_service),
) -> ApiResponse[ListUpdateResponse]:
    """添加 ID 到白名单"""
    try:
        result = await policy_service.add_whitelist(request.ids, source="api")
    except DomainError as exc:
        raise _to_http_error(exc) from exc

    response = ListUpdateResponse(updated_list=result.updated_list, added=result.added, removed=result.removed)
    return ApiResponse(data=response, message=f"Added {len(result.added)} IDs to whitelist")


@router.delete(
    "/whitelist",
    response_model=ApiResponse[ListUpdateResponse],
    summary="移除白名单",
    description="从白名单移除 ID",
)
async def remove_from_whitelist(
    request: ListUpdateRequest,
    policy_service: ConfigPolicyService = Depends(get_config_policy_service),
) -> ApiResponse[ListUpdateResponse]:
    """从白名单移除 ID"""
    try:
        result = await policy_service.remove_whitelist(request.ids, source="api")
    except DomainError as exc:
        raise _to_http_error(exc) from exc

    response = ListUpdateResponse(updated_list=result.updated_list, added=result.added, removed=result.removed)
    return ApiResponse(data=response, message=f"Removed {len(result.removed)} IDs from whitelist")


@router.post(
    "/blacklist",
    response_model=ApiResponse[ListUpdateResponse],
    summary="添加黑名单",
    description="添加 ID 到黑名单",
)
async def add_to_blacklist(
    request: ListUpdateRequest,
    policy_service: ConfigPolicyService = Depends(get_config_policy_service),
) -> ApiResponse[ListUpdateResponse]:
    """添加 ID 到黑名单"""
    try:
        result = await policy_service.add_blacklist(request.ids, source="api")
    except DomainError as exc:
        raise _to_http_error(exc) from exc

    response = ListUpdateResponse(updated_list=result.updated_list, added=result.added, removed=result.removed)
    return ApiResponse(data=response, message=f"Added {len(result.added)} IDs to blacklist")


@router.delete(
    "/blacklist",
    response_model=ApiResponse[ListUpdateResponse],
    summary="移除黑名单",
    description="从黑名单移除 ID",
)
async def remove_from_blacklist(
    request: ListUpdateRequest,
    policy_service: ConfigPolicyService = Depends(get_config_policy_service),
) -> ApiResponse[ListUpdateResponse]:
    """从黑名单移除 ID"""
    try:
        result = await policy_service.remove_blacklist(request.ids, source="api")
    except DomainError as exc:
        raise _to_http_error(exc) from exc

    response = ListUpdateResponse(updated_list=result.updated_list, added=result.added, removed=result.removed)
    return ApiResponse(data=response, message=f"Removed {len(result.removed)} IDs from blacklist")
