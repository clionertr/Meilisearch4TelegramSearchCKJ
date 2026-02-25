"""Service-layer exports."""

from tg_search.services.config_policy_service import ConfigPolicyService
from tg_search.services.container import ServiceContainer, build_service_container
from tg_search.services.contracts import (
    DomainError,
    PolicyChangeResult,
    PolicyConfig,
    SearchHit,
    SearchPage,
    SearchQuery,
)
from tg_search.services.search_service import SearchService

__all__ = [
    "ConfigPolicyService",
    "SearchService",
    "ServiceContainer",
    "build_service_container",
    "DomainError",
    "PolicyConfig",
    "PolicyChangeResult",
    "SearchQuery",
    "SearchHit",
    "SearchPage",
]
