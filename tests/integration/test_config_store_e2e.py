"""
E2E 集成测试：P0 Config Store

连接真实 MeiliSearch，验证配置读写生命周期。
需要设置环境变量：
    TEST_MEILI_HOST=http://localhost:7700
    TEST_MEILI_KEY=<master_key>
    RUN_INTEGRATION_TESTS=true

可单独运行:
    pytest tests/integration/test_config_store_e2e.py -v -s
"""

import os
import sys
from pathlib import Path

import pytest

# 确保项目根目录可导入
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# 集成测试门控 - 遵循现有框架约定
if os.getenv("RUN_INTEGRATION_TESTS", "").lower() not in ("1", "true", "yes"):
    pytest.skip(
        "Config Store integration tests disabled. Set RUN_INTEGRATION_TESTS=true to enable.",
        allow_module_level=True,
    )

from tests.integration.config import TEST_MEILI_HOST, TEST_MEILI_KEY  # noqa: E402
from tests.integration.conftest import switchable  # noqa: E402
from tg_search.config.config_store import ConfigStore, GlobalConfig  # noqa: E402
from tg_search.core.meilisearch import MeiliSearchClient  # noqa: E402

pytestmark = [pytest.mark.integration, pytest.mark.e2e, pytest.mark.meili]

# ============ Constants ============

INDEX_NAME = "system_config_test_e2e"  # 使用专用测试索引，避免污染生产数据


# ============ Fixtures ============


@pytest.fixture(scope="module")
def meili_client():
    """创建真实 MeiliSearch 客户端（仅连接，不自动创建 telegram 索引）"""
    client = MeiliSearchClient(TEST_MEILI_HOST, TEST_MEILI_KEY, auto_create_index=False)
    yield client
    # 测试结束后清理测试索引
    try:
        client.delete_index(INDEX_NAME)
    except Exception:
        pass


@pytest.fixture(scope="module")
def store(meili_client):
    """创建 ConfigStore，使用隔离的测试索引"""
    return ConfigStore(meili_client, index_name=INDEX_NAME)


# ============ E2E Tests ============


class TestConfigStoreE2E:
    """Config Store E2E 集成测试"""

    @switchable("config_store_e2e")
    def test_01_first_load_initializes_document(self, store: ConfigStore):
        """
        AC-1: 首次启动读配置 -> 自动初始化。
        """
        # 强制刷新，跳过缓存，确保从 MeiliSearch 读取
        config = store.load_config(refresh=True)

        assert isinstance(config, GlobalConfig)
        assert config.id == "global"
        assert config.version == 0
        # 默认值正确
        assert config.storage.auto_clean_enabled is False
        assert config.ai.model == "gpt-4o-mini"

    @switchable("config_store_e2e")
    def test_02_write_then_reload_persists(self, store: ConfigStore):
        """
        AC-2: 写入 AI 配置后，重新读取（强制刷新）应返回写入值。
        """
        new_ai = {"model": "gpt-4o", "api_key": "sk-e2e-test", "base_url": "https://api.openai.com/v1"}
        store.update_section("ai", new_ai)

        # 强制绕过缓存
        config = store.load_config(refresh=True)

        assert config.ai.model == "gpt-4o"
        assert config.ai.api_key == "sk-e2e-test"

    @switchable("config_store_e2e")
    def test_03_concurrent_patch_increments_version(self, store: ConfigStore):
        """
        AC-3: 多次 patch -> version 正确递增。
        """
        # 读取当前版本
        before = store.load_config(refresh=True)
        version_before = before.version

        # Patch 1
        store.update_section("storage", {"auto_clean_enabled": True, "media_retention_days": 14})
        after_1 = store.load_config(refresh=True)
        assert after_1.version == version_before + 1

        # Patch 2
        store.update_section("storage", {"auto_clean_enabled": False, "media_retention_days": 30})
        after_2 = store.load_config(refresh=True)
        assert after_2.version == version_before + 2

    @switchable("config_store_e2e")
    def test_04_bad_schema_falls_back_to_defaults(self, store: ConfigStore):
        """
        AC-4: 手动注入坏 schema -> 启动后回退默认。
        """
        import time

        # 直接向 MeiliSearch 写入一个损坏的文档
        index = store._meili.client.index(INDEX_NAME)
        bad_doc = {
            "id": "global",
            "version": "this_is_not_an_int",  # 类型错误
            "storage": 999,  # 完全错误的类型
        }
        index.add_documents([bad_doc])

        # 等待 MeiliSearch 索引完成（它是异步的）
        time.sleep(1)

        # 强制刷新缓存，应触发 fallback
        config = store.load_config(refresh=True)

        # 回退到默认值
        assert config.version == 0
        assert config.storage.auto_clean_enabled is False
        assert config.ai.model == "gpt-4o-mini"
