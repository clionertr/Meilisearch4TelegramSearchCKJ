"""Service-layer exports."""

from tg_search.services.config_policy_service import ConfigPolicyService
from tg_search.services.container import ServiceContainer, build_service_container
from tg_search.services.contracts import (
    DomainError,
    IndexSnapshot,
    PolicyChangeResult,
    PolicyConfig,
    ProgressSnapshot,
    SearchHit,
    SearchPage,
    SearchQuery,
    StorageSnapshot,
    SystemSnapshot,
)
from tg_search.services.observability_service import ObservabilityService
from tg_search.services.search_service import SearchService

__all__ = [
    "ConfigPolicyService",
    "ObservabilityService",
    "SearchService",
    "ServiceContainer",
    "build_service_container",
    "DomainError",
    "PolicyConfig",
    "PolicyChangeResult",
    "SearchQuery",
    "SearchHit",
    "SearchPage",
    "SystemSnapshot",
    "IndexSnapshot",
    "StorageSnapshot",
    "ProgressSnapshot",
]
