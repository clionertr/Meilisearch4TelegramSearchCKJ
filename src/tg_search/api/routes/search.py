"""
搜索 API 路由

提供消息搜索和统计接口
"""

import re
from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from tg_search.api.deps import MeiliSearchAsync, get_meili_async
from tg_search.api.models import (
    ApiResponse,
    ChatInfo,
    MessageModel,
    SearchResult,
    SearchStats,
    UserInfo,
)


class ChatType(str, Enum):
    """聊天类型枚举"""

    PRIVATE = "private"
    GROUP = "group"
    CHANNEL = "channel"


class MeiliFilterBuilder:
    """
    MeiliSearch 过滤器安全构建器

    防止 filter 注入攻击，只允许预定义的字段和安全的值
    """

    # 允许的过滤字段白名单
    ALLOWED_FIELDS = {"chat.id", "chat.type", "date", "from_user.id"}

    # chat.type 允许的值
    ALLOWED_CHAT_TYPES = {"private", "group", "channel"}

    def __init__(self):
        self._conditions: List[str] = []

    def add_chat_id(self, chat_id: int) -> "MeiliFilterBuilder":
        """添加聊天 ID 过滤"""
        # 整数类型已通过 Pydantic 验证，直接使用
        self._conditions.append(f"chat.id = {chat_id}")
        return self

    def add_chat_type(self, chat_type: ChatType) -> "MeiliFilterBuilder":
        """添加聊天类型过滤"""
        # 使用枚举保证值安全
        self._conditions.append(f'chat.type = "{chat_type.value}"')
        return self

    def add_date_from(self, date_from: datetime) -> "MeiliFilterBuilder":
        """添加开始日期过滤"""
        # datetime 已通过 Pydantic 验证，格式化为 ISO8601
        iso_date = date_from.isoformat()
        self._conditions.append(f'date >= "{iso_date}"')
        return self

    def add_date_to(self, date_to: datetime) -> "MeiliFilterBuilder":
        """添加结束日期过滤"""
        iso_date = date_to.isoformat()
        self._conditions.append(f'date <= "{iso_date}"')
        return self

    def build(self) -> Optional[str]:
        """构建最终的过滤字符串"""
        if not self._conditions:
            return None
        return " AND ".join(self._conditions)


router = APIRouter()


def _parse_message(hit: dict) -> MessageModel:
    """将 MeiliSearch 返回的 hit 转换为 MessageModel"""
    chat_data = hit.get("chat", {})
    from_user_data = hit.get("from_user")

    chat = ChatInfo(
        id=chat_data.get("id", 0),
        type=chat_data.get("type", "unknown"),
        title=chat_data.get("title"),
        username=chat_data.get("username"),
    )

    from_user = None
    if from_user_data:
        from_user = UserInfo(
            id=from_user_data.get("id", 0),
            username=from_user_data.get("username"),
        )

    # 解析日期
    date_str = hit.get("date", "")
    try:
        date = datetime.fromisoformat(date_str.replace("Z", "+00:00")) if date_str else datetime.utcnow()
    except (ValueError, AttributeError):
        date = datetime.utcnow()

    return MessageModel(
        id=hit.get("id", ""),
        chat=chat,
        date=date,
        text=hit.get("text", ""),
        from_user=from_user,
        reactions=hit.get("reactions") or {},
        reactions_scores=hit.get("reactions_scores") or 0.0,
        text_len=hit.get("text_len") or len(hit.get("text", "")),
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
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    meili: MeiliSearchAsync = Depends(get_meili_async),
) -> ApiResponse[SearchResult]:
    """
    搜索消息

    支持按聊天 ID、聊天类型、日期范围过滤

    日期参数格式：
    - ISO8601 格式，如 2024-01-15T10:30:00
    - 带时区，如 2024-01-15T10:30:00+08:00
    - 仅日期，如 2024-01-15（会解析为当天 00:00:00）

    聊天类型：
    - private: 私聊
    - group: 群组
    - channel: 频道
    """
    # 使用安全的过滤器构建器（防止注入攻击）
    builder = MeiliFilterBuilder()

    if chat_id is not None:
        builder.add_chat_id(chat_id)

    if chat_type is not None:
        builder.add_chat_type(chat_type)

    if date_from is not None:
        builder.add_date_from(date_from)

    if date_to is not None:
        builder.add_date_to(date_to)

    filter_str = builder.build()

    # 执行搜索
    search_params = {
        "limit": limit,
        "offset": offset,
        "attributesToHighlight": ["text"],
        "highlightPreTag": "<mark>",
        "highlightPostTag": "</mark>",
    }

    if filter_str:
        search_params["filter"] = filter_str

    result = await meili.search(q, **search_params)

    # 解析结果
    hits = [_parse_message(hit) for hit in result.get("hits", [])]

    search_result = SearchResult(
        hits=hits,
        query=q,
        processing_time_ms=result.get("processingTimeMs", 0),
        total_hits=result.get("estimatedTotalHits", len(hits)),
        limit=limit,
        offset=offset,
    )

    return ApiResponse(data=search_result)


@router.get(
    "/stats",
    response_model=ApiResponse[SearchStats],
    summary="搜索统计",
    description="获取 MeiliSearch 索引统计信息",
)
async def get_search_stats(
    meili: MeiliSearchAsync = Depends(get_meili_async),
) -> ApiResponse[SearchStats]:
    """获取搜索统计信息"""
    stats = await meili.get_index_stats()

    search_stats = SearchStats(
        total_documents=stats.number_of_documents,
        index_size_bytes=0,  # IndexStats 可能没有此属性
        is_indexing=stats.is_indexing,
    )

    return ApiResponse(data=search_stats)
