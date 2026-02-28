"""Unit tests for legacy message_tracker helpers (now backed by SQLite ConfigStore)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tg_search.utils import message_tracker as tracker

pytestmark = [pytest.mark.unit]


def _use_temp_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CONFIG_DB_PATH", str(tmp_path / "config_store_test.sqlite3"))
    tracker._STORE_CACHE.clear()


def test_read_config_from_meili_returns_default_when_empty(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)
    meili = MagicMock()

    result = tracker.read_config_from_meili(meili)

    assert result == {"id": 0}


def test_write_config2_meili_persists_latest_msg_ids(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)
    meili = MagicMock()
    payload = {"id": "global", "123": 456, "-1001": "789"}

    tracker.write_config2_meili(meili, payload)
    result = tracker.read_config_from_meili(meili)

    assert result["123"] == 456
    assert result["-1001"] == 789


def test_read_config_from_meili_on_store_error_returns_default(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)
    meili = MagicMock()
    monkeypatch.setattr(tracker, "_get_config_store", lambda _meili: (_ for _ in ()).throw(RuntimeError("boom")))

    result = tracker.read_config_from_meili(meili)

    assert result == {"id": 0}
