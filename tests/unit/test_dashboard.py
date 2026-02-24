"""
Dashboard 路由核心逻辑单元测试。
"""

from datetime import datetime, timezone

import pytest

from tg_search.api.routes.dashboard import (
    _aggregate_activity_items,
    _extract_keywords,
    _to_utc_datetime,
)

pytestmark = [pytest.mark.unit]


def test_to_utc_datetime_parses_iso_z():
    dt = _to_utc_datetime("2026-02-24T10:20:30Z")
    assert dt is not None
    assert dt.tzinfo is not None
    assert dt.tzinfo == timezone.utc
    assert dt.year == 2026
    assert dt.hour == 10


def test_extract_keywords_filters_stopwords_and_limits_top3():
    text = "the dashboard api api telegram telegram telegram meilisearch and for"
    keywords = _extract_keywords(text)
    assert keywords == ["telegram", "api", "dashboard"]


def test_aggregate_activity_items_groups_by_chat_and_sorts():
    hits = [
        {
            "chat": {"id": -1001, "title": "A Group", "type": "group"},
            "date": "2026-02-24T10:00:00Z",
            "text": "telegram api update",
        },
        {
            "chat": {"id": -1002, "title": "B Group", "type": "group"},
            "date": "2026-02-24T11:00:00Z",
            "text": "telegram dashboard",
        },
        {
            "chat": {"id": -1001, "title": "A Group", "type": "group"},
            "date": "2026-02-24T12:00:00Z",
            "text": "meilisearch dashboard api",
        },
    ]

    items = _aggregate_activity_items(hits)
    assert len(items) == 2

    # -1001 有 2 条消息，应排在首位
    first = items[0]
    assert first.chat_id == -1001
    assert first.message_count == 2
    assert first.latest_message_time == datetime(2026, 2, 24, 12, 0, 0, tzinfo=timezone.utc)
    assert first.top_keywords[0] == "api"
    assert "dashboard" in first.sample_message
