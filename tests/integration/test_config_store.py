"""ConfigStore integration tests against real SQLite persistence."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from tg_search.config.config_store import ConfigStore, GlobalConfig

pytestmark = [pytest.mark.integration]


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "config_store.sqlite3"


@pytest.fixture
def store(db_path: Path) -> ConfigStore:
    return ConfigStore(None, db_path=str(db_path))


class TestGlobalConfigDefaults:
    """GlobalConfig Pydantic defaults."""

    def test_default_id(self):
        config = GlobalConfig()
        assert config.id == "global"

    def test_default_version_is_zero(self):
        config = GlobalConfig()
        assert config.version == 0

    def test_default_sync_section(self):
        config = GlobalConfig()
        assert config.sync.dialogs == {}
        assert config.sync.available_cache_ttl_sec == 120

    def test_default_storage_section(self):
        config = GlobalConfig()
        assert config.storage.auto_clean_enabled is False
        assert config.storage.media_retention_days == 30

    def test_default_ai_section(self):
        config = GlobalConfig()
        assert config.ai.provider == "openai_compatible"
        assert config.ai.model == "gpt-4o-mini"
        assert config.ai.api_key == ""


class TestLoadConfig:
    def test_returns_defaults_on_first_start(self, store: ConfigStore, db_path: Path):
        config = store.load_config(refresh=True)

        assert isinstance(config, GlobalConfig)
        assert config.id == "global"
        assert config.version == 0
        assert config.storage.auto_clean_enabled is False
        assert config.ai.model == "gpt-4o-mini"
        assert db_path.exists()

    def test_cache_hit_returns_same_object_identity(self, store: ConfigStore):
        first = store.load_config()
        second = store.load_config()
        assert first is second

    def test_refresh_true_bypasses_cache(self, store: ConfigStore):
        first = store.load_config()
        second = store.load_config(refresh=True)
        assert first.version == second.version
        assert first is not second


class TestSaveConfig:
    def test_increments_version(self, store: ConfigStore):
        before = store.load_config(refresh=True)
        result = store.save_config({"storage": {"auto_clean_enabled": True, "media_retention_days": 14}})
        persisted = store.load_config(refresh=True)

        assert result.version == before.version + 1
        assert persisted.version == before.version + 1
        assert persisted.storage.auto_clean_enabled is True
        assert persisted.storage.media_retention_days == 14

    def test_save_invalidates_cache(self, store: ConfigStore):
        store.save_config({"storage": {"auto_clean_enabled": False, "media_retention_days": 30}})
        config = store.load_config()
        assert config.storage.auto_clean_enabled is False

    def test_version_conflict_raises(self, store: ConfigStore):
        current = store.load_config(refresh=True)
        with pytest.raises(ValueError, match="version"):
            store.save_config(
                {"storage": {"auto_clean_enabled": True, "media_retention_days": 30}},
                expected_version=current.version - 10,
            )


class TestUpdateSection:
    def test_update_ai_section(self, store: ConfigStore):
        before = store.load_config(refresh=True)
        storage_before = before.storage.model_dump()

        result = store.update_section("ai", {"model": "gpt-4o", "api_key": "sk-unittest"})
        persisted = store.load_config(refresh=True)

        assert result.ai.model == "gpt-4o"
        assert result.ai.api_key == "sk-unittest"
        assert result.storage.model_dump() == storage_before
        assert result.version == before.version + 1
        assert persisted.ai.model == "gpt-4o"

    def test_update_storage_section(self, store: ConfigStore):
        before = store.load_config(refresh=True)
        ai_before = before.ai.model_dump()

        result = store.update_section("storage", {"auto_clean_enabled": True, "media_retention_days": 7})

        assert result.storage.auto_clean_enabled is True
        assert result.storage.media_retention_days == 7
        assert result.ai.model_dump() == ai_before
        assert result.version == before.version + 1

    def test_update_sync_section(self, store: ConfigStore):
        before = store.load_config(refresh=True)
        result = store.update_section("sync", {"available_cache_ttl_sec": 300, "dialogs": {}})
        assert result.sync.available_cache_ttl_sec == 300
        assert result.version == before.version + 1


class TestDialogStateGranularity:
    def test_upsert_dialogs_does_not_replace_existing_rows(self, store: ConfigStore):
        store.upsert_dialog_states({100: {"sync_state": "active", "updated_at": "2026-02-28T00:00:00+00:00"}})
        store.upsert_dialog_states({200: {"sync_state": "paused", "updated_at": "2026-02-28T00:00:01+00:00"}})

        cfg = store.load_config(refresh=True)
        assert "100" in cfg.sync.dialogs
        assert "200" in cfg.sync.dialogs

    def test_latest_msg_id_survives_sync_section_updates(self, store: ConfigStore):
        store.set_latest_msg_id(100, 123456)
        store.update_section("sync", {"available_cache_ttl_sec": 180})
        assert store.get_latest_msg_id(100) == 123456

    def test_delete_dialog_state(self, store: ConfigStore):
        store.upsert_dialog_states({300: {"sync_state": "active", "updated_at": "2026-02-28T00:00:02+00:00"}})
        removed = store.delete_dialog_state(300)
        cfg = store.load_config(refresh=True)
        assert removed is True
        assert "300" not in cfg.sync.dialogs


class TestFallbackOnBadSchema:
    def test_falls_back_on_invalid_schema(self, store: ConfigStore, db_path: Path):
        store.load_config(refresh=True)

        with sqlite3.connect(db_path) as conn:
            # meta/version 破坏 + storage JSON 破坏
            conn.execute("UPDATE system_meta SET version = 'bad' WHERE id = 1")
            conn.execute("UPDATE system_config SET value = 'not-json' WHERE key = 'storage'")

        config = store.load_config(refresh=True)

        assert config.version == 0
        assert config.storage.auto_clean_enabled is False
        assert config.ai.model == "gpt-4o-mini"
