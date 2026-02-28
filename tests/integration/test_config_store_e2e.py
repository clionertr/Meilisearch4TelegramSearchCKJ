"""
E2E 集成测试：ConfigStore (SQLite backend).

门控：
    RUN_INTEGRATION_TESTS=true pytest tests/integration/test_config_store_e2e.py -v -s
"""

from __future__ import annotations

import os
import sqlite3

import pytest

from tests.integration.conftest import switchable
from tg_search.config.config_store import ConfigStore, GlobalConfig

# 集成测试门控 - 遵循现有框架约定
if os.getenv("RUN_INTEGRATION_TESTS", "").lower() not in ("1", "true", "yes"):
    pytest.skip(
        "Config Store integration tests disabled. Set RUN_INTEGRATION_TESTS=true to enable.",
        allow_module_level=True,
    )

pytestmark = [pytest.mark.integration, pytest.mark.e2e]


@pytest.fixture(scope="module")
def db_path(tmp_path_factory):
    return tmp_path_factory.mktemp("config_store_e2e") / "config_store.sqlite3"


@pytest.fixture(scope="module")
def store(db_path):
    return ConfigStore(None, db_path=str(db_path))


class TestConfigStoreE2E:
    """Config Store E2E 集成测试"""

    @switchable("config_store_e2e")
    def test_01_first_load_initializes_document(self, store: ConfigStore):
        config = store.load_config(refresh=True)
        assert isinstance(config, GlobalConfig)
        assert config.id == "global"
        assert config.version == 0
        assert config.storage.auto_clean_enabled is False
        assert config.ai.model == "gpt-4o-mini"

    @switchable("config_store_e2e")
    def test_02_write_then_reload_persists(self, store: ConfigStore):
        new_ai = {"model": "gpt-4o", "api_key": "sk-e2e-test", "base_url": "https://api.openai.com/v1"}
        store.update_section("ai", new_ai)
        config = store.load_config(refresh=True)
        assert config.ai.model == "gpt-4o"
        assert config.ai.api_key == "sk-e2e-test"

    @switchable("config_store_e2e")
    def test_03_concurrent_patch_increments_version(self, store: ConfigStore):
        before = store.load_config(refresh=True)
        version_before = before.version

        store.update_section("storage", {"auto_clean_enabled": True, "media_retention_days": 14})
        after_1 = store.load_config(refresh=True)
        assert after_1.version == version_before + 1

        store.update_section("storage", {"auto_clean_enabled": False, "media_retention_days": 30})
        after_2 = store.load_config(refresh=True)
        assert after_2.version == version_before + 2

    @switchable("config_store_e2e")
    def test_04_bad_schema_falls_back_to_defaults(self, store: ConfigStore, db_path):
        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE system_meta SET version = 'bad' WHERE id = 1")
            conn.execute("UPDATE system_config SET value = 'broken-json' WHERE key = 'storage'")

        config = store.load_config(refresh=True)
        assert config.version == 0
        assert config.storage.auto_clean_enabled is False
        assert config.ai.model == "gpt-4o-mini"
