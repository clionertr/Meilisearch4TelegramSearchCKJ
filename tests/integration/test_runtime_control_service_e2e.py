"""E2E integration tests for unified runtime control service (P0-RCS)."""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from dataclasses import dataclass

import httpx
import pytest

from tests.helpers.requirements import check_meili_available, load_meili_env_from_dotenv
from tg_search.core.bot import BotHandler
from tg_search.core.meilisearch import MeiliSearchClient
from tg_search.services.container import ServiceContainer, build_service_container

os.environ.setdefault("SKIP_CONFIG_VALIDATION", "true")
os.environ.setdefault("DISABLE_BOT_AUTOSTART", "true")
os.environ.setdefault("DISABLE_AUTH_CLEANUP_TASK", "true")
load_meili_env_from_dotenv()

_MEILI_HOST = os.environ.get("MEILI_HOST", "http://localhost:7700")
_MEILI_KEY = os.environ.get("MEILI_MASTER_KEY", "")
_MEILI_SKIP_REASON = check_meili_available(_MEILI_HOST, _MEILI_KEY, require_auth=True)

pytestmark = [pytest.mark.integration, pytest.mark.e2e, pytest.mark.meili]
requires_meili = pytest.mark.skipif(
    _MEILI_SKIP_REASON is not None,
    reason=_MEILI_SKIP_REASON or "",
)


@dataclass
class _FakeEvent:
    sender_id: int = 1
    text: str = "/start_client"

    def __post_init__(self) -> None:
        self.replies: list[str] = []

    async def reply(self, text: str) -> None:
        self.replies.append(text)

    async def respond(self, text: str) -> None:
        self.replies.append(text)


@pytest.fixture
def service_container() -> ServiceContainer:
    meili = MeiliSearchClient(_MEILI_HOST, _MEILI_KEY, auto_create_index=False)
    index_name = f"system_config_rcs_e2e_{uuid.uuid4().hex[:8]}"
    container = build_service_container(
        meili_client=meili,
        config_index_name=index_name,
    )
    try:
        yield container
    finally:
        try:
            meili.delete_index(index_name)
        except Exception:
            pass


@pytest.fixture
async def api_client(service_container: ServiceContainer):
    from tg_search.api.app import build_app, lifespan

    app = build_app()
    async with lifespan(app):
        state = app.state.app_state
        state.service_container = service_container
        state.meili_client = service_container.meili_client
        state.config_store = service_container.config_store
        state.config_policy_service = service_container.config_policy_service
        state.runtime_control_service = service_container.runtime_control_service
        state.api_only = False
        state.runtime_control_service.set_api_only_getter(lambda: state.api_only)

        transport = httpx.ASGITransport(app=app, raise_app_exceptions=True)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            yield client, app


@requires_meili
@pytest.mark.asyncio
async def test_api_start_then_bot_start_returns_already_running(api_client, service_container, monkeypatch):
    """API start then Bot start should return `already_running` semantics."""
    client, _app = api_client

    started = asyncio.Event()

    async def fake_run(*, progress_registry=None, services=None):  # type: ignore[no-untyped-def]
        _ = progress_registry
        _ = services
        started.set()
        await asyncio.Event().wait()

    monkeypatch.setattr("tg_search.main.run", fake_run)

    response = await client.post("/api/v1/client/start")
    assert response.status_code == 200, response.text
    assert response.json()["data"]["status"] == "started"

    await asyncio.wait_for(started.wait(), timeout=1.0)

    bot = BotHandler(main=lambda: fake_run(services=service_container), services=service_container)
    event = _FakeEvent(text="/start_client")
    await bot.start_download_and_listening(event)

    assert any("already" in msg.lower() or "运行中" in msg for msg in event.replies), event.replies

    await client.post("/api/v1/client/stop")


@requires_meili
@pytest.mark.asyncio
async def test_bot_stop_then_api_status_consistent(api_client, service_container, monkeypatch):
    """Bot stop should make API status show `is_running=false`."""
    client, _app = api_client

    gate = asyncio.Event()

    async def fake_run(*, progress_registry=None, services=None):  # type: ignore[no-untyped-def]
        _ = progress_registry
        _ = services
        await gate.wait()

    monkeypatch.setattr("tg_search.main.run", fake_run)

    start_resp = await client.post("/api/v1/client/start")
    assert start_resp.status_code == 200

    bot = BotHandler(main=lambda: fake_run(services=service_container), services=service_container)
    event = _FakeEvent(text="/stop_client")
    await bot.stop_download_and_listening(event)

    status_resp = await client.get("/api/v1/client/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["data"]["is_running"] is False


@requires_meili
@pytest.mark.asyncio
async def test_concurrent_start_only_one_task_running(api_client, monkeypatch):
    """10 concurrent starts must produce exactly one running task."""
    client, _app = api_client

    start_count = 0

    async def fake_run(*, progress_registry=None, services=None):  # type: ignore[no-untyped-def]
        nonlocal start_count
        _ = progress_registry
        _ = services
        start_count += 1
        await asyncio.Event().wait()

    monkeypatch.setattr("tg_search.main.run", fake_run)

    responses = await asyncio.gather(*[client.post("/api/v1/client/start") for _ in range(10)])

    statuses = [resp.json()["data"]["status"] for resp in responses]
    assert statuses.count("started") == 1
    assert statuses.count("already_running") == 9
    assert start_count == 1

    await client.post("/api/v1/client/stop")


@requires_meili
@pytest.mark.asyncio
async def test_api_only_mode_consistent_between_api_and_bot(api_client, service_container, monkeypatch):
    """API-only mode should reject start consistently for both API and Bot entry points."""
    client, app = api_client
    app.state.app_state.api_only = True

    async def fake_run(*, progress_registry=None, services=None):  # type: ignore[no-untyped-def]
        _ = progress_registry
        _ = services
        await asyncio.Event().wait()

    monkeypatch.setattr("tg_search.main.run", fake_run)

    api_resp = await client.post("/api/v1/client/start")
    assert api_resp.status_code == 400

    bot = BotHandler(main=lambda: fake_run(services=service_container), services=service_container)
    event = _FakeEvent(text="/start_client")
    await bot.start_download_and_listening(event)

    assert any("api-only" in msg.lower() or "不可启动" in msg for msg in event.replies), event.replies


@requires_meili
@pytest.mark.asyncio
async def test_force_cancel_then_can_restart(api_client, service_container, monkeypatch):
    """After forced cancellation, runtime can start again normally."""
    client, _app = api_client

    started = 0
    entered = asyncio.Event()

    async def fake_run(*, progress_registry=None, services=None):  # type: ignore[no-untyped-def]
        nonlocal started
        _ = progress_registry
        _ = services
        started += 1
        entered.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            raise

    monkeypatch.setattr("tg_search.main.run", fake_run)

    r1 = await client.post("/api/v1/client/start")
    assert r1.status_code == 200
    assert r1.json()["data"]["status"] == "started"
    await asyncio.wait_for(entered.wait(), timeout=1.0)

    # force stop via API to emulate external cancellation path
    r_stop = await client.post("/api/v1/client/stop")
    assert r_stop.status_code == 200

    # give runtime loop a short time slice to settle
    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline:
        status = await client.get("/api/v1/client/status")
        if status.json()["data"]["is_running"] is False:
            break
        await asyncio.sleep(0.02)

    r2 = await client.post("/api/v1/client/start")
    assert r2.status_code == 200
    assert r2.json()["data"]["status"] in {"started", "already_running"}
    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline and started < 2:
        await asyncio.sleep(0.02)

    assert started >= 2
    await client.post("/api/v1/client/stop")
