"""Dialog Sync integration tests against real MeiliSearch + FastAPI app."""

from __future__ import annotations

import asyncio
import os
import time
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from tests.helpers.requirements import (
    check_meili_available,
    load_meili_env_from_dotenv,
)

# ── 环境设置（必须在 import 项目模块前） ────────────────────────────────────
os.environ.setdefault("SKIP_CONFIG_VALIDATION", "true")
os.environ.setdefault("API_ONLY", "true")
os.environ.setdefault("DISABLE_BOT_AUTOSTART", "1")
os.environ.setdefault("DISABLE_AUTH_CLEANUP_TASK", "1")
os.environ.setdefault("DISABLE_THREAD_OFFLOAD", "1")
os.environ.setdefault("APP_ID", "12345")
os.environ.setdefault("APP_HASH", "testhash")
os.environ.setdefault("BOT_TOKEN", "1:test")
load_meili_env_from_dotenv()

# ── MeiliSearch 连接参数（在环境设置之后读取） ─────────────────────────────
_MEILI_HOST = os.environ.get("MEILI_HOST", "http://localhost:7700")
_MEILI_KEY = os.environ.get("MEILI_MASTER_KEY", "")

pytestmark = [pytest.mark.integration, pytest.mark.meili]
_MEILI_SKIP_REASON = check_meili_available(_MEILI_HOST, _MEILI_KEY, require_auth=True)
requires_meili = pytest.mark.skipif(
    _MEILI_SKIP_REASON is not None,
    reason=_MEILI_SKIP_REASON or "",
)

# ── 必要导入（在环境变量设置之后） ────────────────────────────────────────
from tg_search.api.app import build_app, lifespan  # noqa: E402
from tg_search.api.auth_store import AuthStore, AuthToken  # noqa: E402
from tg_search.api.models import (  # noqa: E402
    AvailableDialogItem,
    AvailableDialogsMeta,
    AvailableDialogsResponse,
    DeleteSyncResult,
    PatchSyncStateRequest,
    SyncedDialogItem,
    SyncRequest,
    SyncResult,
)

# ══════════════════════════════════════════════════════════════════════════
# Pydantic 模型测试（T-P0-DS-01）
# 不需要 MeiliSearch 连接
# ══════════════════════════════════════════════════════════════════════════


class TestDialogPydanticModels:
    """T-P0-DS-01: Dialog API Pydantic 模型默认值和字段验证"""

    def test_available_dialog_item_defaults(self):
        """AvailableDialogItem 默认 sync_state=inactive, message_count=None"""
        item = AvailableDialogItem(id=-100123, title="Tech Group", type="group")
        assert item.id == -100123
        assert item.title == "Tech Group"
        assert item.type == "group"
        assert item.message_count is None  # ADR-DS-002
        assert item.sync_state == "inactive"

    def test_available_dialogs_meta(self):
        """AvailableDialogsMeta 包含 cached 和 cache_ttl_sec"""
        meta = AvailableDialogsMeta(cached=True, cache_ttl_sec=120)
        assert meta.cached is True
        assert meta.cache_ttl_sec == 120

    def test_sync_request_dedup_and_limits(self):
        """SyncRequest: dialog_ids 空列表应 Pydantic 验证失败"""
        with pytest.raises(Exception):
            SyncRequest(dialog_ids=[])

    def test_sync_request_over_limit(self):
        """SyncRequest: dialog_ids 超过 200 应 Pydantic 验证失败"""
        with pytest.raises(Exception):
            SyncRequest(dialog_ids=list(range(201)))

    def test_sync_result_fields(self):
        """SyncResult 含 accepted/ignored/not_found"""
        result = SyncResult(accepted=[1], ignored=[2], not_found=[3])
        assert result.accepted == [1]
        assert result.ignored == [2]
        assert result.not_found == [3]

    def test_patch_sync_state_request(self):
        """PatchSyncStateRequest 接受 active/paused"""
        req = PatchSyncStateRequest(sync_state="paused")
        assert req.sync_state == "paused"

    def test_delete_sync_result(self):
        """DeleteSyncResult 含 removed/purge_index/purge_error"""
        result = DeleteSyncResult(removed=True, purge_index=True)
        assert result.removed is True
        assert result.purge_index is True
        assert result.purge_error is None

    def test_synced_dialog_item_fields(self):
        """SyncedDialogItem 包含所有必须字段"""
        item = SyncedDialogItem(
            id=-100123,
            title="Group",
            type="group",
            sync_state="active",
            updated_at="2026-02-24T10:00:00Z",
        )
        assert item.sync_state == "active"
        assert item.is_syncing is False
        assert item.last_synced_at is None

    def test_patch_invalid_sync_state_422(self):
        """Fix-1: PatchSyncStateRequest 拒绝非枚举值"""
        with pytest.raises(Exception):
            PatchSyncStateRequest(sync_state="invalid_state")
        with pytest.raises(Exception):
            PatchSyncStateRequest(sync_state="inactive")

    def test_sync_default_state_invalid_422(self):
        """Fix-1: SyncRequest.default_sync_state 拒绝非枚举值"""
        with pytest.raises(Exception):
            SyncRequest(dialog_ids=[1], default_sync_state="stopped")
        # 合法值不应报错
        req = SyncRequest(dialog_ids=[1], default_sync_state="paused")
        assert req.default_sync_state == "paused"


