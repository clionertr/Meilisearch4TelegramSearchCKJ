"""Unit tests for unified SearchService."""

from __future__ import annotations

from datetime import datetime

import pytest

from tg_search.services.contracts import SearchQuery
from tg_search.services.search_service import SearchService

pytestmark = [pytest.mark.unit]


class _FakeMeili:
    def __init__(self, result: dict):
        self.result = result
        self.calls: list[tuple[str, str, dict]] = []

    def search(self, query: str, index_name: str = "telegram", **kwargs):
        self.calls.append((query, index_name, kwargs))
        return self.result


@pytest.mark.asyncio
async def test_search_builds_unified_filter_and_pagination_params():
    fake = _FakeMeili(
        {
            "hits": [],
            "processingTimeMs": 3,
            "estimatedTotalHits": 0,
        }
    )
    service = SearchService(fake, cache_enabled=False)

    await service.search(
        SearchQuery(
            q="hello",
            chat_id=123,
            chat_type="group",
            date_from=datetime(2026, 1, 1, 12, 0, 0),
            date_to=datetime(2026, 1, 2, 12, 0, 0),
            limit=15,
            offset=5,
        )
    )

    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call[0] == "hello"
    assert call[1] == "telegram"
    assert call[2]["limit"] == 15
    assert call[2]["offset"] == 5
    assert "chat.id = 123" in call[2]["filter"]
    assert 'chat.type = "group"' in call[2]["filter"]
    assert 'date >=' in call[2]["filter"]
    assert 'date <=' in call[2]["filter"]


@pytest.mark.asyncio
async def test_search_parses_formatted_text_from_meili_hit():
    fake = _FakeMeili(
        {
            "hits": [
                {
                    "id": "100-1",
                    "chat": {"id": 100, "type": "group", "title": "g1"},
                    "date": "2026-01-01T00:00:00Z",
                    "text": "hello world",
                    "_formatted": {"text": "<mark>hello</mark> world"},
                    "from_user": {"id": 7, "username": "alice"},
                }
            ],
            "processingTimeMs": 9,
            "estimatedTotalHits": 1,
        }
    )
    service = SearchService(fake, cache_enabled=False)

    page = await service.search(SearchQuery(q="hello"))

    assert page.total_hits == 1
    assert len(page.hits) == 1
    assert page.hits[0].formatted_text == "<mark>hello</mark> world"
    assert page.hits[0].from_user is not None
    assert page.hits[0].from_user.username == "alice"


@pytest.mark.asyncio
async def test_search_for_presentation_uses_service_cache_for_multi_page_navigation():
    hits = []
    for i in range(8):
        hits.append(
            {
                "id": f"100-{i}",
                "chat": {"id": 100, "type": "group", "title": "g1"},
                "date": "2026-01-01T00:00:00Z",
                "text": f"hello {i}",
            }
        )
    fake = _FakeMeili(
        {
            "hits": hits,
            "processingTimeMs": 9,
            "estimatedTotalHits": len(hits),
        }
    )
    service = SearchService(fake, cache_enabled=True, cache_ttl_sec=3600, max_presentation_hits=20)
    query = SearchQuery(q="hello")

    page1 = await service.search_for_presentation(query, page=0, page_size=5)
    page2 = await service.search_for_presentation(query, page=1, page_size=5)

    assert [item.id for item in page1.hits] == ["100-0", "100-1", "100-2", "100-3", "100-4"]
    assert [item.id for item in page2.hits] == ["100-5", "100-6", "100-7"]
    assert len(fake.calls) == 1


def test_decode_legacy_callback_payload_preserves_underscore_query():
    service = SearchService(_FakeMeili({"hits": [], "processingTimeMs": 0, "estimatedTotalHits": 0}))

    query, page, page_size = service.decode_page_callback("page_foo_bar_2")

    assert query.q == "foo_bar"
    assert page == 2
    assert page_size > 0


def test_encode_callback_falls_back_to_short_token_when_payload_too_long():
    service = SearchService(
        _FakeMeili({"hits": [], "processingTimeMs": 0, "estimatedTotalHits": 0}),
        cache_ttl_sec=300,
    )
    long_query = "q_" + ("x" * 300)

    payload = service.encode_page_callback(SearchQuery(q=long_query), page=2, page_size=5)

    assert payload.startswith(b"pagek:")
    assert len(payload) <= 64
    decoded_query, page, page_size = service.decode_page_callback(payload)
    assert decoded_query.q == long_query
    assert page == 2
    assert page_size == 5

@pytest.mark.asyncio
async def test_search_builds_filter_with_sender_username():
    fake = _FakeMeili({"hits": [], "processingTimeMs": 3, "estimatedTotalHits": 0})
    service = SearchService(fake, cache_enabled=False)

    await service.search(
        SearchQuery(
            q="hello",
            sender_username='alice"bob',
        )
    )

    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert 'from_user.username = "alice\\"bob"' in call[2]["filter"]

def test_encode_callback_includes_sender_username():
    service = SearchService(_FakeMeili({"hits": [], "processingTimeMs": 0, "estimatedTotalHits": 0}))

    query = SearchQuery(q="hello", sender_username="alice")
    payload = service.encode_page_callback(query, page=1, page_size=5)

    decoded_query, page, page_size = service.decode_page_callback(payload)
    assert decoded_query.q == "hello"
    assert decoded_query.sender_username == "alice"
