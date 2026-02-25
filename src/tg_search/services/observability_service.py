"""Unified observability snapshots shared by API routes and Bot `/ping`."""

from __future__ import annotations

import asyncio
import time
import tracemalloc
import uuid
from datetime import datetime, timezone
from typing import Any, Protocol

from tg_search.core.logger import setup_logger
from tg_search.core.meilisearch import MeiliSearchClient
from tg_search.services.contracts import IndexSnapshot, ProgressSnapshot, StorageSnapshot, SystemSnapshot

logger = setup_logger()


class ProgressRegistryLike(Protocol):
    """Minimal progress registry contract used by observability snapshots."""

    def get_all_progress(self) -> dict[int, Any]:
        ...


class ObservabilityService:
    """Collect health/storage/progress snapshots with partial-failure degradation."""

    def __init__(
        self,
        meili_client: MeiliSearchClient,
        *,
        index_name: str = "telegram",
        progress_registry: ProgressRegistryLike | None = None,
        snapshot_timeout_sec: float = 0.8,
        slow_snapshot_warn_ms: int = 800,
    ) -> None:
        self._meili = meili_client
        self._index_name = index_name
        self._progress_registry = progress_registry
        self._snapshot_timeout_sec = max(snapshot_timeout_sec, 0.1)
        self._slow_snapshot_warn_ms = max(int(slow_snapshot_warn_ms), 1)

    def attach_progress_registry(self, progress_registry: ProgressRegistryLike) -> None:
        """Bind/replace runtime progress registry provider."""
        self._progress_registry = progress_registry

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
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

    @staticmethod
    def _safe_int(value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _extract_index_payload(all_stats: dict[str, Any], index_name: str) -> dict[str, Any]:
        indexes = all_stats.get("indexes")
        if not isinstance(indexes, dict):
            return {}

        payload = indexes.get(index_name)
        if isinstance(payload, dict):
            return payload
        return {}

    async def _run_meili_call(self, label: str, func: Any, *args: Any) -> tuple[Any | None, str | None]:
        try:
            result = await asyncio.wait_for(asyncio.to_thread(func, *args), timeout=self._snapshot_timeout_sec)
            return result, None
        except asyncio.TimeoutError:
            return None, f"{label} timeout"
        except Exception as exc:  # pragma: no cover - defensive guard
            return None, f"{label} failed: {type(exc).__name__}: {exc}"

    def _read_memory_usage_mb(self) -> tuple[float, list[str]]:
        memory_usage_mb = 0.0
        notes: list[str] = []

        if tracemalloc.is_tracing():
            current, _peak = tracemalloc.get_traced_memory()
            memory_usage_mb = current / (1024 * 1024)
            return round(memory_usage_mb, 2), notes

        try:
            import resource

            usage = resource.getrusage(resource.RUSAGE_SELF)
            memory_usage_mb = usage.ru_maxrss / 1024
        except (ImportError, AttributeError, OSError):
            notes.append("memory usage metric unavailable on this platform")

        return round(memory_usage_mb, 2), notes

    def _log_snapshot(
        self,
        *,
        trace_id: str,
        source: str,
        snapshot_type: str,
        started_at: float,
        notes: list[str],
        errors: list[str],
    ) -> None:
        duration_ms = (time.monotonic() - started_at) * 1000
        is_slow = duration_ms > self._slow_snapshot_warn_ms
        has_errors = len(errors) > 0
        log_method = logger.warning if (is_slow or has_errors) else logger.info
        log_method(
            "[ObservabilityService] trace_id=%s source=%s snapshot_type=%s duration_ms=%.1f notes=%d errors=%d",
            trace_id,
            source,
            snapshot_type,
            duration_ms,
            len(notes),
            len(errors),
        )

    async def index_snapshot(self, *, source: str = "unknown") -> IndexSnapshot:
        """Collect canonical index-level snapshot with partial failure fallback."""
        started_at = time.monotonic()
        trace_id = uuid.uuid4().hex[:8]

        notes: list[str] = []
        errors: list[str] = []

        index_task = self._run_meili_call("get_index_stats", self._meili.get_index_stats, self._index_name)

        async def _missing_all_stats() -> tuple[None, str]:
            return None, "get_all_stats unavailable on Meili client"

        meili_raw_client = getattr(self._meili, "client", None)
        all_stats_fn = getattr(meili_raw_client, "get_all_stats", None)
        all_task = self._run_meili_call("get_all_stats", all_stats_fn) if callable(all_stats_fn) else _missing_all_stats()
        (index_stats, index_error), (all_stats_raw, all_error) = await asyncio.gather(index_task, all_task)

        if index_error is not None:
            notes.append("failed to retrieve index stats from MeiliSearch")
            errors.append(index_error)

        if all_error is not None:
            notes.append("failed to retrieve global stats from MeiliSearch")
            errors.append(all_error)

        all_stats = all_stats_raw if isinstance(all_stats_raw, dict) else {}
        index_payload = self._extract_index_payload(all_stats, self._index_name)

        total_documents = 0
        is_indexing = False

        if index_stats is not None:
            total_documents = int(getattr(index_stats, "number_of_documents", 0) or 0)
            is_indexing = bool(getattr(index_stats, "is_indexing", False))
        else:
            total_documents = int(index_payload.get("numberOfDocuments") or 0)
            is_indexing = bool(index_payload.get("isIndexing", False))

        database_size = self._safe_int(all_stats.get("databaseSize"))
        last_update = self._parse_datetime(all_stats.get("lastUpdate"))
        if last_update is None:
            last_update = self._parse_datetime(index_payload.get("lastUpdate"))

        snapshot = IndexSnapshot(
            total_documents=total_documents,
            is_indexing=is_indexing,
            database_size=database_size,
            last_update=last_update,
            meili_connected=index_stats is not None or bool(all_stats),
            notes=notes,
            errors=errors,
        )

        self._log_snapshot(
            trace_id=trace_id,
            source=source,
            snapshot_type="index",
            started_at=started_at,
            notes=notes,
            errors=errors,
        )
        return snapshot

    async def system_snapshot(
        self,
        *,
        uptime_seconds: float,
        bot_running: bool,
        telegram_connected: bool,
        source: str = "unknown",
    ) -> SystemSnapshot:
        """Collect runtime system snapshot."""
        started_at = time.monotonic()
        trace_id = uuid.uuid4().hex[:8]

        index = await self.index_snapshot(source=source)
        memory_usage_mb, memory_notes = self._read_memory_usage_mb()

        notes = list(index.notes)
        notes.extend(memory_notes)
        errors = list(index.errors)

        snapshot = SystemSnapshot(
            uptime_seconds=max(float(uptime_seconds), 0.0),
            meili_connected=index.meili_connected,
            telegram_connected=telegram_connected,
            bot_running=bot_running,
            indexed_messages=index.total_documents,
            memory_usage_mb=memory_usage_mb,
            notes=notes,
            errors=errors,
        )

        self._log_snapshot(
            trace_id=trace_id,
            source=source,
            snapshot_type="system",
            started_at=started_at,
            notes=notes,
            errors=errors,
        )
        return snapshot

    async def storage_snapshot(self, *, source: str = "unknown") -> StorageSnapshot:
        """Collect storage snapshot derived from index/global stats."""
        started_at = time.monotonic()
        trace_id = uuid.uuid4().hex[:8]

        index = await self.index_snapshot(source=source)
        notes = list(index.notes)
        notes.append("media storage is disabled in current architecture")

        snapshot = StorageSnapshot(
            total_bytes=index.database_size,
            index_bytes=index.database_size,
            media_supported=False,
            cache_supported=False,
            notes=notes,
            errors=list(index.errors),
        )

        self._log_snapshot(
            trace_id=trace_id,
            source=source,
            snapshot_type="storage",
            started_at=started_at,
            notes=snapshot.notes,
            errors=snapshot.errors,
        )
        return snapshot

    async def progress_snapshot(self, *, source: str = "unknown") -> ProgressSnapshot:
        """Collect in-memory progress snapshot for REST/WebSocket consistency checks."""
        started_at = time.monotonic()
        trace_id = uuid.uuid4().hex[:8]

        notes: list[str] = []
        progress_data: dict[str, dict[str, Any]] = {}
        active_count = 0

        if self._progress_registry is None:
            notes.append("progress registry unavailable")
        else:
            raw_progress = self._progress_registry.get_all_progress()
            for dialog_id, progress in raw_progress.items():
                if hasattr(progress, "to_dict") and callable(progress.to_dict):
                    payload = progress.to_dict()
                elif isinstance(progress, dict):
                    payload = dict(progress)
                else:
                    payload = {}

                progress_data[str(dialog_id)] = payload
                if payload.get("status") == "downloading":
                    active_count += 1

        snapshot = ProgressSnapshot(
            all_progress=progress_data,
            active_count=active_count,
            notes=notes,
        )

        self._log_snapshot(
            trace_id=trace_id,
            source=source,
            snapshot_type="progress",
            started_at=started_at,
            notes=notes,
            errors=[],
        )
        return snapshot
