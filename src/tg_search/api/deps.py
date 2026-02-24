"""
依赖注入模块

提供 FastAPI 依赖注入函数
"""

import asyncio
import os
from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING, Any, Literal, Optional

from fastapi import Depends, Header, HTTPException, Request
from fastapi.security import APIKeyHeader

from tg_search.config.settings import API_KEY, API_KEY_HEADER

if TYPE_CHECKING:
    from tg_search.api.auth_store import AuthStore, AuthToken
    from tg_search.api.state import AppState, ProgressRegistry
    from tg_search.config.config_store import ConfigStore
    from tg_search.core.meilisearch import MeiliSearchClient


# API Key 安全依赖
api_key_header = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)


async def verify_api_key(api_key: Optional[str] = Depends(api_key_header)) -> Optional[str]:
    """
    验证 API Key

    如果 API_KEY 未配置，则跳过验证（开发模式）
    如果 API_KEY 已配置但请求未提供或不匹配，返回 401

    Returns:
        验证通过的 API Key 或 None（无需认证时）

    Raises:
        HTTPException: 401 认证失败
    """
    # 如果未配置 API_KEY，跳过认证
    if API_KEY is None:
        return None

    # 检查请求是否提供了 API Key
    if api_key is None:
        raise HTTPException(
            status_code=401,
            detail={
                "error_code": "MISSING_API_KEY",
                "message": f"API Key required. Please provide it in the '{API_KEY_HEADER}' header.",
            },
        )

    # 验证 API Key
    if api_key != API_KEY:
        raise HTTPException(
            status_code=401,
            detail={
                "error_code": "INVALID_API_KEY",
                "message": "Invalid API Key.",
            },
        )

    return api_key


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
    from tg_search.api.auth_store import AuthToken

    token = parse_bearer_token(authorization)

    if token is None:
        raise HTTPException(
            status_code=401,
            detail={
                "error_code": "TOKEN_MISSING",
                "message": "Bearer token required. Please provide it in the 'Authorization' header.",
            },
        )

    auth_store = await get_auth_store(request)
    auth_token = await auth_store.validate_token(token)

    if auth_token is None:
        raise HTTPException(
            status_code=401,
            detail={
                "error_code": "TOKEN_INVALID",
                "message": "Invalid or expired token.",
            },
        )

    return auth_token


# ============ 双通道鉴权 ============


@dataclass
class AuthContext:
    """认证上下文"""

    auth_type: Literal["api_key", "bearer", "none"]
    user: Optional["AuthToken"] = None


async def verify_api_key_or_bearer_token(
    request: Request,
    api_key: Optional[str] = Depends(api_key_header),
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> AuthContext:
    """
    双通道鉴权：API Key 或 Bearer Token 任意通过

    优先级：
    1. 如果未配置 API_KEY，直接通过（开发模式）
    2. 如果提供了有效的 Bearer Token，通过
    3. 如果提供了有效的 API Key，通过
    4. 否则返回 401

    Returns:
        AuthContext 包含认证类型和用户信息

    Raises:
        HTTPException: 401 认证失败
    """
    # 开发模式：未配置 API_KEY 则跳过认证
    if API_KEY is None:
        return AuthContext(auth_type="none")

    # 尝试 Bearer Token 认证
    token = parse_bearer_token(authorization)
    if token is not None:
        auth_store = await get_auth_store(request)
        auth_token = await auth_store.validate_token(token)
        if auth_token is not None:
            return AuthContext(auth_type="bearer", user=auth_token)

    # 尝试 API Key 认证
    if api_key is not None and api_key == API_KEY:
        return AuthContext(auth_type="api_key")

    # 都失败了，返回 401
    raise HTTPException(
        status_code=401,
        detail={
            "error_code": "UNAUTHORIZED",
            "message": "Valid API Key or Bearer token required.",
        },
    )
