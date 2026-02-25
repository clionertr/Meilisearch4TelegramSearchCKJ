"""Unit tests for ObservabilityService."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tg_search.services.observability_service import ObservabilityService

pytestmark = [pytest.mark.unit]


class _FailingMeili:
    def __init__(self):
        self.client = SimpleNamespace(get_all_stats=self._raise)

    @staticmethod
    def _raise(*_args, **_kwargs):
        raise RuntimeError("boom")

    @staticmethod
    def get_index_stats(*_args, **_kwargs):
        raise RuntimeError("boom")


class _HealthyMeili:
    def __init__(self):
        self.client = SimpleNamespace(get_all_stats=self.get_all_stats)

    @staticmethod
    def get_index_stats(*_args, **_kwargs):
        return SimpleNamespace(number_of_documents=7, is_indexing=False)

    @staticmethod
    def get_all_stats():
        return {
            "databaseSize": 2048,
            "lastUpdate": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "indexes": {
                "telegram": {
                    "numberOfDocuments": 7,
                    "isIndexing": False,
                }
            },
        }


class _FakeProgress:
    def __init__(self, status: str):
        self.status = status

    def to_dict(self):
        return {
            "status": self.status,
            "current": 1,
            "total": 2,
        }


class _FakeProgressRegistry:
    def get_all_progress(self):
        return {
            1: _FakeProgress("downloading"),
            2: _FakeProgress("completed"),
        }


@pytest.mark.asyncio
async def test_index_snapshot_degrades_when_meili_unavailable():
    service = ObservabilityService(_FailingMeili())

    snapshot = await service.index_snapshot(source="test")

    assert snapshot.meili_connected is False
    assert snapshot.total_documents == 0
    assert len(snapshot.notes) >= 1
    assert len(snapshot.errors) >= 1


@pytest.mark.asyncio
async def test_system_snapshot_contains_memory_diagnostic_note(monkeypatch: pytest.MonkeyPatch):
    service = ObservabilityService(_HealthyMeili())

    monkeypatch.setattr(
        service,
        "_read_memory_usage_mb",
        lambda: (0.0, ["memory usage metric unavailable on this platform"]),
    )

    snapshot = await service.system_snapshot(
        uptime_seconds=10.0,
        bot_running=True,
        telegram_connected=False,
        source="test",
    )

    assert snapshot.indexed_messages == 7
    assert snapshot.meili_connected is True
    assert any("memory" in note.lower() for note in snapshot.notes)


@pytest.mark.asyncio
async def test_progress_snapshot_counts_active_tasks():
    service = ObservabilityService(
        _HealthyMeili(),
        progress_registry=_FakeProgressRegistry(),
    )

    snapshot = await service.progress_snapshot(source="test")

    assert snapshot.active_count == 1
    assert set(snapshot.all_progress.keys()) == {"1", "2"}
