"""
Dashboard API 路由 (P2-DB)

提供首页活动聚合与规则摘要接口：
  GET /dashboard/activity
  GET /dashboard/brief
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query

from tg_search.api.deps import MeiliSearchAsync, get_meili_async
from tg_search.api.models import (
    ApiResponse,
    DashboardActivityData,
    DashboardActivityItem,
    DashboardBriefData,
)

router = APIRouter()

_SAMPLE_SIZE = 500
_MAX_KEYWORDS = 3
_DEFAULT_MIN_MESSAGES = 20
_TEMPLATE_ID = "brief.v1"
_NO_ENOUGH_DATA = "NO_ENOUGH_DATA"
_TOKEN_RE = re.compile(r"[A-Za-z0-9_]{2,}")
_STOP_WORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "have",
    "your",
    "you",
    "are",
    "was",
    "were",
    "will",
    "just",
    "into",
    "about",
    "http",
    "https",
}


def _to_utc_datetime(value: Any) -> datetime | None:
    """将输入转为 UTC datetime。"""
    if not value:
        return None

    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _extract_keywords(text: str, max_count: int = _MAX_KEYWORDS) -> list[str]:
    """从文本中提取 top keywords（简单规则版，deterministic）。"""
    if not text:
        return []

    counter: Counter[str] = Counter()
    for token in _TOKEN_RE.findall(text.lower()):
        if token in _STOP_WORDS:
            continue
        counter[token] += 1
    return [word for word, _ in counter.most_common(max_count)]


async def _load_window_hits(
    meili: MeiliSearchAsync,
    window_hours: int,
) -> tuple[list[dict[str, Any]], int, bool]:
    """
    拉取时间窗口内样本消息。

    返回: (hits, source_count, sampled)
    """
    now_utc = datetime.now(timezone.utc)
    start_time = now_utc - timedelta(hours=window_hours)
    filter_str = f'date >= "{start_time.isoformat().replace("+00:00", "Z")}"'

    result = await meili.search(
        "",
        limit=_SAMPLE_SIZE,
        offset=0,
        filter=filter_str,
        sort=["date:desc"],
        attributesToRetrieve=["id", "chat", "date", "text"],
    )

    hits_raw = result.get("hits", [])
    hits = hits_raw if isinstance(hits_raw, list) else []
    estimated_total = result.get("estimatedTotalHits", len(hits))
    try:
        source_count = max(int(estimated_total), len(hits))
    except (TypeError, ValueError):
        source_count = len(hits)

    sampled = source_count > len(hits)
    return hits, source_count, sampled


def _aggregate_activity_items(hits: list[dict[str, Any]]) -> list[DashboardActivityItem]:
    """按 chat 维度聚合 activity。"""
    grouped: dict[int, dict[str, Any]] = {}

    for hit in hits:
        chat = hit.get("chat") if isinstance(hit, dict) else {}
        if not isinstance(chat, dict):
            chat = {}

        raw_chat_id = chat.get("id")
        try:
            chat_id = int(raw_chat_id)
        except (TypeError, ValueError):
            continue

        dt = _to_utc_datetime(hit.get("date")) or datetime.now(timezone.utc)
        text = str(hit.get("text") or "").strip()
        if chat_id not in grouped:
            grouped[chat_id] = {
                "chat_title": str(chat.get("title") or chat.get("username") or f"chat_{chat_id}"),
                "chat_type": str(chat.get("type") or "unknown"),
                "message_count": 0,
                "latest_message_time": dt,
                "latest_text": text,
                "keywords": Counter(),
            }

        bucket = grouped[chat_id]
        bucket["message_count"] += 1
        if dt >= bucket["latest_message_time"]:
            bucket["latest_message_time"] = dt
            if text:
                bucket["latest_text"] = text

        for token in _extract_keywords(text, max_count=30):
            bucket["keywords"][token] += 1

    items: list[DashboardActivityItem] = []
    for chat_id, bucket in grouped.items():
        top_keywords = [word for word, _ in bucket["keywords"].most_common(_MAX_KEYWORDS)]
        sample_message = str(bucket["latest_text"] or "")
        if len(sample_message) > 240:
            sample_message = sample_message[:240].rstrip() + "..."

        items.append(
            DashboardActivityItem(
                chat_id=chat_id,
                chat_title=bucket["chat_title"],
                chat_type=bucket["chat_type"],
                message_count=int(bucket["message_count"]),
                latest_message_time=bucket["latest_message_time"],
                top_keywords=top_keywords,
                sample_message=sample_message,
            )
        )

    items.sort(
        key=lambda x: (
            -x.message_count,
            -x.latest_message_time.timestamp(),
            x.chat_id,
        )
    )
    return items


@router.get(
    "/activity",
    response_model=ApiResponse[DashboardActivityData],
    summary="Dashboard 活动聚合",
    description="窗口拉取 + API 层内存分组聚合（不依赖 Meili 聚合能力）",
)
async def get_dashboard_activity(
    window_hours: int = Query(24, ge=1, le=168, description="统计窗口（小时）"),
    limit: int = Query(20, ge=1, le=100, description="返回聊天数量"),
    offset: int = Query(0, ge=0, description="聊天偏移"),
    meili: MeiliSearchAsync = Depends(get_meili_async),
) -> ApiResponse[DashboardActivityData]:
    """
    获取 Dashboard 活动聚合列表。
    """
    hits, source_count, sampled = await _load_window_hits(meili, window_hours=window_hours)
    all_items = _aggregate_activity_items(hits)
    items = all_items[offset : offset + limit]

    data = DashboardActivityData(
        items=items,
        total=len(all_items),
        sampled=sampled,
        sample_size=min(source_count, _SAMPLE_SIZE),
    )
    return ApiResponse(data=data)


@router.get(
    "/brief",
    response_model=ApiResponse[DashboardBriefData],
    summary="Dashboard 规则摘要",
    description="规则模板 brief.v1，低于最小消息量返回 NO_ENOUGH_DATA",
)
async def get_dashboard_brief(
    window_hours: int = Query(24, ge=1, le=168, description="统计窗口（小时）"),
    min_messages: int = Query(_DEFAULT_MIN_MESSAGES, ge=1, le=1_000_000, description="最小消息阈值"),
    meili: MeiliSearchAsync = Depends(get_meili_async),
) -> ApiResponse[DashboardBriefData]:
    """
    获取 Dashboard 规则摘要。
    """
    hits, source_count, sampled = await _load_window_hits(meili, window_hours=window_hours)
    activity_items = _aggregate_activity_items(hits)

    if source_count < min_messages or not activity_items:
        return ApiResponse(
            data=DashboardBriefData(
                summary="",
                template_id=_TEMPLATE_ID,
                source_count=source_count,
                reason=_NO_ENOUGH_DATA,
                sampled=sampled,
                sample_size=min(source_count, _SAMPLE_SIZE),
            )
        )

    top_chat = activity_items[0]
    summary = (
        f"过去{window_hours}小时共新增 {source_count} 条消息，"
        f"最活跃会话是 {top_chat.chat_title}（{top_chat.message_count} 条）。"
    )
    return ApiResponse(
        data=DashboardBriefData(
            summary=summary,
            template_id=_TEMPLATE_ID,
            source_count=source_count,
            reason=None,
            sampled=sampled,
            sample_size=min(source_count, _SAMPLE_SIZE),
        )
    )
