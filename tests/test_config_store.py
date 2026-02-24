"""
Config Store 测试

使用真实 MeiliSearch 环境测试 GlobalConfig 模型和 ConfigStore 的核心功能。

依赖环境变量（默认值可在 .env 中设置）：
    MEILI_HOST=http://localhost:7700
    MEILI_MASTER_KEY=<master_key>

遵循与 tests/integration/ 相同的真实环境策略：不使用 Mock，直接连接 MeiliSearch。
每个测试类使用独立的索引名称，测试结束后自动清理，确保测试隔离。

注意：tests/conftest.py 中的 setdefault() 会在此模块加载之前覆盖 MEILI_MASTER_KEY
为假值（仅当未设置时）。为正确连接真实 MeiliSearch，
本测试从 .env 文件（如存在）加载凭据，并在 MeiliSearch 不可达时自动跳过。
"""

import os
import time
from pathlib import Path

import pytest

# ── 尝试从 .env 取回真实凭据 ───────────────────────────────────────────────
# 问题背景：conftest.py 先于本模块执行，已通过 setdefault() 设置了假凭据。
# 解决方案：直接读取 .env 文件，如果当前环境变量仍是已知假值则用真实值覆盖。
_FAKE_KEYS: set[str] = {"test_master_key_12345", "test_master_key", "", "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"}

_env_path = Path(__file__).resolve().parents[1] / ".env"
if _env_path.exists():
    try:
        from dotenv import dotenv_values as _dotenv_values

        _dot = _dotenv_values(_env_path)
        # 仅当当前值是假占位符时才覆盖
        if os.environ.get("MEILI_HOST", "") in {"", "http://localhost:7700"}:
            _real_host = _dot.get("MEILI_HOST")
            if _real_host:
                os.environ["MEILI_HOST"] = _real_host
        if os.environ.get("MEILI_MASTER_KEY", "") in _FAKE_KEYS:
            _real_key = _dot.get("MEILI_MASTER_KEY", "")
            if _real_key and _real_key not in _FAKE_KEYS:
                os.environ["MEILI_MASTER_KEY"] = _real_key
    except ImportError:
        pass

os.environ.setdefault("SKIP_CONFIG_VALIDATION", "true")

# 捕获此时的凭据（conftest 已注入，.env 覆盖已尝试）
_MEILI_HOST = os.environ.get("MEILI_HOST", "http://localhost:7700")
_MEILI_KEY = os.environ.get("MEILI_MASTER_KEY", "")

from tg_search.config.config_store import ConfigStore, GlobalConfig  # noqa: E402
from tg_search.core.meilisearch import MeiliSearchClient  # noqa: E402


def _check_meili_available() -> str | None:
    """检查 MeiliSearch 是否可用。返回 None 表示可用，否则返回跳过原因。"""
    if _MEILI_KEY in _FAKE_KEYS:
        return f"MEILI_MASTER_KEY 为测试占位值 ({_MEILI_KEY!r})，跳过真实 MeiliSearch 测试"
    try:
        import httpx

        r = httpx.get(f"{_MEILI_HOST}/health", timeout=3)
        if r.status_code != 200:
            return f"MeiliSearch health check 失败: {r.status_code}"
    except Exception as e:
        return f"MeiliSearch 不可达 ({_MEILI_HOST}): {e}"
    return None


_MEILI_SKIP_REASON = _check_meili_available()
requires_meili = pytest.mark.skipif(
    _MEILI_SKIP_REASON is not None,
    reason=_MEILI_SKIP_REASON or "",
)


# ============ Helper ============


def _wait_task(client: MeiliSearchClient, index_name: str) -> None:
    """等待 MeiliSearch 异步索引任务完成（最多 5 秒）"""
    index = client.client.index(index_name)
    for _ in range(50):
        stats = index.get_stats()
        if not stats.is_indexing:
            return
        time.sleep(0.1)


# ============ Fixtures ============


