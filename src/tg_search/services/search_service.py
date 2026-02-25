"""Unified SearchService shared by API and Bot presentation layers."""

from __future__ import annotations

import asyncio
import base64
import json
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from tg_search.config.settings import (
    CACHE_EXPIRE_SECONDS,
    RESULTS_PER_PAGE,
    SEARCH_CACHE,
    SEARCH_CALLBACK_TOKEN_TTL_SEC,
    SEARCH_PRESENTATION_MAX_HITS,
)
from tg_search.core.logger import setup_logger
from tg_search.core.meilisearch import MeiliSearchClient
from tg_search.services.contracts import DomainError, SearchChat, SearchHit, SearchPage, SearchQuery, SearchUser

logger = setup_logger()


@dataclass(slots=True)
class _PresentationCacheEntry:
    page: SearchPage
    expires_at: float

    def is_expired(self) -> bool:
        return time.monotonic() >= self.expires_at


@dataclass(slots=True)
class _CallbackQueryEntry:
    query: SearchQuery
    expires_at: float

    def is_expired(self) -> bool:
        return time.monotonic() >= self.expires_at


class SearchService:
    """Single source of truth for search filters, parsing, pagination and cache."""

    def __init__(
        self,
        meili: MeiliSearchClient,
        *,
        cache_enabled: bool = SEARCH_CACHE,
        cache_ttl_sec: int = CACHE_EXPIRE_SECONDS,
        max_presentation_hits: int = SEARCH_PRESENTATION_MAX_HITS,
        callback_token_ttl_sec: int = SEARCH_CALLBACK_TOKEN_TTL_SEC,
    ) -> None:
        self._meili = meili
        self._cache_enabled = cache_enabled
        self._cache_ttl_sec = max(int(cache_ttl_sec), 1)
        self._max_presentation_hits = max(int(max_presentation_hits), RESULTS_PER_PAGE)
        self._callback_token_ttl_sec = max(int(callback_token_ttl_sec), 1)
        self._presentation_cache: dict[str, _PresentationCacheEntry] = {}
        self._callback_query_cache: dict[str, _CallbackQueryEntry] = {}
        self._cache_lock = asyncio.Lock()
        logger.info(
            "[SearchService] initialized cache_enabled=%s cache_ttl_sec=%d max_presentation_hits=%d callback_token_ttl_sec=%d",
            self._cache_enabled,
            self._cache_ttl_sec,
            self._max_presentation_hits,
            self._callback_token_ttl_sec,
        )

    def clear_cache(self) -> None:
        presentation_entries = len(self._presentation_cache)
        callback_entries = len(self._callback_query_cache)
        self._presentation_cache.clear()
        self._callback_query_cache.clear()
        logger.info(
            "[SearchService] clear_cache presentation_entries=%d callback_entries=%d",
            presentation_entries,
            callback_entries,
        )

    def _build_filter(self, query: SearchQuery) -> str | None:
        conditions: list[str] = []
        if query.chat_id is not None:
            conditions.append(f"chat.id = {query.chat_id}")
        if query.chat_type is not None:
            conditions.append(f'chat.type = "{query.chat_type}"')
        if query.date_from is not None:
            conditions.append(f'date >= "{query.date_from.isoformat()}"')
        if query.date_to is not None:
            conditions.append(f'date <= "{query.date_to.isoformat()}"')
        if query.sender_username is not None:
            safe = query.sender_username.replace('"', '\\"')
            conditions.append(f'from_user.username = "{safe}"')

        return " AND ".join(conditions) if conditions else None

    @staticmethod
    def _parse_hit(hit: dict[str, Any]) -> SearchHit:
        chat_data = hit.get("chat") or {}
        from_user_data = hit.get("from_user")
        date_str = hit.get("date", "")
        try:
            date_value = (
                datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
                if date_str
                else datetime.utcnow()
            )
        except (ValueError, TypeError):
            date_value = datetime.utcnow()

        formatted = hit.get("_formatted")
        formatted_text = None
        if isinstance(formatted, dict):
            formatted_text = formatted.get("text")

        from_user = None
        if isinstance(from_user_data, dict):
            from_user = SearchUser(
                id=from_user_data.get("id", 0),
                username=from_user_data.get("username"),
            )

        return SearchHit(
            id=hit.get("id", ""),
            chat=SearchChat(
                id=chat_data.get("id", 0),
                type=chat_data.get("type", "unknown"),
                title=chat_data.get("title"),
                username=chat_data.get("username"),
            ),
            date=date_value,
            text=hit.get("text", ""),
            from_user=from_user,
            reactions=hit.get("reactions") or {},
            reactions_scores=hit.get("reactions_scores") or 0.0,
            text_len=hit.get("text_len") or len(hit.get("text", "")),
            formatted=formatted if isinstance(formatted, dict) else None,
            formatted_text=formatted_text,
        )

    async def search(self, query: SearchQuery) -> SearchPage:
        started_at = time.monotonic()
        search_params: dict[str, Any] = {
            "limit": query.limit,
            "offset": query.offset,
            "attributesToHighlight": ["text"],
            "highlightPreTag": "<mark>",
            "highlightPostTag": "</mark>",
        }

        filter_str = self._build_filter(query)
        if filter_str:
            search_params["filter"] = filter_str

        result = await asyncio.to_thread(
            self._meili.search,
            query.q,
            query.index_name,
            **search_params,
        )
        hits = [self._parse_hit(hit) for hit in result.get("hits", [])]
        page = SearchPage(
            hits=hits,
            query=query.q,
            processing_time_ms=int(result.get("processingTimeMs", 0)),
            total_hits=int(result.get("estimatedTotalHits", len(hits))),
            limit=query.limit,
            offset=query.offset,
        )
        duration_ms = (time.monotonic() - started_at) * 1000
        logger.info(
            "[SearchService] search q_len=%d index=%s filter_enabled=%s limit=%d offset=%d hits=%d total_hits=%d duration_ms=%.1f meili_processing_ms=%d",
            len(query.q),
            query.index_name,
            filter_str is not None,
            query.limit,
            query.offset,
            len(page.hits),
            page.total_hits,
            duration_ms,
            page.processing_time_ms,
        )
        return page

    @staticmethod
    def _presentation_cache_key(query: SearchQuery) -> str:
        payload = {
            "q": query.q,
            "chat_id": query.chat_id,
            "chat_type": query.chat_type,
            "date_from": query.date_from.isoformat() if query.date_from else None,
            "date_to": query.date_to.isoformat() if query.date_to else None,
            "sender_username": query.sender_username,
            "index_name": query.index_name,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    async def _get_cached_or_load_presentation(self, query: SearchQuery) -> SearchPage:
        key = self._presentation_cache_key(query)
        key_hash = hash(key)
        if self._cache_enabled:
            async with self._cache_lock:
                entry = self._presentation_cache.get(key)
                if entry is not None and not entry.is_expired():
                    logger.info("[SearchService] presentation_cache_hit key_hash=%d", key_hash)
                    return entry.page
                if entry is not None and entry.is_expired():
                    self._presentation_cache.pop(key, None)
                    logger.info("[SearchService] presentation_cache_expired key_hash=%d", key_hash)

        logger.info("[SearchService] presentation_cache_miss key_hash=%d", key_hash)

        loaded_page = await self.search(
            query.model_copy(
                update={
                    "limit": self._max_presentation_hits,
                    "offset": 0,
                }
            )
        )

        if self._cache_enabled:
            async with self._cache_lock:
                self._presentation_cache[key] = _PresentationCacheEntry(
                    page=loaded_page,
                    expires_at=time.monotonic() + self._cache_ttl_sec,
                )
        return loaded_page

    async def search_for_presentation(
        self,
        query: SearchQuery,
        page: int,
        page_size: int = RESULTS_PER_PAGE,
    ) -> SearchPage:
        if page < 0:
            raise DomainError("search_invalid_page", "page must be >= 0")
        if page_size <= 0:
            raise DomainError("search_invalid_page_size", "page_size must be > 0")

        source_page = await self._get_cached_or_load_presentation(query)
        start = page * page_size
        end = start + page_size
        hits_window = source_page.hits[: self._max_presentation_hits]
        visible_total = min(source_page.total_hits, len(hits_window))

        return SearchPage(
            hits=hits_window[start:end],
            query=query.q,
            processing_time_ms=source_page.processing_time_ms,
            total_hits=visible_total,
            limit=page_size,
            offset=start,
        )

    def encode_page_callback(self, query: SearchQuery, page: int, page_size: int = RESULTS_PER_PAGE) -> bytes:
        self._cleanup_callback_query_cache()
        payload: dict[str, Any] = {
            "q": query.q,
            "p": page,
            "s": page_size,
            "index": query.index_name,
        }
        if query.chat_id is not None:
            payload["cid"] = query.chat_id
        if query.chat_type is not None:
            payload["ct"] = query.chat_type
        if query.date_from is not None:
            payload["df"] = query.date_from.isoformat()
        if query.date_to is not None:
            payload["dt"] = query.date_to.isoformat()
        if query.sender_username is not None:
            payload["su"] = query.sender_username

        packed = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        token = base64.urlsafe_b64encode(packed).decode("ascii").rstrip("=")
        encoded = f"page:{token}".encode("utf-8")
        if len(encoded) <= 64:
            logger.info(
                "[SearchService] encode_callback mode=inline page=%d page_size=%d payload_bytes=%d",
                page,
                page_size,
                len(encoded),
            )
            return encoded

        short_token = uuid.uuid4().hex[:12]
        self._callback_query_cache[short_token] = _CallbackQueryEntry(
            query=query.model_copy(
                update={
                    "limit": page_size,
                    "offset": page * page_size,
                }
            ),
            expires_at=time.monotonic() + self._callback_token_ttl_sec,
        )
        logger.warning(
            "[SearchService] encode_callback mode=token_fallback page=%d page_size=%d inline_payload_bytes=%d token=%s",
            page,
            page_size,
            len(encoded),
            short_token,
        )
        return f"pagek:{short_token}:{page}:{page_size}".encode("utf-8")

    def decode_page_callback(self, raw_data: str | bytes) -> tuple[SearchQuery, int, int]:
        self._cleanup_callback_query_cache()
        raw = raw_data.decode("utf-8") if isinstance(raw_data, bytes) else raw_data
        if raw.startswith("pagek:"):
            try:
                _, token, page_text, page_size_text = raw.split(":", 3)
            except ValueError as exc:
                raise DomainError("search_pagination_invalid", "invalid pagination payload") from exc
            entry = self._callback_query_cache.get(token)
            if entry is None or entry.is_expired():
                raise DomainError("search_pagination_invalid", "pagination token expired")
            try:
                page = int(page_text)
                page_size = int(page_size_text)
            except ValueError as exc:
                raise DomainError("search_pagination_invalid", "invalid page number") from exc
            query = entry.query.model_copy(update={"limit": page_size, "offset": page * page_size})
            logger.info(
                "[SearchService] decode_callback mode=token page=%d page_size=%d token=%s",
                page,
                page_size,
                token,
            )
            return query, page, page_size

        if raw.startswith("page:"):
            token = raw[5:]
            padding = "=" * ((4 - len(token) % 4) % 4)
            try:
                payload = json.loads(base64.urlsafe_b64decode(token + padding).decode("utf-8"))
                page = int(payload["p"])
                page_size = int(payload.get("s", RESULTS_PER_PAGE))
                query = SearchQuery(
                    q=str(payload["q"]),
                    chat_id=payload.get("cid"),
                    chat_type=payload.get("ct"),
                    date_from=datetime.fromisoformat(payload["df"]) if payload.get("df") else None,
                    date_to=datetime.fromisoformat(payload["dt"]) if payload.get("dt") else None,
                    sender_username=payload.get("su"),
                    index_name=str(payload.get("index", "telegram")),
                    limit=page_size,
                    offset=page * page_size,
                )
                logger.info(
                    "[SearchService] decode_callback mode=inline page=%d page_size=%d",
                    page,
                    page_size,
                )
                return query, page, page_size
            except Exception as exc:  # pragma: no cover - defensive branch
                raise DomainError("search_pagination_invalid", "invalid pagination payload", detail=str(exc)) from exc

        # Backward compatibility: legacy format `page_{query}_{page}`.
        if raw.startswith("page_"):
            body = raw[len("page_") :]
            query_text, sep, page_text = body.rpartition("_")
            if not sep:
                raise DomainError("search_pagination_invalid", "invalid legacy pagination payload")
            try:
                page = int(page_text)
            except ValueError as exc:
                raise DomainError("search_pagination_invalid", "invalid page number", detail=page_text) from exc
            page_size = RESULTS_PER_PAGE
            query = SearchQuery(
                q=query_text,
                limit=page_size,
                offset=page * page_size,
            )
            logger.info(
                "[SearchService] decode_callback mode=legacy page=%d page_size=%d",
                page,
                page_size,
            )
            return query, page, page_size

        raise DomainError("search_pagination_invalid", "unsupported pagination payload")

    def _cleanup_callback_query_cache(self) -> None:
        expired_tokens = [token for token, entry in self._callback_query_cache.items() if entry.is_expired()]
        for token in expired_tokens:
            self._callback_query_cache.pop(token, None)
        if expired_tokens:
            logger.info("[SearchService] cleanup_callback_tokens removed=%d", len(expired_tokens))
