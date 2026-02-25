"""Search API routes backed by unified SearchService."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from fastapi import APIRouter, Depends, Query

from tg_search.api.deps import MeiliSearchAsync, get_meili_async, get_observability_service, get_search_service
from tg_search.api.models import (
    ApiResponse,
    ChatInfo,
    MessageModel,
    SearchResult,
    SearchStats,
    UserInfo,
)
from tg_search.services.contracts import SearchHit, SearchQuery
from tg_search.services.observability_service import ObservabilityService
from tg_search.services.search_service import SearchService


class ChatType(str, Enum):
    """聊天类型枚举。"""

    PRIVATE = "private"
    GROUP = "group"
    CHANNEL = "channel"


router = APIRouter()


def _to_message_model(hit: SearchHit) -> MessageModel:
    return MessageModel(
        id=hit.id,
        chat=ChatInfo(
            id=hit.chat.id,
            type=hit.chat.type,
            title=hit.chat.title,
            username=hit.chat.username,
        ),
        date=hit.date,
        text=hit.text,
        from_user=(
            UserInfo(id=hit.from_user.id, username=hit.from_user.username)
            if hit.from_user is not None
            else None
        ),
        reactions=hit.reactions,
        reactions_scores=hit.reactions_scores,
        text_len=hit.text_len,
        formatted=hit.formatted,
        formatted_text=hit.formatted_text,
    )


@router.get(
    "",
    response_model=ApiResponse[SearchResult],
    summary="搜索消息",
    description="在 MeiliSearch 中搜索 Telegram 消息",
)
async def search_messages(
    q: str = Query(..., min_length=1, max_length=500, description="搜索关键词"),
    chat_id: Optional[int] = Query(None, description="限定聊天 ID"),
    chat_type: Optional[ChatType] = Query(None, description="聊天类型: private/group/channel"),
    date_from: Optional[datetime] = Query(None, description="开始日期 (ISO8601)"),
    date_to: Optional[datetime] = Query(None, description="结束日期 (ISO8601)"),
    sender_username: Optional[str] = Query(None, description="发送者用户名"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    search_service: SearchService = Depends(get_search_service),
) -> ApiResponse[SearchResult]:
    page = await search_service.search(
        SearchQuery(
            q=q,
            chat_id=chat_id,
            chat_type=chat_type.value if chat_type is not None else None,
            date_from=date_from,
            date_to=date_to,
            sender_username=sender_username,
            limit=limit,
            offset=offset,
        )
    )

    search_result = SearchResult(
        hits=[_to_message_model(item) for item in page.hits],
        query=page.query,
        processing_time_ms=page.processing_time_ms,
        total_hits=page.total_hits,
        limit=page.limit,
        offset=page.offset,
    )
    return ApiResponse(data=search_result)


@router.get(
    "/stats",
    response_model=ApiResponse[SearchStats],
    summary="搜索统计",
    description="获取 MeiliSearch 索引统计信息",
)
async def get_search_stats(
    observability: ObservabilityService = Depends(get_observability_service),
) -> ApiResponse[SearchStats]:
    """获取搜索统计信息。"""
    snapshot = await observability.index_snapshot(source="api.search.stats")

    search_stats = SearchStats(
        total_documents=snapshot.total_documents,
        index_size_bytes=snapshot.database_size or 0,
        last_update=snapshot.last_update,
        is_indexing=snapshot.is_indexing,
        notes=snapshot.notes,
    )

    return ApiResponse(data=search_stats)