@pytest.fixture(scope="class")
def meili(request) -> MeiliSearchClient:
    """
    每个测试类使用独立索引的 MeiliSearch 客户端。
    测试完成后删除该索引。
    当 MeiliSearch 不可达或凭据无效时，自动跳过整个类。
    """
    if _MEILI_SKIP_REASON:
        pytest.skip(_MEILI_SKIP_REASON)

    # 根据类名生成唯一索引，避免测试间干扰
    class_name = request.cls.__name__.lower() if request.cls else "default"
    index_name = f"system_config_test_{class_name}"

    client = MeiliSearchClient(_MEILI_HOST, _MEILI_KEY, auto_create_index=False)
    yield client

    # 清理测试索引
    try:
        client.delete_index(index_name)
        time.sleep(0.3)
    except Exception:
        pass


@pytest.fixture(scope="class")
def index_name(request) -> str:
    """返回当前测试类使用的索引名"""
    class_name = request.cls.__name__.lower() if request.cls else "default"
    return f"system_config_test_{class_name}"


@pytest.fixture(scope="class")
def store(meili, index_name) -> ConfigStore:
    """每个测试类共享一个 ConfigStore 实例（同一个索引）"""
    try:
        return ConfigStore(meili, index_name=index_name)
    except Exception as e:
        pytest.skip(f"MeiliSearch 连接或认证失败，跳过测试: {e}")


# ============ Model Tests（不需要 MeiliSearch 连接） ============


class TestGlobalConfigDefaults:
    """GlobalConfig Pydantic 模型默认值验证"""

    def test_default_id(self):
        """id 固定为 'global'"""
        config = GlobalConfig()
        assert config.id == "global"

    def test_default_version_is_zero(self):
        """默认 version 应为 0"""
        config = GlobalConfig()
        assert config.version == 0

    def test_default_sync_section(self):
        """sync 子模型的默认值"""
        config = GlobalConfig()
        assert config.sync.dialogs == {}
        assert config.sync.available_cache_ttl_sec == 120

    def test_default_storage_section(self):
        """storage 子模型的默认值"""
        config = GlobalConfig()
        assert config.storage.auto_clean_enabled is False
        assert config.storage.media_retention_days == 30

    def test_default_ai_section(self):
        """ai 子模型的默认值"""
        config = GlobalConfig()
        assert config.ai.provider == "openai_compatible"
        assert config.ai.model == "gpt-4o-mini"
        assert config.ai.api_key == ""


# ============ ConfigStore Tests（真实 MeiliSearch） ============


@requires_meili
class TestLoadConfig:
    """load_config：首次启动 + 缓存行为"""

    def test_returns_defaults_on_first_start(self, store: ConfigStore, meili: MeiliSearchClient, index_name: str):
        """
        AC-1: 服务首次启动，配置不存在，应返回内置默认值并自动初始化文档。
        """
        config = store.load_config(refresh=True)

        assert isinstance(config, GlobalConfig)
        assert config.id == "global"
        assert config.version == 0
        assert config.storage.auto_clean_enabled is False
        assert config.ai.model == "gpt-4o-mini"

        # 验证：文档已写入 MeiliSearch（可被再次读取）
        _wait_task(meili, index_name)
        config2 = store.load_config(refresh=True)
        assert config2.id == "global"

    def test_cache_hit_avoids_meili_roundtrip(self, store: ConfigStore):
        """
        AC-5: 缓存未过期时，连续读取应命中缓存，返回相同对象。
        """
        first = store.load_config()
        second = store.load_config()
        # 缓存命中 -> 返回同一个 Python 对象（identity check）
        assert first is second

    def test_refresh_true_bypasses_cache(self, store: ConfigStore):
        """
        AC-5: refresh=True 应强制绕过缓存，重新从 MeiliSearch 获取。
        """
        first = store.load_config()
        # 强制刷新应返回新对象（即使内容相同）
        second = store.load_config(refresh=True)
        # 内容应一致，但对象不同（不是同一个缓存引用）
        assert first.version == second.version
        assert first is not second


