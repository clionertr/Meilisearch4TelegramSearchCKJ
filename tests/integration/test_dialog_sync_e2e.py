"""
E2E 集成测试：P0 Dialog Sync API

连接真实运行中的 API 服务器 + 真实 MeiliSearch，验证 dialog 同步生命周期。

需要设置环境变量：
    TEST_API_BASE_URL=http://localhost:8000   (API 服务器地址)
    TEST_MEILI_HOST=http://localhost:7700     (MeiliSearch 地址)
    TEST_MEILI_KEY=<master_key>              (MeiliSearch key)
    RUN_INTEGRATION_TESTS=true              (启用集成测试)
    TEST_BEARER_TOKEN=<Bearer Token>         (可选，否则尝试无 Bearer 的情况)

可单独运行:
    RUN_INTEGRATION_TESTS=true pytest tests/integration/test_dialog_sync_e2e.py -v -s

注意：GET /available 依赖真实 Telegram 客户端（API-only 模式下返回空列表）。
      测试不强要求 dialogs 非空，只验证格式和行为。
"""

import os
import sys
from pathlib import Path

import httpx
import pytest

# 确保项目根目录可导入
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# 集成测试门控
if os.getenv("RUN_INTEGRATION_TESTS", "").lower() not in ("1", "true", "yes"):
    pytest.skip(
        "Dialog Sync E2E tests disabled. Set RUN_INTEGRATION_TESTS=true to enable.",
        allow_module_level=True,
    )

from tests.integration.config import TEST_API_BASE_URL  # noqa: E402
from tests.integration.conftest import switchable  # noqa: E402

pytestmark = [pytest.mark.integration, pytest.mark.e2e, pytest.mark.meili]

# ── Bearer Token ──────────────────────────────────────────────────────────
# 集成测试环境中需要提前登录并设置 TEST_BEARER_TOKEN
_TEST_BEARER_TOKEN = os.getenv("TEST_BEARER_TOKEN", "")


def _auth_headers() -> dict[str, str]:
    if _TEST_BEARER_TOKEN:
        return {"Authorization": f"Bearer {_TEST_BEARER_TOKEN}"}
    return {}


def _has_token() -> bool:
    return bool(_TEST_BEARER_TOKEN)


# ── 日志工具（复用 test_api_e2e.py 约定） ─────────────────────────────────

import json  # noqa: E402


def _log(method: str, path: str, status: int, body: dict | None = None) -> None:
    print(f"\n  [{method} {path}] -> {status}")
    if body:
        print(f"  Response: {json.dumps(body, indent=2, ensure_ascii=False)[:500]}")


def _assert_audit(condition: bool, title: str, detail: str) -> None:
    if condition:
        print(f"  {title}✅️ ({detail})")
        return
    print(f"  {title}❌ ({detail})")
    raise AssertionError(f"{title}: {detail}")


# ── INDEX 清理辅助（直接访问 MeiliSearch） ────────────────────────────────

def _cleanup_dialog_sync_in_config(host: str, key: str) -> None:
    """测试结束后清理 config_store 中注入的 dialog 同步配置（optional best-effort）"""
    pass  # 生产 config_store 数据由 API DELETE /sync 端点清理；E2E 测试自己管理


# ══════════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def api_client() -> httpx.Client:
    with httpx.Client(base_url=TEST_API_BASE_URL, timeout=20.0) as c:
        yield c


# ══════════════════════════════════════════════════════════════════════════
# E2E Tests
# ══════════════════════════════════════════════════════════════════════════