# ══════════════════════════════════════════════════════════════════════════
# API 端点测试
# 需要真实 MeiliSearch（用于 ConfigStore）
# ══════════════════════════════════════════════════════════════════════════

# ── 每个测试类独立 ConfigStore 索引 ───────────────────────────────────────
_DS_INDEX_PREFIX = "system_config_test_dialogs_"


def _class_index(class_name: str) -> str:
    return f"{_DS_INDEX_PREFIX}{class_name.lower()}"


def _extract_task_uid(task_info) -> int | None:
    """兼容 SDK 对 TaskInfo 的不同字段命名"""
    for field in ("task_uid", "uid", "taskUid"):
        value = getattr(task_info, field, None)
        if isinstance(value, int):
            return value
    if isinstance(task_info, dict):
        for field in ("task_uid", "uid", "taskUid"):
            value = task_info.get(field)
            if isinstance(value, int):
                return value
    return None


def _wait_task(meili_client, task_info, timeout_ms: int = 8000) -> None:
    """等待异步任务完成（best effort）"""
    task_uid = _extract_task_uid(task_info)
    if task_uid is None:
        return
    wait_for_task = getattr(meili_client.client, "wait_for_task", None)
    if not callable(wait_for_task):
        return
    try:
        wait_for_task(task_uid, timeout_in_ms=timeout_ms, interval_in_ms=50)
    except TypeError:
        wait_for_task(task_uid)


def _delete_docs_by_chat_id(meili_client, idx, chat_id: int) -> None:
    """测试辅助：兼容是否支持 delete_documents_by_filter"""
    delete_by_filter = getattr(idx, "delete_documents_by_filter", None)
    if callable(delete_by_filter):
        _wait_task(meili_client, delete_by_filter(f"chat.id = {chat_id}"))
        return

    result = idx.search("", {"filter": f"chat.id = {chat_id}", "limit": 200, "attributesToRetrieve": ["id"]})
    ids = [hit.get("id") for hit in result.get("hits", []) if isinstance(hit.get("id"), int)]
    if ids:
        _wait_task(meili_client, idx.delete_documents(ids))


@pytest.fixture(scope="module")
def real_meili_client():
    """真实 MeiliSearch 客户端（auto_create_index=False）"""
    if _MEILI_SKIP_REASON:
        pytest.skip(_MEILI_SKIP_REASON)

    from tg_search.core.meilisearch import MeiliSearchClient

    client = MeiliSearchClient(_MEILI_HOST, _MEILI_KEY, auto_create_index=False)
    return client


def _make_bearer_token(client: httpx.AsyncClient) -> str:
    """通过 app_state.auth_store 生成一个合法 Bearer Token"""
    # 直接访问 app state 内的 auth_store（测试专用）
    auth_store: AuthStore = client.app.state.app_state.auth_store  # type: ignore[attr-defined]
    import asyncio

    user_info = {"id": 99999, "username": "tester"}
    token_obj: AuthToken = asyncio.get_event_loop().run_until_complete(auth_store.create_token(user_info))
    return token_obj.token


def _get_auth_store(app) -> AuthStore:
    return app.state.app_state.auth_store