@requires_meili
class TestSaveConfig:
    """save_config：版本递增 + 缓存失效"""

    def test_increments_version(self, store: ConfigStore, meili: MeiliSearchClient, index_name: str):
        """
        AC-3: 写入成功后，version 应在原基础上加 1。
        """
        before = store.load_config(refresh=True)
        version_before = before.version

        result = store.save_config({"storage": {"auto_clean_enabled": True, "media_retention_days": 14}})
        assert result.version == version_before + 1

        # 持久化验证
        _wait_task(meili, index_name)
        persisted = store.load_config(refresh=True)
        assert persisted.version == version_before + 1
        assert persisted.storage.auto_clean_enabled is True
        assert persisted.storage.media_retention_days == 14

    def test_save_invalidates_cache(self, store: ConfigStore):
        """
        写操作后，下一次 load_config（不带 refresh）应获取最新值。
        """
        store.save_config({"storage": {"auto_clean_enabled": False, "media_retention_days": 30}})
        # 不用 refresh=True，缓存应已失效
        config = store.load_config()
        assert config.storage.auto_clean_enabled is False

    def test_version_conflict_raises(self, store: ConfigStore):
        """
        AC-3: expected_version 与当前 version 不匹配时，应抛出 ValueError。
        """
        current = store.load_config(refresh=True)

        with pytest.raises(ValueError, match="version"):
            store.save_config(
                {"storage": {"auto_clean_enabled": True, "media_retention_days": 30}},
                expected_version=current.version - 10,  # 故意错误的版本
            )


@requires_meili
class TestUpdateSection:
    """update_section：section 级辅助函数"""

    def test_update_ai_section(self, store: ConfigStore, meili: MeiliSearchClient, index_name: str):
        """
        T-P0-CS-05: 更新 ai section，不影响其他 section。
        """
        before = store.load_config(refresh=True)
        storage_before = before.storage.model_dump()

        result = store.update_section("ai", {"model": "gpt-4o", "api_key": "sk-unittest"})

        assert result.ai.model == "gpt-4o"
        assert result.ai.api_key == "sk-unittest"
        # storage 不变
        assert result.storage.model_dump() == storage_before
        # version 递增
        assert result.version == before.version + 1

        # 持久化验证
        _wait_task(meili, index_name)
        persisted = store.load_config(refresh=True)
        assert persisted.ai.model == "gpt-4o"

    def test_update_storage_section(self, store: ConfigStore, meili: MeiliSearchClient, index_name: str):
        """
        T-P0-CS-05: 更新 storage section，不影响 ai section 的核心字段。
        """
        before = store.load_config(refresh=True)
        # 只比较核心字段，排除可能变动的 updated_at
        ai_before_core = {k: v for k, v in before.ai.model_dump().items() if k != "updated_at"}

        result = store.update_section("storage", {"auto_clean_enabled": True, "media_retention_days": 7})

        assert result.storage.auto_clean_enabled is True
        assert result.storage.media_retention_days == 7
        # ai 核心字段不变
        ai_result_core = {k: v for k, v in result.ai.model_dump().items() if k != "updated_at"}
        assert ai_result_core == ai_before_core
        assert result.version == before.version + 1

    def test_update_sync_section(self, store: ConfigStore, meili: MeiliSearchClient, index_name: str):
        """
        T-P0-CS-05: 更新 sync section（available_cache_ttl_sec）。
        """
        before = store.load_config(refresh=True)

        result = store.update_section("sync", {"available_cache_ttl_sec": 300, "dialogs": {}})

        assert result.sync.available_cache_ttl_sec == 300
        assert result.version == before.version + 1


@requires_meili
class TestFallbackOnBadSchema:
    """坏文档回退测试"""

    def test_falls_back_on_invalid_schema(self, store: ConfigStore, meili: MeiliSearchClient, index_name: str):
        """
        AC-4: 配置文档结构不合法，应回退到默认值并记录告警日志。
        """
        # 初始化索引（确保索引存在）
        store.load_config(refresh=True)
        _wait_task(meili, index_name)

        # 直接向 MeiliSearch 写入损坏的文档
        index = meili.client.index(index_name)
        bad_doc = {
            "id": "global",
            "version": "not_an_integer",  # 错误类型
            "storage": 9999,  # 完全错误的类型
        }
        index.add_documents([bad_doc])
        _wait_task(meili, index_name)

        # 强制刷新 -> 应触发 fallback
        import logging
        import unittest.mock as mock

        with mock.patch("tg_search.config.config_store.logger") as mock_logger:
            config = store.load_config(refresh=True)

        # 回退到默认值
        assert config.version == 0
        assert config.storage.auto_clean_enabled is False
        assert config.ai.model == "gpt-4o-mini"
        # 告警日志被记录
        mock_logger.warning.assert_called()
