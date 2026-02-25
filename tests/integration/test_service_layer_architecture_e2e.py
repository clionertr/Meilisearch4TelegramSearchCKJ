"""E2E integration tests for P0 Service Layer Architecture closure."""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from collections.abc import Awaitable, Callable

import httpx
import pytest

from tests.helpers.requirements import check_meili_available, load_meili_env_from_dotenv
from tg_search.core.meilisearch import MeiliSearchClient
from tg_search.services.container import ServiceContainer, build_service_container
from tg_search.services.contracts import PolicyConfig
from tg_search.utils.permissions import is_allowed

os.environ.setdefault("SKIP_CONFIG_VALIDATION", "true")
load_meili_env_from_dotenv()

_MEILI_HOST = os.environ.get("MEILI_HOST", "http://localhost:7700")
_MEILI_KEY = os.environ.get("MEILI_MASTER_KEY", "")
_MEILI_SKIP_REASON = check_meili_available(_MEILI_HOST, _MEILI_KEY, require_auth=True)

pytestmark = [pytest.mark.integration, pytest.mark.e2e, pytest.mark.meili]
requires_meili = pytest.mark.skipif(
    _MEILI_SKIP_REASON is not None,
    reason=_MEILI_SKIP_REASON or "",
)


class _RuntimePolicyCache:
    """Runtime consumer with large TTL to verify push-based immediate consistency."""

    def __init__(
        self,
        loader: Callable[[], Awaitable[tuple[list[int], list[int]]]],
        *,
        ttl_sec: int,
    ) -> None:
        self._loader = loader
        self._ttl_sec = max(ttl_sec, 1)
        self._loaded_at = 0.0
        self.white_list: list[int] = []
        self.black_list: list[int] = []

    async def refresh(self, force: bool = False) -> None:
        if (not force) and (time.monotonic() - self._loaded_at < self._ttl_sec):
            return
        white_list, black_list = await self._loader()
        self.white_list = list(white_list)
        self.black_list = list(black_list)
        self._loaded_at = time.monotonic()

    async def on_policy_changed(self, policy: PolicyConfig) -> None:
        self.white_list = list(policy.white_list)
        self.black_list = list(policy.black_list)
        self._loaded_at = time.monotonic()

    async def is_allowed(self, peer_id: int) -> bool:
        await self.refresh(force=False)
        return is_allowed(peer_id, self.white_list, self.black_list)


@pytest.fixture
def service_container() -> ServiceContainer:
    """Build a real service container backed by a dedicated test index."""
    meili = MeiliSearchClient(_MEILI_HOST, _MEILI_KEY, auto_create_index=False)
    index_name = f"system_config_sla_e2e_{uuid.uuid4().hex[:8]}"
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
    """ASGI client with lifespan and injected shared service container."""
    from tg_search.api.app import build_app, lifespan

    app = build_app()
    async with lifespan(app):
        state = app.state.app_state
        state.service_container = service_container
        state.meili_client = service_container.meili_client
        state.config_store = service_container.config_store
        state.config_policy_service = service_container.config_policy_service
        state.search_service = service_container.search_service
        state.api_only = False

        headers: dict[str, str] = {}
        api_key = os.environ.get("API_KEY")
        if api_key:
            headers["X-API-Key"] = api_key

        transport = httpx.ASGITransport(app=app, raise_app_exceptions=True)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers=headers,
        ) as client:
            yield client, app


@requires_meili
@pytest.mark.asyncio
async def test_control_start_passes_shared_service_container(api_client, service_container: ServiceContainer, monkeypatch):
    """`/client/start` must inject the exact shared ServiceContainer into run()."""
    client, _app = api_client
    captured: dict[str, object] = {}
    started = asyncio.Event()

    async def fake_run(*, progress_registry=None, services=None):  # type: ignore[no-untyped-def]
        captured["progress_registry"] = progress_registry
        captured["services"] = services
        started.set()
        await asyncio.sleep(0)

    monkeypatch.setattr("tg_search.main.run", fake_run)

    response = await client.post("/api/v1/client/start")
    assert response.status_code == 200, response.text
    await asyncio.wait_for(started.wait(), timeout=2)

    assert captured.get("services") is service_container

    # cleanup
    await client.post("/api/v1/client/stop")


@requires_meili
@pytest.mark.asyncio
async def test_policy_change_visible_to_runtime_consumer_within_one_second(api_client, service_container: ServiceContainer):
    """
    API policy write should be visible to a runtime consumer in <1s,
    even when the consumer's own pull TTL is large.
    """
    client, _app = api_client
    policy_service = service_container.config_policy_service
    target_peer_id = 987654321

    # Ensure test target is absent first.
    await policy_service.remove_whitelist([target_peer_id], source="test")

    runtime_cache = _RuntimePolicyCache(
        loader=lambda: policy_service.get_policy_lists(refresh=False),
        ttl_sec=3600,
    )
    await runtime_cache.refresh(force=True)
    assert await runtime_cache.is_allowed(target_peer_id) is False

    # Key expectation: runtime consumer receives push notification on API write.
    policy_service.subscribe(runtime_cache.on_policy_changed)

    response = await client.post("/api/v1/config/whitelist", json={"ids": [target_peer_id]})
    assert response.status_code == 200, response.text

    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline:
        if await runtime_cache.is_allowed(target_peer_id):
            break
        await asyncio.sleep(0.02)

    assert await runtime_cache.is_allowed(target_peer_id) is True
