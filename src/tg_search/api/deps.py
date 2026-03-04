"""
依赖注入模块

提供 FastAPI 依赖注入函数
"""

import asyncio
import os
from functools import partial
from typing import TYPE_CHECKING, Any, Optional

from fastapi import Depends, Header, HTTPException, Request

if TYPE_CHECKING:
    from tg_search.api.auth_store import AuthStore, AuthToken
    from tg_search.api.state import AppState, ProgressRegistry
    from tg_search.config.config_store import ConfigStore
    from tg_search.core.meilisearch import MeiliSearchClient
    from tg_search.services.config_policy_service import ConfigPolicyService
    from tg_search.services.observability_service import ObservabilityService
    from tg_search.services.runtime_control_service import RuntimeControlService
    from tg_search.services.search_service import SearchService

async def get_app_state(request: Request) -> "AppState":
    """获取应用状态"""
    return request.app.state.app_state


async def get_meili_client(request: Request) -> "MeiliSearchClient":
    """获取 MeiliSearch 客户端"""
    app_state = await get_app_state(request)
    if app_state.meili_client is None:
        raise HTTPException(status_code=503, detail="MeiliSearch client not initialized")
    return app_state.meili_client


async def get_progress_registry(request: Request) -> "ProgressRegistry":
    """获取进度注册表"""
    app_state = await get_app_state(request)
    return app_state.progress_registry


async def run_sync_in_thread(func: Any, *args: Any, **kwargs: Any) -> Any:
    """
    将同步函数放入线程池执行

    用于包装 MeiliSearch 的同步调用，避免阻塞事件循环

    Args:
        func: 要执行的同步函数
        *args: 位置参数
        **kwargs: 关键字参数

    Returns:
        函数执行结果
    """
    # Escape hatch for unit tests / constrained environments.
    # When enabled, sync calls will run in the event loop thread (may block in production).
    if os.getenv("DISABLE_THREAD_OFFLOAD", "").lower() in ("1", "true", "yes"):
        return func(*args, **kwargs)

    return await asyncio.to_thread(partial(func, *args, **kwargs))


class MeiliSearchAsync:
    """
    MeiliSearch 异步包装器

    将同步的 MeiliSearchClient 方法包装为异步版本
    """

    def __init__(self, client: "MeiliSearchClient"):
        self._client = client

    async def search(self, query: str, index_name: str = "telegram", **kwargs: Any) -> dict:
        """异步搜索"""
        return await run_sync_in_thread(self._client.search, query, index_name, **kwargs)

    async def get_index_stats(self, index_name: str = "telegram") -> Any:
        """异步获取索引统计"""
        return await run_sync_in_thread(self._client.get_index_stats, index_name)

    async def add_documents(self, documents: list, index_name: str = "telegram") -> Any:
        """异步添加文档"""
        return await run_sync_in_thread(self._client.add_documents, documents, index_name)

    async def delete_documents(self, document_ids: list, index_name: str = "telegram") -> Any:
        """异步删除文档"""
        return await run_sync_in_thread(self._client.delete_documents, document_ids, index_name)

    async def get_all_stats(self) -> dict:
        """获取 MeiliSearch 全局统计（包含 databaseSize）"""
        return await run_sync_in_thread(self._client.client.get_all_stats)


async def get_meili_async(
    meili_client: "MeiliSearchClient" = Depends(get_meili_client),
) -> MeiliSearchAsync:
    """获取异步 MeiliSearch 包装器"""
    return MeiliSearchAsync(meili_client)


# ============ AuthStore 依赖 ============


async def get_auth_store(request: Request) -> "AuthStore":
    """获取 AuthStore"""
    app_state = await get_app_state(request)
    if app_state.auth_store is None:
        raise HTTPException(status_code=503, detail="AuthStore not initialized")
    return app_state.auth_store


async def get_config_store(request: Request) -> "ConfigStore":
    """获取 ConfigStore"""
    from tg_search.config.config_store import ConfigStore  # noqa: F401

    app_state = await get_app_state(request)
    if app_state.config_store is None:
        raise HTTPException(status_code=503, detail="ConfigStore not initialized")
    return app_state.config_store


