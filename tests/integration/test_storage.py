"""Storage API integration tests against a real MeiliSearch instance."""

import os
import time
from unittest import mock

import pytest
from tests.helpers.requirements import (
    check_meili_available,
    load_meili_env_from_dotenv,
)

os.environ.setdefault("SKIP_CONFIG_VALIDATION", "true")
load_meili_env_from_dotenv()

# 同步 settings 模块中已缓存的 Meili 变量（conftest 可能已在导入时缓存了假值）
from tg_search.config import settings as _settings  # noqa: E402

_settings.MEILI_PASS = os.environ.get("MEILI_MASTER_KEY", "")
_settings.MEILI_HOST = os.environ.get("MEILI_HOST", "http://localhost:7700")

from fastapi.testclient import TestClient  # noqa: E402

from tg_search.api.app import build_app  # noqa: E402

_MEILI_HOST = os.environ.get("MEILI_HOST", "http://localhost:7700")
_MEILI_KEY = os.environ.get("MEILI_MASTER_KEY", "")

# 测试用 API Key（仅在 fixture 中通过 mock.patch 注入，不修改全局状态）
_TEST_API_KEY = "test-storage-api-key-for-auth"
_AUTH_HEADER = {"X-API-Key": _TEST_API_KEY}


pytestmark = [pytest.mark.integration, pytest.mark.meili]
_MEILI_SKIP_REASON = check_meili_available(_MEILI_HOST, _MEILI_KEY, require_auth=True)
requires_meili = pytest.mark.skipif(
    _MEILI_SKIP_REASON is not None,
    reason=_MEILI_SKIP_REASON or "",
)


# ============ Fixtures ============


@pytest.fixture(scope="module")
def client():
    """
    同步 TestClient，触发 FastAPI lifespan 以初始化 app_state。
    通过 mock.patch 注入 API_KEY，仅在本模块 TestClient 生命周期内生效。
    """
    with (
        mock.patch("tg_search.api.deps.API_KEY", _TEST_API_KEY),
        mock.patch("tg_search.config.settings.API_KEY", _TEST_API_KEY),
    ):
        app = build_app()
        with TestClient(app) as c:
            yield c


# ============ 401 未授权测试 ============


@requires_meili
class TestStorageAuth:
    """验收标准 AC-1: 未携带 Token 时全部返回 401"""

    def test_get_stats_without_auth_returns_401(self, client: TestClient):
        """GET /storage/stats 无认证 → 401"""
        resp = client.get("/api/v1/storage/stats")
        assert resp.status_code == 401

    def test_patch_auto_clean_without_auth_returns_401(self, client: TestClient):
        """PATCH /storage/auto-clean 无认证 → 401"""
        resp = client.patch("/api/v1/storage/auto-clean", json={"enabled": True})
        assert resp.status_code == 401

    def test_cleanup_cache_without_auth_returns_401(self, client: TestClient):
        """POST /storage/cleanup/cache 无认证 → 401"""
        resp = client.post("/api/v1/storage/cleanup/cache")
        assert resp.status_code == 401

    def test_cleanup_media_without_auth_returns_401(self, client: TestClient):
        """POST /storage/cleanup/media 无认证 → 401"""
        resp = client.post("/api/v1/storage/cleanup/media")
        assert resp.status_code == 401


# ============ GET /storage/stats 测试 ============


@requires_meili
class TestGetStorageStats:
    """验收标准 AC-2, AC-3: 存储统计"""

    def test_returns_200_with_stats(self, client: TestClient):
        """GET /storage/stats 返回 200 且包含必要字段"""
        resp = client.get("/api/v1/storage/stats", headers=_AUTH_HEADER)
        assert resp.status_code == 200

        body = resp.json()
        assert body["success"] is True
        data = body["data"]

        assert "total_bytes" in data
        assert "index_bytes" in data
        assert "media_bytes" in data
        assert "media_supported" in data
        assert "cache_supported" in data
        assert "notes" in data

    def test_media_supported_is_false(self, client: TestClient):
        """AC-3: media_supported=false, media_bytes=null"""
        resp = client.get("/api/v1/storage/stats", headers=_AUTH_HEADER)
        data = resp.json()["data"]

        assert data["media_supported"] is False
        assert data["media_bytes"] is None

    def test_index_bytes_is_present(self, client: TestClient):
        """AC-2: index_bytes 来自 MeiliSearch databaseSize"""
        resp = client.get("/api/v1/storage/stats", headers=_AUTH_HEADER)
        data = resp.json()["data"]

        assert data["index_bytes"] is not None
        assert isinstance(data["index_bytes"], int)
        assert data["index_bytes"] >= 0

    def test_total_bytes_equals_index_bytes(self, client: TestClient):
        """当前版本 total_bytes 应等于 index_bytes（无其他存储来源）"""
        resp = client.get("/api/v1/storage/stats", headers=_AUTH_HEADER)
        data = resp.json()["data"]

        assert data["total_bytes"] == data["index_bytes"]

    def test_notes_contains_media_disabled_message(self, client: TestClient):
        """notes 应包含媒体存储禁用说明"""
        resp = client.get("/api/v1/storage/stats", headers=_AUTH_HEADER)
        data = resp.json()["data"]

        assert isinstance(data["notes"], list)
        assert len(data["notes"]) > 0
        assert any("media" in note.lower() for note in data["notes"])


