"""Service-layer contracts for runtime policies, search, and observability snapshots."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class DomainError(Exception):
    """Structured domain error used by service layer."""

    def __init__(self, code: str, message: str, detail: str | None = None) -> None:
        self.code = code
        self.message = message
        self.detail = detail
        super().__init__(message if detail is None else f"{message}: {detail}")


class PolicyConfig(BaseModel):
    """Canonical runtime policy snapshot."""

    white_list: list[int] = Field(default_factory=list)
    black_list: list[int] = Field(default_factory=list)
    version: int
    updated_at: str
    source: Literal["config_store", "bootstrap_defaults"] = "config_store"


class PolicyChangeResult(BaseModel):
    """Mutation result for whitelist/blacklist updates."""

    updated_list: list[int] = Field(default_factory=list)
    added: list[int] = Field(default_factory=list)
    removed: list[int] = Field(default_factory=list)
    version: int


class SearchQuery(BaseModel):
    """Canonical search input used by both API and Bot presentation layers."""

    q: str = Field(..., min_length=1, max_length=500)
    chat_id: Optional[int] = None
    chat_type: Optional[Literal["private", "group", "channel"]] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    index_name: str = "telegram"


class SearchChat(BaseModel):
    """Chat metadata in a normalized search hit."""

    id: int
    type: str
    title: Optional[str] = None
    username: Optional[str] = None


class SearchUser(BaseModel):
    """Sender metadata in a normalized search hit."""

    id: int
    username: Optional[str] = None


class SearchHit(BaseModel):
    """Normalized search hit entity."""

    id: str
    chat: SearchChat
    date: datetime
    text: str
    from_user: Optional[SearchUser] = None
    reactions: dict[str, int] = Field(default_factory=dict)
    reactions_scores: float = 0.0
    text_len: int = 0
    formatted: Optional[dict[str, Any]] = None
    formatted_text: Optional[str] = None


class SearchPage(BaseModel):
    """Paginated search page result."""

    hits: list[SearchHit] = Field(default_factory=list)
    query: str
    processing_time_ms: int
    total_hits: int
    limit: int
    offset: int

class IndexSnapshot(BaseModel):
    """Canonical Meili index snapshot."""

    total_documents: int = 0
    is_indexing: bool = False
    database_size: int | None = None
    last_update: datetime | None = None
    meili_connected: bool = False
    notes: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class SystemSnapshot(BaseModel):
    """Runtime/system snapshot used by API `/status` and Bot `/ping`."""

    uptime_seconds: float = 0.0
    meili_connected: bool = False
    telegram_connected: bool = False
    bot_running: bool = False
    indexed_messages: int = 0
    memory_usage_mb: float = 0.0
    notes: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class StorageSnapshot(BaseModel):
    """Storage snapshot for `/storage/stats`."""

    total_bytes: int | None = None
    index_bytes: int | None = None
    media_supported: bool = False
    cache_supported: bool = False
    notes: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class ProgressSnapshot(BaseModel):
    """Progress snapshot for `/status/progress` and push-event consistency checks."""

    all_progress: dict[str, dict[str, Any]] = Field(default_factory=dict)
    active_count: int = 0
    notes: list[str] = Field(default_factory=list)
