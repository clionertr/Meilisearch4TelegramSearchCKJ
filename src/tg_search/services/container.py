"""Service container for shared singleton-style service wiring."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from tg_search.config.config_store import ConfigStore
from tg_search.config.settings import MEILI_HOST, MEILI_PASS
from tg_search.core.meilisearch import MeiliSearchClient
from tg_search.services.config_policy_service import ConfigPolicyService
from tg_search.services.observability_service import ObservabilityService


@dataclass(slots=True)
class ServiceContainer:
    """Shared runtime services used by both API and Bot presentation layers."""

    meili_client: MeiliSearchClient
    config_store: ConfigStore
    config_policy_service: ConfigPolicyService
    observability_service: ObservabilityService


def build_service_container(
    *,
    meili_client: MeiliSearchClient | None = None,
    meili_host: str | None = None,
    meili_key: str | None = None,
    config_index_name: str = "system_config",
    bootstrap_white_list: Sequence[int] | None = None,
    bootstrap_black_list: Sequence[int] | None = None,
    progress_registry: object | None = None,
) -> ServiceContainer:
    """Build a fully wired service container."""
    client = meili_client or MeiliSearchClient(meili_host or MEILI_HOST, meili_key or MEILI_PASS)
    config_store = ConfigStore(client, index_name=config_index_name)
    config_policy_service = ConfigPolicyService(
        config_store,
        bootstrap_white_list=bootstrap_white_list,
        bootstrap_black_list=bootstrap_black_list,
    )
    observability_service = ObservabilityService(client, progress_registry=progress_registry)
    return ServiceContainer(
        meili_client=client,
        config_store=config_store,
        config_policy_service=config_policy_service,
        observability_service=observability_service,
    )