# ============ PATCH /storage/auto-clean 测试 ============


@requires_meili
class TestPatchAutoClean:
    """验收标准 AC-4: auto-clean 配置持久化"""

    def test_returns_200_with_config(self, client: TestClient):
        """PATCH /storage/auto-clean 返回 200 且包含配置"""
        resp = client.patch(
            "/api/v1/storage/auto-clean",
            headers=_AUTH_HEADER,
            json={"enabled": True, "media_retention_days": 14},
        )
        assert resp.status_code == 200

        body = resp.json()
        assert body["success"] is True
        data = body["data"]

        assert data["enabled"] is True
        assert data["media_retention_days"] == 14

    def test_config_persisted(self, client: TestClient):
        """配置修改后应持久化，再次查询应反映新值"""
        client.patch(
            "/api/v1/storage/auto-clean",
            headers=_AUTH_HEADER,
            json={"enabled": True, "media_retention_days": 7},
        )

        time.sleep(0.5)

        resp = client.patch(
            "/api/v1/storage/auto-clean",
            headers=_AUTH_HEADER,
            json={"enabled": False, "media_retention_days": 30},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["enabled"] is False
        assert data["media_retention_days"] == 30

    def test_default_media_retention_days(self, client: TestClient):
        """仅传 enabled 时，media_retention_days 使用默认值 30"""
        resp = client.patch(
            "/api/v1/storage/auto-clean",
            headers=_AUTH_HEADER,
            json={"enabled": True},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["media_retention_days"] == 30


# ============ POST /storage/cleanup/cache 测试 ============


@requires_meili
class TestCleanupCache:
    """验收标准 AC-5: 缓存清理"""

    def test_returns_200_with_targets(self, client: TestClient):
        """POST /storage/cleanup/cache 返回 200 且包含 targets_cleared"""
        resp = client.post("/api/v1/storage/cleanup/cache", headers=_AUTH_HEADER)
        assert resp.status_code == 200

        body = resp.json()
        assert body["success"] is True
        data = body["data"]

        assert "targets_cleared" in data
        assert isinstance(data["targets_cleared"], list)
        assert "freed_bytes" in data

    def test_targets_include_known_caches(self, client: TestClient):
        """targets_cleared 应包含已知缓存项"""
        resp = client.post("/api/v1/storage/cleanup/cache", headers=_AUTH_HEADER)
        data = resp.json()["data"]

        targets = data["targets_cleared"]
        # 应至少包含 dialogs_cache 和 config_cache
        assert "dialogs_cache" in targets
        assert "config_cache" in targets

    def test_freed_bytes_is_null(self, client: TestClient):
        """当前版本 freed_bytes 固定为 null"""
        resp = client.post("/api/v1/storage/cleanup/cache", headers=_AUTH_HEADER)
        data = resp.json()["data"]

        assert data["freed_bytes"] is None


# ============ POST /storage/cleanup/media 测试 ============


@requires_meili
class TestCleanupMedia:
    """验收标准 AC-6: 媒体清理 (当前版本 not_applicable)"""

    def test_returns_200_not_applicable(self, client: TestClient):
        """POST /storage/cleanup/media 返回 200 且 not_applicable=true"""
        resp = client.post("/api/v1/storage/cleanup/media", headers=_AUTH_HEADER)
        assert resp.status_code == 200

        body = resp.json()
        assert body["success"] is True
        data = body["data"]

        assert data["not_applicable"] is True
        assert data["reason"] == "MEDIA_STORAGE_DISABLED"
        assert data["freed_bytes"] == 0