async def get_config_policy_service(request: Request) -> "ConfigPolicyService":
    """获取 ConfigPolicyService。"""
    from tg_search.services.config_policy_service import ConfigPolicyService  # noqa: F401

    app_state = await get_app_state(request)
    if app_state.config_policy_service is None:
        raise HTTPException(status_code=503, detail="ConfigPolicyService not initialized")
    return app_state.config_policy_service


async def get_search_service(request: Request) -> "SearchService":
    """获取 SearchService。"""
    from tg_search.services.search_service import SearchService  # noqa: F401

    app_state = await get_app_state(request)
    if app_state.search_service is None:
        raise HTTPException(status_code=503, detail="SearchService not initialized")
    return app_state.search_service


async def get_observability_service(request: Request) -> "ObservabilityService":
    """获取 ObservabilityService。"""
    from tg_search.services.observability_service import ObservabilityService  # noqa: F401

    app_state = await get_app_state(request)

    # Primary path: service container wiring.
    if app_state.service_container is not None:
        service = getattr(app_state.service_container, "observability_service", None)
        if service is not None:
            return service

    # Fallback path: direct AppState reference.
    if app_state.observability_service is not None:
        return app_state.observability_service

    # Last-resort fallback for unit tests / partially initialized app state.
    if app_state.meili_client is not None:
        from tg_search.services.observability_service import ObservabilityService

        app_state.observability_service = ObservabilityService(
            app_state.meili_client,
            progress_registry=app_state.progress_registry,
        )
        return app_state.observability_service

    raise HTTPException(status_code=503, detail="ObservabilityService not initialized")


async def get_runtime_control_service(request: Request) -> "RuntimeControlService":
    """获取 RuntimeControlService。"""
    from tg_search.services.runtime_control_service import RuntimeControlService  # noqa: F401

    app_state = await get_app_state(request)
    runtime = getattr(app_state, "runtime_control_service", None)
    if runtime is not None:
        return runtime

    # 向后兼容：如果 AppState 尚未显式设置，尝试从容器读取。
    if app_state.service_container is not None:
        runtime = getattr(app_state.service_container, "runtime_control_service", None)
        if runtime is not None:
            app_state.runtime_control_service = runtime
            return runtime

    raise HTTPException(status_code=503, detail="RuntimeControlService not initialized")


def parse_bearer_token(authorization: Optional[str]) -> Optional[str]:
    """
    从 Authorization header 解析 Bearer token

    Args:
        authorization: Authorization header 值

    Returns:
        解析出的 token 或 None
    """
    if authorization is None:
        return None
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1]


def _unauthorized(error_code: str, message: str) -> HTTPException:
    """构造统一的 401 认证异常。"""
    return HTTPException(
        status_code=401,
        detail={
            "error_code": error_code,
            "message": message,
        },
    )


async def validate_auth_token(
    auth_store: "AuthStore",
    token: Optional[str],
) -> Optional["AuthToken"]:
    """
    统一 Bearer token 校验函数（供 HTTP / WebSocket 复用）。
    """
    if token is None or not token.strip():
        return None
    return await auth_store.validate_token(token.strip())


async def verify_bearer_token(
    request: Request,
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> "AuthToken":
    """
    验证 Bearer Token（仅限 Bearer Token，不接受 API Key）

    用于需要用户登录的端点（如 /auth/me, /auth/logout）

    Returns:
        AuthToken 对象

    Raises:
        HTTPException: 401 认证失败
    """

    token = parse_bearer_token(authorization)

    if token is None:
        raise _unauthorized(
            error_code="TOKEN_MISSING",
            message="Bearer token required. Please provide it in the 'Authorization' header.",
        )

    auth_store = await get_auth_store(request)
    auth_token = await validate_auth_token(auth_store, token)

    if auth_token is None:
        raise _unauthorized(
            error_code="TOKEN_INVALID",
            message="Invalid or expired token.",
        )

    return auth_token
