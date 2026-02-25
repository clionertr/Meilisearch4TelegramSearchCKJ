"""E2E integration tests for P1 ObservabilityService."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from unittest import mock

import pytest
from fastapi.testclient import TestClient

from tests.helpers.requirements import check_meili_available, load_meili_env_from_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

os.environ.setdefault("SKIP_CONFIG_VALIDATION", "true")
load_meili_env_from_dotenv()

# Keep settings module aligned with potentially loaded real env values.
from tg_search.config import settings as _settings  # noqa: E402

_settings.MEILI_PASS = os.environ.get("MEILI_MASTER_KEY", "")
_settings.MEILI_HOST = os.environ.get("MEILI_HOST", "http://localhost:7700")

from tg_search.api.app import build_app  # noqa: E402

_MEILI_HOST = os.environ.get("MEILI_HOST", "http://localhost:7700")
_MEILI_KEY = os.environ.get("MEILI_MASTER_KEY", "")

pytestmark = [pytest.mark.integration, pytest.mark.e2e, pytest.mark.meili]
_MEILI_SKIP_REASON = check_meili_available(_MEILI_HOST, _MEILI_KEY, require_auth=True)
requires_meili = pytest.mark.skipif(
    _MEILI_SKIP_REASON is not None,
    reason=_MEILI_SKIP_REASON or "",
)


class _NoopTelegramClient:
    """Tiny TelegramClient stub to avoid network usage in BotHandler constructor."""

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class _FakeBotEvent:
    def __init__(self, sender_id: int = 1):
        self.sender_id = sender_id
        self.replies: list[str] = []

    async def reply(self, text: str):
        self.replies.append(text)

    async def respond(self, text: str):
        self.replies.append(text)


@pytest.fixture
def client() -> TestClient:
    """Real-lifespan TestClient with auth disabled for route/WebSocket assertions."""
    with (
        mock.patch("tg_search.api.deps.API_KEY", None),
        mock.patch("tg_search.config.settings.API_KEY", None),
    ):
        app = build_app()
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


def _build_bot_handler_from_app_state(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    from tg_search.core import bot as bot_module

    monkeypatch.setattr(bot_module, "TelegramClient", _NoopTelegramClient)
    monkeypatch.setattr(bot_module, "OWNER_IDS", [])

    app_state = client.app.state.app_state
    assert app_state.service_container is not None

    return bot_module.BotHandler(main=lambda: None, services=app_state.service_container)


def _parse_ping_telegram_doc_count(text: str) -> int:
    match = re.search(r"Index telegram has (\d+) documents", text)
    assert match is not None, f"cannot parse telegram doc count from ping text: {text}"
    return int(match.group(1))


@requires_meili
class TestObservabilityServiceE2E:
    def test_status_and_ping_share_document_count_snapshot(self, client: TestClient, monkeypatch: pytest.MonkeyPatch):
        """AC-1: /status 与 Bot /ping 的核心文档统计保持一致。"""
        response = client.get("/api/v1/status")
        assert response.status_code == 200, response.text
        status_body = response.json()
        indexed_messages = int(status_body["data"]["indexed_messages"])

        bot_handler = _build_bot_handler_from_app_state(client, monkeypatch)
        event = _FakeBotEvent()

        import asyncio

        asyncio.run(bot_handler.ping_handler(event))
        assert event.replies, "bot /ping should produce one reply"
        ping_doc_count = _parse_ping_telegram_doc_count(event.replies[-1])

        assert ping_doc_count == indexed_messages

    def test_meili_outage_returns_degraded_results_without_500(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """AC-2: Meili 不可用时状态类接口降级可用，Bot /ping 返回统一不可用语义。"""
        app_state = client.app.state.app_state

        def _raise_unavailable(*_args, **_kwargs):
            raise RuntimeError("simulated_meili_outage")

        monkeypatch.setattr(app_state.meili_client, "get_index_stats", _raise_unavailable)
        monkeypatch.setattr(app_state.meili_client.client, "get_all_stats", _raise_unavailable)

        status_resp = client.get("/api/v1/status")
        assert status_resp.status_code == 200, status_resp.text
        assert status_resp.json()["data"]["meili_connected"] is False

        search_resp = client.get("/api/v1/search/stats")
        assert search_resp.status_code == 200, search_resp.text
        assert int(search_resp.json()["data"]["total_documents"]) == 0

        storage_resp = client.get("/api/v1/storage/stats")
        assert storage_resp.status_code == 200, storage_resp.text
        storage_data = storage_resp.json()["data"]
        assert storage_data["index_bytes"] is None

        bot_handler = _build_bot_handler_from_app_state(client, monkeypatch)
        event = _FakeBotEvent()

        import asyncio

        asyncio.run(bot_handler.ping_handler(event))
        assert event.replies, "bot /ping should degrade instead of raising"
        assert "服务不可用" in event.replies[-1]

    def test_status_progress_matches_websocket_progress_event(self, client: TestClient):
        """AC-3: /status/progress 的 active_count 与 WebSocket progress 事件一致。"""
        app_state = client.app.state.app_state
        dialog_id = 778899001

        with client.websocket_connect("/api/v1/ws/status") as ws:
            connected = ws.receive_json()
            assert connected["type"] == "connected"

            client.portal.call(
                app_state.progress_registry.update_progress,
                dialog_id,
                "obs-e2e-dialog",
                8,
                20,
                "downloading",
            )

            event = ws.receive_json()
            assert event["type"] == "progress"
            assert int(event["data"]["dialog_id"]) == dialog_id
            assert event["data"]["status"] == "downloading"

        progress_resp = client.get("/api/v1/status/progress")
        assert progress_resp.status_code == 200, progress_resp.text
        progress_data = progress_resp.json()["data"]
        assert int(progress_data["count"]) == 1
        assert str(dialog_id) in progress_data["progress"]
        assert progress_data["progress"][str(dialog_id)]["status"] == "downloading"

    def test_api_only_mode_reports_telegram_disconnected(self, client: TestClient):
        """AC-4: API-only 场景下 status 可用且 telegram_connected=false。"""
        app_state = client.app.state.app_state
        app_state.api_only = True
        app_state.telegram_client = None

        response = client.get("/api/v1/status")
        assert response.status_code == 200, response.text

        body = response.json()
        assert body["data"]["telegram_connected"] is False

    def test_status_memory_degradation_has_diagnostic_note(self, client: TestClient, monkeypatch: pytest.MonkeyPatch):
        """AC-5: 内存统计不可获取时，状态快照包含可诊断说明。"""
        app_state = client.app.state.app_state
        assert app_state.service_container is not None
        assert hasattr(app_state.service_container, "observability_service")

        service = app_state.service_container.observability_service

        def _fake_memory_probe():
            return 0.0, ["memory metrics unavailable (simulated)"]

        monkeypatch.setattr(service, "_read_memory_usage_mb", _fake_memory_probe)

        response = client.get("/api/v1/status")
        assert response.status_code == 200, response.text
        data = response.json()["data"]

        assert "notes" in data
        assert any("memory" in str(note).lower() for note in data["notes"])