class TestDialogSyncE2E:
    """Dialog Sync E2E 集成测试"""

    @switchable("dialog_sync_auth")
    def test_01_no_token_returns_401(self, api_client: httpx.Client):
        """
        AC-1: 无 Token 调用 → 401
        """
        paths = [
            ("GET", "/api/v1/dialogs/available"),
            ("GET", "/api/v1/dialogs/synced"),
        ]
        for method, path in paths:
            if method == "GET":
                r = api_client.get(path)
            else:
                r = api_client.post(path, json={})
            _log(method, path, r.status_code)
            _assert_audit(r.status_code == 401, "无 Token 状态码审核", f"HTTP 401 @ {path}")

    @switchable("dialog_sync_available")
    def test_02_get_available_returns_array(self, api_client: httpx.Client):
        """
        AC-2: GET /available → 200, data.dialogs 是数组
        """
        if not _has_token():
            pytest.skip("TEST_BEARER_TOKEN 未设置，跳过需要 Token 的测试")

        r = api_client.get("/api/v1/dialogs/available", headers=_auth_headers())
        _log("GET", "/api/v1/dialogs/available", r.status_code, r.json())

        _assert_audit(r.status_code == 200, "available 状态码审核", "HTTP 200")
        body = r.json()
        _assert_audit(body.get("success") is True, "available success 标记审核", "success=true")
        _assert_audit(isinstance(body["data"]["dialogs"], list), "dialogs 类型审核", "list")
        _assert_audit("total" in body["data"], "total 字段审核", "包含 total")
        _assert_audit("cached" in body["meta"], "meta.cached 字段审核", "包含 meta.cached")
        _assert_audit("cache_ttl_sec" in body["meta"], "meta.cache_ttl_sec 字段审核", "包含 meta.cache_ttl_sec")
        _assert_audit(body["meta"]["cache_ttl_sec"] == 120, "cache_ttl_sec 值审核", "120s")

    @switchable("dialog_sync_cache")
    def test_03_cache_second_call(self, api_client: httpx.Client):
        """
        AC-3: 连续两次 GET /available → 第二次 meta.cached=true
        """
        if not _has_token():
            pytest.skip("TEST_BEARER_TOKEN 未设置")

        headers = _auth_headers()
        # 强制刷新建立缓存
        api_client.get("/api/v1/dialogs/available?refresh=true", headers=headers)
        # 第二次
        r2 = api_client.get("/api/v1/dialogs/available", headers=headers)
        _log("GET", "/api/v1/dialogs/available", r2.status_code, r2.json())

        _assert_audit(r2.status_code == 200, "第二次请求状态码审核", "HTTP 200")
        _assert_audit(r2.json()["meta"]["cached"] is True, "缓存命中审核", "meta.cached=true")

    @switchable("dialog_sync_cache")
    def test_04_refresh_bypasses_cache(self, api_client: httpx.Client):
        """
        AC-4: refresh=true → meta.cached=false
        """
        if not _has_token():
            pytest.skip("TEST_BEARER_TOKEN 未设置")

        headers = _auth_headers()
        # 先建立缓存
        api_client.get("/api/v1/dialogs/available", headers=headers)
        # 强制刷新
        r = api_client.get("/api/v1/dialogs/available?refresh=true", headers=headers)
        _log("GET", "/api/v1/dialogs/available?refresh=true", r.status_code, r.json())

        _assert_audit(r.status_code == 200, "refresh 状态码审核", "HTTP 200")
        _assert_audit(r.json()["meta"]["cached"] is False, "refresh 绕过缓存审核", "meta.cached=false")

    @switchable("dialog_sync_sync")
    def test_05_post_sync_validation_empty(self, api_client: httpx.Client):
        """
        AC-8: dialog_ids=[] → 422
        """
        if not _has_token():
            pytest.skip("TEST_BEARER_TOKEN 未设置")

        r = api_client.post(
            "/api/v1/dialogs/sync",
            json={"dialog_ids": []},
            headers=_auth_headers(),
        )
        _log("POST", "/api/v1/dialogs/sync (empty)", r.status_code, r.json())
        _assert_audit(r.status_code == 422, "空 dialog_ids 422 审核", "HTTP 422")

    @switchable("dialog_sync_sync")
    def test_06_post_sync_validation_over_limit(self, api_client: httpx.Client):
        """
        AC-9: dialog_ids 超 200 → 422
        """
        if not _has_token():
            pytest.skip("TEST_BEARER_TOKEN 未设置")

        r = api_client.post(
            "/api/v1/dialogs/sync",
            json={"dialog_ids": list(range(201))},
            headers=_auth_headers(),
        )
        _log("POST", "/api/v1/dialogs/sync (over limit)", r.status_code, r.json())
        _assert_audit(r.status_code == 422, "超限 dialog_ids 422 审核", "HTTP 422")

    @switchable("dialog_sync_sync")
    def test_07_post_sync_returns_categories(self, api_client: httpx.Client):
        """
        AC-5: POST /sync 返回 accepted/ignored/not_found 三个列表
        （使用一个不在 available 中的 id 触发 not_found）
        """
        if not _has_token():
            pytest.skip("TEST_BEARER_TOKEN 未设置")

        # 使用必然不存在的 id
        r = api_client.post(
            "/api/v1/dialogs/sync",
            json={"dialog_ids": [-9999999]},
            headers=_auth_headers(),
        )
        _log("POST", "/api/v1/dialogs/sync", r.status_code, r.json())
        _assert_audit(r.status_code == 200, "POST /sync 状态码审核", "HTTP 200")
        body = r.json()
        _assert_audit(body.get("success") is True, "POST /sync success 审核", "success=true")
        data = body["data"]
        _assert_audit("accepted" in data, "accepted 字段审核", "包含 accepted")
        _assert_audit("ignored" in data, "ignored 字段审核", "包含 ignored")
        _assert_audit("not_found" in data, "not_found 字段审核", "包含 not_found")
        _assert_audit(-9999999 in data["not_found"], "not_found 内容审核", "-9999999 in not_found")

    @switchable("dialog_sync_patch")
    def test_08_patch_sync_state_not_synced_404(self, api_client: httpx.Client):
        """
        AC-6: 未同步的 dialog → 404
        """
        if not _has_token():
            pytest.skip("TEST_BEARER_TOKEN 未设置")

        r = api_client.patch(
            "/api/v1/dialogs/-9999888/sync-state",
            json={"sync_state": "paused"},
            headers=_auth_headers(),
        )
        _log("PATCH", "/api/v1/dialogs/-9999888/sync-state", r.status_code, r.json())
        _assert_audit(r.status_code == 404, "未同步 dialog PATCH 404 审核", "HTTP 404")

    @switchable("dialog_sync_delete")
    def test_09_delete_sync_not_synced_404(self, api_client: httpx.Client):
        """
        DELETE 未同步 dialog → 404
        """
        if not _has_token():
            pytest.skip("TEST_BEARER_TOKEN 未设置")

        r = api_client.delete(
            "/api/v1/dialogs/-9999777/sync",
            headers=_auth_headers(),
        )
        _log("DELETE", "/api/v1/dialogs/-9999777/sync", r.status_code, r.json())
        _assert_audit(r.status_code == 404, "未同步 dialog DELETE 404 审核", "HTTP 404")

    @switchable("dialog_sync_sync")
    def test_10_synced_returns_array(self, api_client: httpx.Client):
        """
        GET /synced → 200, dialogs 是列表
        """
        if not _has_token():
            pytest.skip("TEST_BEARER_TOKEN 未设置")

        r = api_client.get("/api/v1/dialogs/synced", headers=_auth_headers())
        _log("GET", "/api/v1/dialogs/synced", r.status_code, r.json())
        _assert_audit(r.status_code == 200, "synced 状态码审核", "HTTP 200")
        body = r.json()
        _assert_audit(body.get("success") is True, "synced success 标记审核", "success=true")
        _assert_audit(isinstance(body["data"]["dialogs"], list), "synced dialogs 类型审核", "list")
        _assert_audit("total" in body["data"], "synced total 字段审核", "包含 total")
