"""Unit tests for control route domain-error mapping."""

import pytest

from tg_search.api.routes.control import _to_http_error
from tg_search.services.contracts import DomainError

pytestmark = [pytest.mark.unit]


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (DomainError("runtime_api_only_mode", "api-only"), 400),
        (DomainError("runtime_start_failed", "start failed"), 500),
        (DomainError("runtime_stop_failed", "stop failed"), 500),
        (DomainError("runtime_cleanup_failed", "cleanup failed"), 500),
    ],
)
def test_runtime_domain_error_to_http_status_mapping(error: DomainError, expected_status: int):
    http_error = _to_http_error(error)
    assert http_error.status_code == expected_status
    assert http_error.detail["error_code"] == error.code
