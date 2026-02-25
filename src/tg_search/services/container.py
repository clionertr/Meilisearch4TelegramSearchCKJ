"""Service container for shared singleton-style service wiring."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Sequence

from tg_search.config.config_store import ConfigStore
from tg_search.config.settings import (
    MEILI_HOST,
    MEILI_PASS,
    OBS_SNAPSHOT_TIMEOUT_SEC,
    OBS_SNAPSHOT_WARN_MS,
)
from tg_search.core.meilisearch import MeiliSearchClient
from tg_search.services.config_policy_service import ConfigPolicyService
from tg_search.services.observability_service import ObservabilityService
from tg_search.services.runtime_control_service import RuntimeControlService
from tg_search.services.search_service import SearchService


@dataclass(slots=True)
class ServiceContainer:
    """Shared runtime services used by both API and Bot presentation layers."""

    meili_client: MeiliSearchClient
    config_store: ConfigStore
    config_policy_service: ConfigPolicyService
    observability_service: ObservabilityService
    runtime_control_service: RuntimeControlService
    search_service: SearchService


def build_service_container(
    *,
    meili_client: MeiliSearchClient | None = None,
    meili_host: str | None = None,
    meili_key: str | None = None,
    config_index_name: str = "system_config",
    bootstrap_white_list: Sequence[int] | None = None,
    bootstrap_black_list: Sequence[int] | None = None,
    progress_registry: object | None = None,
    runtime_progress_registry_getter: Callable[[], Any | None] | None = None,
    runtime_api_only_getter: Callable[[], bool] | None = None,
    runtime_cleanup: Callable[[], Any] | None = None,
) -> ServiceContainer:
    """Build a fully wired service container."""
    client = meili_client or MeiliSearchClient(meili_host or MEILI_HOST, meili_key or MEILI_PASS)
    config_store = ConfigStore(client, index_name=config_index_name)
    config_policy_service = ConfigPolicyService(
        config_store,
        bootstrap_white_list=bootstrap_white_list,
        bootstrap_black_list=bootstrap_black_list,
    )
    observability_service = ObservabilityService(
        client,
        progress_registry=progress_registry,
        snapshot_timeout_sec=OBS_SNAPSHOT_TIMEOUT_SEC,
        slow_snapshot_warn_ms=OBS_SNAPSHOT_WARN_MS,
    )
    search_service = SearchService(client)

    container_ref: ServiceContainer | None = None

    def _progress_registry() -> Any | None:
        if runtime_progress_registry_getter is None:
            return None
        return runtime_progress_registry_getter()

    def _api_only_mode() -> bool:
        if runtime_api_only_getter is None:
            return False
        return bool(runtime_api_only_getter())

    async def _runner() -> None:
        from tg_search.main import run

        if container_ref is None:  # pragma: no cover - defensive
            raise RuntimeError("service container is not initialized")
        await run(progress_registry=_progress_registry(), services=container_ref)

    runtime_control_service = RuntimeControlService(
        _runner,
        cleanup=runtime_cleanup,
        api_only_getter=_api_only_mode,
    )
    container = ServiceContainer(
        meili_client=client,
        config_store=config_store,
        config_policy_service=config_policy_service,
        observability_service=observability_service,
        runtime_control_service=runtime_control_service,
        search_service=search_service,
    )
    container_ref = container
    return container