@pytest.fixture(scope="class")
def index_name(request) -> str:
    class_name = request.cls.__name__ if request.cls else "default"
    return _class_index(class_name)


# ── App 工厂：使用真实 MeiliSearch，但不连接 Telegram ─────────────────────

@pytest.fixture(scope="class")
async def ds_client(real_meili_client, index_name) -> AsyncGenerator[dict, None]:
    """
    返回 {"client": httpx.AsyncClient, "bearer": str, "app": FastAPI app}

    * 用真实 MeiliSearchClient（真实 ConfigStore 写入索引）
    * Mock Telegram client（iter_dialogs 返回可控假数据）
    * 测试结束后清理索引
    """
    from tg_search.api.state import AppState
    from tg_search.config.config_store import ConfigStore

    mock_tg = AsyncMock()
    mock_tg_dialog_1 = MagicMock()
    mock_tg_dialog_1.id = -100111
    mock_tg_dialog_1.title = "Group One"
    mock_tg_dialog_1.is_group = True
    mock_tg_dialog_1.is_channel = False
    mock_tg_dialog_1.is_user = False

    mock_tg_dialog_2 = MagicMock()
    mock_tg_dialog_2.id = -100222
    mock_tg_dialog_2.title = "Channel Two"
    mock_tg_dialog_2.is_group = False
    mock_tg_dialog_2.is_channel = True
    mock_tg_dialog_2.is_user = False

    # iter_dialogs 是一个异步生成器
    async def _iter_dialogs():
        yield mock_tg_dialog_1
        yield mock_tg_dialog_2

    mock_tg.iter_dialogs = _iter_dialogs

    with patch("tg_search.api.app.MeiliSearchClient", return_value=real_meili_client):
        app = build_app()
        async with lifespan(app):
            # 替换 config_store 使用隔离索引
            store = ConfigStore(real_meili_client, index_name=index_name)
            app.state.app_state.config_store = store
            # 注入 telegram_client
            app.state.app_state.telegram_client = mock_tg
            # 确保 meili_client 正确
            app.state.app_state.meili_client = real_meili_client

            transport = httpx.ASGITransport(app=app, raise_app_exceptions=True)
            async with httpx.AsyncClient(
                transport=transport, base_url="http://testserver"
            ) as client:
                # 生成 Bearer Token
                auth_store: AuthStore = app.state.app_state.auth_store
                token_obj = await auth_store.issue_token(
                    user_id=99999,
                    phone_number="+8600000000000",
                    username="tester",
                )
                bearer = token_obj.token

                client.app = app  # type: ignore[attr-defined]
                yield {"client": client, "bearer": bearer, "store": store, "app": app}

    # 清理隔离索引
    try:
        real_meili_client.delete_index(index_name)
        time.sleep(0.3)
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════
# AC-1: 鉴权 - 无 Token → 401
# ══════════════════════════════════════════════════════════════════════════


@requires_meili
class TestDialogAuthRequired:
    """AC-1: 所有 /dialogs/* 端点在无 Token 时返回 401"""

    async def test_available_no_token_401(self, ds_client):
        c = ds_client["client"]
        r = await c.get("/api/v1/dialogs/available")
        assert r.status_code == 401, f"Expected 401, got {r.status_code}: {r.text}"

    async def test_synced_no_token_401(self, ds_client):
        c = ds_client["client"]
        r = await c.get("/api/v1/dialogs/synced")
        assert r.status_code == 401

    async def test_post_sync_no_token_401(self, ds_client):
        c = ds_client["client"]
        r = await c.post("/api/v1/dialogs/sync", json={"dialog_ids": [1]})
        assert r.status_code == 401

    async def test_patch_sync_state_no_token_401(self, ds_client):
        c = ds_client["client"]
        r = await c.patch("/api/v1/dialogs/-100111/sync-state", json={"sync_state": "paused"})
        assert r.status_code == 401

    async def test_delete_sync_no_token_401(self, ds_client):
        c = ds_client["client"]
        r = await c.delete("/api/v1/dialogs/-100111/sync")
        assert r.status_code == 401


# ══════════════════════════════════════════════════════════════════════════
# AC-2/3/4: GET /available - 返回数组、缓存、refresh
# ══════════════════════════════════════════════════════════════════════════


