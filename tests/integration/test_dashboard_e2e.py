"""
E2E 集成测试：P2 Dashboard API

连接真实运行中的 API 服务与真实 MeiliSearch，
验证 dashboard activity / brief 的业务契约。
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
import meilisearch
import pytest

# 确保项目根目录可导入
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# 集成测试门控
if os.getenv("RUN_INTEGRATION_TESTS", "").lower() not in ("1", "true", "yes"):
    pytest.skip(
        "Dashboard E2E tests disabled. Set RUN_INTEGRATION_TESTS=true to enable.",
        allow_module_level=True,
    )

from tests.integration.config import TEST_API_BASE_URL, TEST_MEILI_HOST, TEST_MEILI_KEY  # noqa: E402
from tests.integration.conftest import switchable  # noqa: E402

pytestmark = [pytest.mark.integration, pytest.mark.e2e, pytest.mark.meili]

_TEST_BEARER_TOKEN = os.getenv("TEST_BEARER_TOKEN", "")


def _auth_headers() -> dict[str, str]:
    if not _TEST_BEARER_TOKEN:
        return {}
    return {"Authorization": f"Bearer {_TEST_BEARER_TOKEN}"}


def _has_token() -> bool:
    return bool(_TEST_BEARER_TOKEN)


def _extract_task_uid(task: Any) -> int | None:
    """兼容 Meili SDK 不同返回类型，提取 task uid。"""
    if task is None:
        return None
    if isinstance(task, dict):
        for key in ("taskUid", "uid", "task_uid"):
            value = task.get(key)
            if isinstance(value, int):
                return value
        return None

    for key in ("task_uid", "uid", "taskUid"):
        value = getattr(task, key, None)
        if isinstance(value, int):
            return value
    return None


def _wait_for_task(meili_client: meilisearch.Client, task_uid: int | None) -> None:
    """等待 Meili 异步任务完成。"""
    if task_uid is None:
        time.sleep(0.8)
        return

    # 兼容不同 SDK 版本
    wait_fn = getattr(meili_client, "wait_for_task", None)
    if callable(wait_fn):
        try:
            wait_fn(task_uid, timeout_in_ms=12_000, interval_in_ms=80)
            return
        except TypeError:
            wait_fn(task_uid)
            return
        except Exception:
            pass

    time.sleep(0.8)


@pytest.fixture(scope="module")
def dashboard_seed_context() -> dict[str, Any]:
    """
    注入一批“最近 24 小时”测试消息，保证 dashboard 聚合可观测、可重复。
    """
    marker = f"p2dash_{int(time.time())}"
    chat_id = -1009000000000 - int(time.time()) % 100000
    chat_title = f"__dashboard_e2e_{marker}"
    now = datetime.now(timezone.utc)

    docs: list[dict[str, Any]] = []
    doc_ids: list[str] = []
    seed_count = 140
    for i in range(seed_count):
        doc_id = f"{chat_id}_{marker}_{i}"
        doc_ids.append(doc_id)
        dt = (now - timedelta(minutes=i % 90, seconds=i)).replace(microsecond=0)
        docs.append(
            {
                "id": doc_id,
                "chat": {"id": chat_id, "type": "group", "title": chat_title},
                "date": dt.isoformat().replace("+00:00", "Z"),
                "text": (f"{marker} meilisearch telegram api dashboard keyword{(i % 5) + 1} sample message {i}"),
                "from_user": {"id": 1000 + i, "username": f"dash_user_{i}"},
                "reactions": {},
                "reactions_scores": 0.0,
                "text_len": 0,
            }
        )

    meili_client = meilisearch.Client(TEST_MEILI_HOST, TEST_MEILI_KEY)
    index = meili_client.index("telegram")
    add_task = index.add_documents(docs)
    _wait_for_task(meili_client, _extract_task_uid(add_task))
    time.sleep(0.3)

    yield {
        "marker": marker,
        "chat_id": chat_id,
        "chat_title": chat_title,
        "seed_count": seed_count,
        "doc_ids": doc_ids,
    }

    try:
        del_task = index.delete_documents(doc_ids)
        _wait_for_task(meili_client, _extract_task_uid(del_task))
    except Exception:
        # best-effort cleanup
        pass


class TestDashboardE2E:
    """Dashboard E2E 测试"""

    @switchable("dashboard_auth")
    def test_01_no_bearer_token_returns_401(self):
        """AC-1: 未携带 Bearer Token 访问 dashboard 端点应返回 401"""
        with httpx.Client(base_url=TEST_API_BASE_URL, timeout=20.0) as client:
            r1 = client.get("/api/v1/dashboard/activity", params={"window_hours": 24, "limit": 20})
            r2 = client.get("/api/v1/dashboard/brief", params={"window_hours": 24})
        assert r1.status_code == 401
        assert r2.status_code == 401

    @switchable("dashboard_activity")
    def test_02_activity_returns_items_schema(
        self,
        api_client: httpx.Client,
        dashboard_seed_context: dict[str, Any],
    ):
        """AC-2: GET /dashboard/activity 返回 200 且 data.items 满足 schema"""
        if not _has_token():
            pytest.skip("TEST_BEARER_TOKEN 未设置，跳过需要 Bearer 的测试")

        resp = api_client.get(
            "/api/v1/dashboard/activity",
            params={"window_hours": 24, "limit": 20},
            headers=_auth_headers(),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["success"] is True

        data = body["data"]
        assert isinstance(data["items"], list)
        assert "sampled" in data
        assert "sample_size" in data

        seeded_item = next(
            (it for it in data["items"] if it.get("chat_id") == dashboard_seed_context["chat_id"]),
            None,
        )
        assert seeded_item is not None, "seeded chat not found in activity result"

        required_fields = (
            "chat_id",
            "chat_title",
            "chat_type",
            "message_count",
            "latest_message_time",
            "top_keywords",
            "sample_message",
        )
        for field in required_fields:
            assert field in seeded_item

        assert seeded_item["chat_title"] == dashboard_seed_context["chat_title"]
        assert seeded_item["chat_type"] in ("group", "channel", "private", "unknown")
        assert isinstance(seeded_item["message_count"], int)
        assert seeded_item["message_count"] >= dashboard_seed_context["seed_count"]
        assert isinstance(seeded_item["top_keywords"], list)
        assert len(seeded_item["top_keywords"]) <= 3

    @switchable("dashboard_activity")
    def test_03_activity_limit_out_of_range_returns_422(self, api_client: httpx.Client):
        """AC-3: limit>100 返回 422"""
        if not _has_token():
            pytest.skip("TEST_BEARER_TOKEN 未设置，跳过需要 Bearer 的测试")

        resp = api_client.get(
            "/api/v1/dashboard/activity",
            params={"window_hours": 24, "limit": 101},
            headers=_auth_headers(),
        )
        assert resp.status_code == 422

    @switchable("dashboard_brief")
    def test_04_brief_returns_template_fields(self, api_client: httpx.Client):
        """AC-4: GET /dashboard/brief 返回 summary/template_id/reason"""
        if not _has_token():
            pytest.skip("TEST_BEARER_TOKEN 未设置，跳过需要 Bearer 的测试")

        resp = api_client.get(
            "/api/v1/dashboard/brief",
            params={"window_hours": 24},
            headers=_auth_headers(),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["success"] is True
        data = body["data"]

        assert "summary" in data
        assert "template_id" in data
        assert "reason" in data
        assert "source_count" in data
        assert data["template_id"] == "brief.v1"

    @switchable("dashboard_brief")
    def test_05_brief_returns_no_enough_data_when_threshold_not_met(self, api_client: httpx.Client):
        """AC-5: 消息量低于 min_messages 时 summary 为空且 reason=NO_ENOUGH_DATA"""
        if not _has_token():
            pytest.skip("TEST_BEARER_TOKEN 未设置，跳过需要 Bearer 的测试")

        resp = api_client.get(
            "/api/v1/dashboard/brief",
            params={"window_hours": 24, "min_messages": 999999},
            headers=_auth_headers(),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["summary"] == ""
        assert data["reason"] == "NO_ENOUGH_DATA"
