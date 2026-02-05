"""
依赖注入模块

提供 FastAPI 依赖注入函数
"""

from functools import partial
from typing import TYPE_CHECKING, Any, Optional

import anyio
from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyHeader

from tg_search.config.settings import API_KEY, API_KEY_HEADER

if TYPE_CHECKING:
    from tg_search.api.state import AppState, ProgressRegistry
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


def get_app_state(request: Request) -> "AppState":
    """获取应用状态"""
    return request.app.state.app_state


def get_meili_client(request: Request) -> "MeiliSearchClient":
    """获取 MeiliSearch 客户端"""
    app_state = get_app_state(request)
    if app_state.meili_client is None:
        raise HTTPException(status_code=503, detail="MeiliSearch client not initialized")
    return app_state.meili_client


def get_progress_registry(request: Request) -> "ProgressRegistry":
    """获取进度注册表"""
    app_state = get_app_state(request)
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
    return await anyio.to_thread.run_sync(partial(func, *args, **kwargs))


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


def get_meili_async(
    meili_client: "MeiliSearchClient" = Depends(get_meili_client),
) -> MeiliSearchAsync:
    """获取异步 MeiliSearch 包装器"""
    return MeiliSearchAsync(meili_client)