@requires_meili
class TestDialogAvailable:
    """AC-2/3/4: GET /available 基础行为"""

    async def test_get_available_returns_array(self, ds_client):
        """AC-2: 有效 Token → 200, data.dialogs 是数组"""
        c, bearer = ds_client["client"], ds_client["bearer"]
        r = await c.get(
            "/api/v1/dialogs/available",
            headers={"Authorization": f"Bearer {bearer}"},
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        body = r.json()
        assert body["success"] is True
        dialogs = body["data"]["dialogs"]
        assert isinstance(dialogs, list)
        assert body["data"]["total"] == len(dialogs)
        meta = body["meta"]
        assert "cached" in meta
        assert "cache_ttl_sec" in meta
        assert meta["cache_ttl_sec"] == 120

    async def test_available_second_call_cached(self, ds_client):
        """AC-3: 连续两次调用，第二次 meta.cached=true"""
        c, bearer = ds_client["client"], ds_client["bearer"]
        headers = {"Authorization": f"Bearer {bearer}"}

        # 第一次（清洁缓存），强制刷新
        await c.get("/api/v1/dialogs/available?refresh=true", headers=headers)
        # 第二次（命中缓存）
        r2 = await c.get("/api/v1/dialogs/available", headers=headers)
        assert r2.status_code == 200
        body = r2.json()
        assert body["meta"]["cached"] is True, "第二次调用应命中缓存"

    async def test_available_refresh_bypasses_cache(self, ds_client):
        """AC-4: refresh=true 不从缓存取"""
        c, bearer = ds_client["client"], ds_client["bearer"]
        headers = {"Authorization": f"Bearer {bearer}"}

        # 先调用一次，建立缓存
        await c.get("/api/v1/dialogs/available", headers=headers)
        # 带 refresh=true 调用
        r = await c.get("/api/v1/dialogs/available?refresh=true", headers=headers)
        assert r.status_code == 200
        body = r.json()
        # refresh=true 必须 cached=false
        assert body["meta"]["cached"] is False, "refresh=true 应绕过缓存"


# ══════════════════════════════════════════════════════════════════════════
# GET /synced
# ══════════════════════════════════════════════════════════════════════════


@requires_meili
class TestDialogSynced:
    """T-P0-DS-04: GET /synced"""

    async def test_synced_returns_array(self, ds_client):
        """首次（未同步任何 dialog），synced 应返回空数组"""
        c, bearer = ds_client["client"], ds_client["bearer"]
        r = await c.get(
            "/api/v1/dialogs/synced",
            headers={"Authorization": f"Bearer {bearer}"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert isinstance(body["data"]["dialogs"], list)
        assert "total" in body["data"]

    async def test_synced_shows_synced_dialog(self, ds_client):
        """POST /sync 后，synced 应包含刚同步的 dialog"""
        c, bearer = ds_client["client"], ds_client["bearer"]
        headers = {"Authorization": f"Bearer {bearer}"}

        # 先同步一个 dialog
        r_sync = await c.post(
            "/api/v1/dialogs/sync",
            json={"dialog_ids": [-100111]},
            headers=headers,
        )
        assert r_sync.status_code == 200

        # 再查 synced
        r = await c.get("/api/v1/dialogs/synced", headers=headers)
        assert r.status_code == 200
        dialogs = r.json()["data"]["dialogs"]
        ids = [d["id"] for d in dialogs]
        assert -100111 in ids, f"Expected -100111 in synced dialogs, got {ids}"
        # 验证字段完整
        matched = next(d for d in dialogs if d["id"] == -100111)
        assert "sync_state" in matched
        assert "updated_at" in matched
        assert "is_syncing" in matched


# ══════════════════════════════════════════════════════════════════════════
# AC-5: POST /sync
# ══════════════════════════════════════════════════════════════════════════


@requires_meili
class TestDialogPostSync:
    """AC-5: POST /sync - accepted/ignored/not_found"""

    async def test_sync_accepted_ignored_not_found(self, ds_client):
        """AC-5: 包含有效、已同步、不存在 id → 三个列表"""
        c, bearer = ds_client["client"], ds_client["bearer"]
        headers = {"Authorization": f"Bearer {bearer}"}

        # 先同步 -100111，使其变为"已同步"
        await c.post(
            "/api/v1/dialogs/sync",
            json={"dialog_ids": [-100111]},
            headers=headers,
        )

        # 再次 POST：
        #   -100111 已同步 → ignored
        #   -100222 未同步 → accepted
        #   -999999 不存在 → not_found
        r = await c.post(
            "/api/v1/dialogs/sync",
            json={"dialog_ids": [-100111, -100222, -999999]},
            headers=headers,
        )
        assert r.status_code == 200, f"Expected 200: {r.text}"
        body = r.json()
        assert body["success"] is True
        data = body["data"]
        assert -100222 in data["accepted"], f"expected -100222 in accepted: {data}"
        assert -100111 in data["ignored"], f"expected -100111 in ignored: {data}"
        assert -999999 in data["not_found"], f"expected -999999 in not_found: {data}"

    async def test_sync_idempotent(self, ds_client):
        """AC-5（幂等）: 重复 POST /sync 不产生重复记录"""
        c, bearer = ds_client["client"], ds_client["bearer"]
        headers = {"Authorization": f"Bearer {bearer}"}

        # 第一次同步
        await c.post("/api/v1/dialogs/sync", json={"dialog_ids": [-100222]}, headers=headers)
        # 第二次同步同一个 id
        r2 = await c.post("/api/v1/dialogs/sync", json={"dialog_ids": [-100222]}, headers=headers)
        assert r2.status_code == 200
        data = r2.json()["data"]
        assert -100222 in data["ignored"], "重复同步应出现在 ignored"
        assert -100222 not in data["accepted"], "重复同步不应出现在 accepted"

    async def test_sync_empty_list_422(self, ds_client):
        """AC-8: dialog_ids=[] → 422"""
        c, bearer = ds_client["client"], ds_client["bearer"]
        r = await c.post(
            "/api/v1/dialogs/sync",
            json={"dialog_ids": []},
            headers={"Authorization": f"Bearer {bearer}"},
        )
        assert r.status_code == 422, f"Expected 422, got {r.status_code}: {r.text}"

    async def test_sync_over_limit_422(self, ds_client):
        """AC-9: dialog_ids 超过 200 → 422"""
        c, bearer = ds_client["client"], ds_client["bearer"]
        r = await c.post(
            "/api/v1/dialogs/sync",
            json={"dialog_ids": list(range(201))},
            headers={"Authorization": f"Bearer {bearer}"},
        )
        assert r.status_code == 422, f"Expected 422, got {r.status_code}: {r.text}"

    async def test_sync_invalidates_available_cache(self, ds_client):
        """POST /sync 后，available 缓存应失效（下次调用 cached=false）"""
        c, bearer = ds_client["client"], ds_client["bearer"]
        headers = {"Authorization": f"Bearer {bearer}"}

        # 建立缓存
        await c.get("/api/v1/dialogs/available", headers=headers)
        # POST /sync 应致使缓存失效
        await c.post("/api/v1/dialogs/sync", json={"dialog_ids": [-100222]}, headers=headers)
        # 下次获取应 cached=false（重新从 TG 获取）
        r = await c.get("/api/v1/dialogs/available", headers=headers)
        assert r.status_code == 200
        # 在缓存被清除后，第一次调用必须是 cached=false
        assert r.json()["meta"]["cached"] is False


# ══════════════════════════════════════════════════════════════════════════
# AC-6: PATCH /sync-state
# ══════════════════════════════════════════════════════════════════════════


@requires_meili
class TestDialogPatchSyncState:
    """AC-6: PATCH /{dialog_id}/sync-state"""

    async def _ensure_synced(self, c: httpx.AsyncClient, bearer: str, dialog_id: int) -> None:
        """前置：确保 dialog 已同步"""
        r = await c.post(
            "/api/v1/dialogs/sync",
            json={"dialog_ids": [dialog_id]},
            headers={"Authorization": f"Bearer {bearer}"},
        )
        assert r.status_code == 200

    async def test_patch_sync_state_active_to_paused(self, ds_client):
        """AC-6: 将已同步 dialog 状态改为 paused → 返回更新后状态"""
        c, bearer = ds_client["client"], ds_client["bearer"]
        headers = {"Authorization": f"Bearer {bearer}"}

        await self._ensure_synced(c, bearer, -100111)

        r = await c.patch(
            "/api/v1/dialogs/-100111/sync-state",
            json={"sync_state": "paused"},
            headers=headers,
        )
        assert r.status_code == 200, f"Expected 200: {r.text}"
        body = r.json()
        assert body["success"] is True
        assert body["data"]["sync_state"] == "paused"
        assert body["data"]["id"] == -100111

    async def test_patch_sync_state_paused_to_active(self, ds_client):
        """AC-6: paused → active"""
        c, bearer = ds_client["client"], ds_client["bearer"]
        headers = {"Authorization": f"Bearer {bearer}"}

        await self._ensure_synced(c, bearer, -100111)
        # 先暂停
        await c.patch(
            "/api/v1/dialogs/-100111/sync-state",
            json={"sync_state": "paused"},
            headers=headers,
        )
        # 再激活
        r = await c.patch(
            "/api/v1/dialogs/-100111/sync-state",
            json={"sync_state": "active"},
            headers=headers,
        )
        assert r.status_code == 200
        assert r.json()["data"]["sync_state"] == "active"

    async def test_patch_sync_state_not_synced_404(self, ds_client):
        """AC-6: 未同步 dialog → 404"""
        c, bearer = ds_client["client"], ds_client["bearer"]
        r = await c.patch(
            "/api/v1/dialogs/-999888/sync-state",
            json={"sync_state": "paused"},
            headers={"Authorization": f"Bearer {bearer}"},
        )
        assert r.status_code == 404, f"Expected 404: {r.text}"


# ══════════════════════════════════════════════════════════════════════════
# AC-7: DELETE /sync
# ══════════════════════════════════════════════════════════════════════════


@requires_meili
class TestDialogDeleteSync:
    """AC-7: DELETE /{dialog_id}/sync"""

    async def _ensure_synced(self, c: httpx.AsyncClient, bearer: str, dialog_id: int) -> None:
        r = await c.post(
            "/api/v1/dialogs/sync",
            json={"dialog_ids": [dialog_id]},
            headers={"Authorization": f"Bearer {bearer}"},
        )
        assert r.status_code == 200

    async def test_delete_sync_purge_true(self, ds_client):
        """AC-7: DELETE 默认 purge_index=true → removed=True，synced 不再出现"""
        c, bearer = ds_client["client"], ds_client["bearer"]
        headers = {"Authorization": f"Bearer {bearer}"}

        await self._ensure_synced(c, bearer, -100111)

        r = await c.delete("/api/v1/dialogs/-100111/sync", headers=headers)
        assert r.status_code == 200, f"Expected 200: {r.text}"
        body = r.json()
        assert body["success"] is True
        assert body["data"]["removed"] is True
        assert body["data"]["purge_index"] is True

        # 验证 synced 不再出现
        r_synced = await c.get("/api/v1/dialogs/synced", headers=headers)
        ids = [d["id"] for d in r_synced.json()["data"]["dialogs"]]
        assert -100111 not in ids, f"-100111 still in synced after delete: {ids}"

    async def test_delete_sync_purge_true_removes_meili_documents(self, ds_client):
        """AC-7: 删除同步后，Meili 中该 chat.id 文档应被清理"""
        c, bearer = ds_client["client"], ds_client["bearer"]
        app = ds_client["app"]
        headers = {"Authorization": f"Bearer {bearer}"}
        meili = app.state.app_state.meili_client
        index_name = "telegram"
        target_chat_id = -100111
        control_chat_id = -100222
        control_doc_id = None

        # 确保索引存在（若已存在则幂等）
        meili.create_index(index_name=index_name, primary_key="id")
        idx = meili.client.index(index_name)

        # 先清理目标 chat，避免历史脏数据干扰断言
        _delete_docs_by_chat_id(meili, idx, target_chat_id)

        now = int(time.time() * 1000)
        docs = [
            {
                "id": now,
                "text": "purge_target_1",
                "chat": {"id": target_chat_id, "type": "group"},
                "from_user": {"id": 1},
            },
            {
                "id": now + 1,
                "text": "purge_target_2",
                "chat": {"id": target_chat_id, "type": "group"},
                "from_user": {"id": 1},
            },
            {
                "id": now + 2,
                "text": "purge_control",
                "chat": {"id": control_chat_id, "type": "channel"},
                "from_user": {"id": 2},
            },
        ]
        control_doc_id = now + 2
        _wait_task(meili, idx.add_documents(docs))

        before_target = idx.search("", {"filter": f"chat.id = {target_chat_id}", "limit": 50})
        before_control = idx.search("", {"filter": f"chat.id = {control_chat_id}", "limit": 50})
        assert before_target.get("estimatedTotalHits", 0) >= 2
        assert before_control.get("estimatedTotalHits", 0) >= 1

        await self._ensure_synced(c, bearer, target_chat_id)
        r = await c.delete(f"/api/v1/dialogs/{target_chat_id}/sync", headers=headers)
        assert r.status_code == 200, f"Expected 200: {r.text}"
        assert r.json()["data"]["purge_index"] is True

        # delete_documents_by_filter 是异步任务，轮询确认最终一致性
        deadline = time.time() + 6.0
        while True:
            after_target = idx.search("", {"filter": f"chat.id = {target_chat_id}", "limit": 50})
            if after_target.get("estimatedTotalHits", 0) == 0:
                break
            if time.time() > deadline:
                pytest.fail(f"chat.id={target_chat_id} documents not purged in time: {after_target}")
            await asyncio.sleep(0.2)

        # 控制组 chat 文档应保留，证明是按 chat.id 精准删除
        after_control = idx.search("", {"filter": f"chat.id = {control_chat_id}", "limit": 50})
        assert after_control.get("estimatedTotalHits", 0) >= 1

        if control_doc_id is not None:
            _wait_task(meili, idx.delete_documents([control_doc_id]))

    async def test_delete_sync_purge_false(self, ds_client):
        """AC-7: purge_index=false → removed=True，仅删同步配置"""
        c, bearer = ds_client["client"], ds_client["bearer"]
        headers = {"Authorization": f"Bearer {bearer}"}

        await self._ensure_synced(c, bearer, -100222)

        r = await c.delete("/api/v1/dialogs/-100222/sync?purge_index=false", headers=headers)
        assert r.status_code == 200, f"Expected 200: {r.text}"
        body = r.json()
        assert body["success"] is True
        assert body["data"]["removed"] is True
        assert body["data"]["purge_index"] is False

        # 验证 synced 不再出现
        r_synced = await c.get("/api/v1/dialogs/synced", headers=headers)
        ids = [d["id"] for d in r_synced.json()["data"]["dialogs"]]
        assert -100222 not in ids

    async def test_delete_sync_not_synced_404(self, ds_client):
        """DELETE 未同步的 dialog → 404"""
        c, bearer = ds_client["client"], ds_client["bearer"]
        r = await c.delete(
            "/api/v1/dialogs/-999777/sync",
            headers={"Authorization": f"Bearer {bearer}"},
        )
        assert r.status_code == 404, f"Expected 404: {r.text}"

    async def test_delete_invalidates_available_cache(self, ds_client):
        """DELETE /sync 后缓存应失效"""
        c, bearer = ds_client["client"], ds_client["bearer"]
        headers = {"Authorization": f"Bearer {bearer}"}

        # 先建立 available 缓存
        await c.get("/api/v1/dialogs/available?refresh=true", headers=headers)
        await c.get("/api/v1/dialogs/available", headers=headers)  # 缓存命中

        # 先同步一个，之后删除
        await self._ensure_synced(c, bearer, -100111)
        await c.delete("/api/v1/dialogs/-100111/sync", headers=headers)

        # 删除后，第一次访问 available 必须 cached=false
        r = await c.get("/api/v1/dialogs/available", headers=headers)
        assert r.json()["meta"]["cached"] is False


# ══════════════════════════════════════════════════════════════════════════
# Fix-1: PATCH 无效 sync_state → 422（API 层）
# ══════════════════════════════════════════════════════════════════════════


@requires_meili
class TestDialogPatchInvalidState:
    """Fix-1: PATCH /{dialog_id}/sync-state 无效枚举值 → 422"""

    async def test_patch_invalid_sync_state_api_422(self, ds_client):
        """PATCH 传入 sync_state='stopped' → 422"""
        c, bearer = ds_client["client"], ds_client["bearer"]
        headers = {"Authorization": f"Bearer {bearer}"}

        # 先同步一个 dialog
        await c.post("/api/v1/dialogs/sync", json={"dialog_ids": [-100111]}, headers=headers)

        r = await c.patch(
            "/api/v1/dialogs/-100111/sync-state",
            json={"sync_state": "stopped"},
            headers=headers,
        )
        assert r.status_code == 422, f"Expected 422 for invalid state, got {r.status_code}: {r.text}"

    async def test_sync_invalid_default_state_api_422(self, ds_client):
        """POST /sync 传 default_sync_state='invalid' → 422"""
        c, bearer = ds_client["client"], ds_client["bearer"]
        headers = {"Authorization": f"Bearer {bearer}"}

        r = await c.post(
            "/api/v1/dialogs/sync",
            json={"dialog_ids": [-100111], "default_sync_state": "invalid"},
            headers=headers,
        )
        assert r.status_code == 422, f"Expected 422, got {r.status_code}: {r.text}"


# ══════════════════════════════════════════════════════════════════════════
# Fix-2: Telegram 异常 → 503
# ══════════════════════════════════════════════════════════════════════════


@requires_meili
class TestDialogTelegramError:
    """Fix-2: Telegram 拉取失败时返回 503，而非静默 200"""

    async def test_available_telegram_error_503(self, ds_client):
        """GET /available 时 iter_dialogs 抛异常 → 503"""
        c, bearer = ds_client["client"], ds_client["bearer"]
        app = ds_client["app"]
        headers = {"Authorization": f"Bearer {bearer}"}

        # 强制缓存失效，让下次请求触发 Telegram 拉取
        cache = app.state.app_state.dialog_available_cache
        cache.invalidate()

        # 让 iter_dialogs 抛异常
        async def _failing_iter():
            raise ConnectionError("Telegram 连接中断")
            # 需要一个 yield 使其成为 async generator
            yield  # pragma: no cover

        original_iter = app.state.app_state.telegram_client.iter_dialogs
        app.state.app_state.telegram_client.iter_dialogs = _failing_iter

        try:
            r = await c.get("/api/v1/dialogs/available?refresh=true", headers=headers)
            assert r.status_code == 503, f"Expected 503, got {r.status_code}: {r.text}"
            assert "TELEGRAM_UNAVAILABLE" in r.text
        finally:
            app.state.app_state.telegram_client.iter_dialogs = original_iter

    async def test_sync_telegram_error_503(self, ds_client):
        """POST /sync 时 Telegram 不可用 → 503（而非 200+全部 not_found）"""
        c, bearer = ds_client["client"], ds_client["bearer"]
        app = ds_client["app"]
        headers = {"Authorization": f"Bearer {bearer}"}

        # 强制缓存失效
        cache = app.state.app_state.dialog_available_cache
        cache.invalidate()

        async def _failing_iter():
            raise ConnectionError("Telegram 网络超时")
            yield  # pragma: no cover

        original_iter = app.state.app_state.telegram_client.iter_dialogs
        app.state.app_state.telegram_client.iter_dialogs = _failing_iter

        try:
            r = await c.post(
                "/api/v1/dialogs/sync",
                json={"dialog_ids": [-100111]},
                headers=headers,
            )
            assert r.status_code == 503, f"Expected 503, got {r.status_code}: {r.text}"
        finally:
            app.state.app_state.telegram_client.iter_dialogs = original_iter


# ══════════════════════════════════════════════════════════════════════════
# Fix-5: limit 参数
# ══════════════════════════════════════════════════════════════════════════


@requires_meili
class TestDialogAvailableLimit:
    """Fix-5: GET /available?limit=N 截断返回"""

    async def test_available_limit_param(self, ds_client):
        """limit=1 → dialogs 长度 ≤ 1，total 保持为完整total"""
        c, bearer = ds_client["client"], ds_client["bearer"]
        headers = {"Authorization": f"Bearer {bearer}"}

        # 先获取全量
        r_full = await c.get("/api/v1/dialogs/available?refresh=true", headers=headers)
        assert r_full.status_code == 200
        full_total = r_full.json()["data"]["total"]

        # limit=1
        r = await c.get("/api/v1/dialogs/available?limit=1", headers=headers)
        assert r.status_code == 200
        body = r.json()
        assert len(body["data"]["dialogs"]) <= 1
        # total 应为完整的可用数量，不受 limit 影响
        assert body["data"]["total"] == full_total
