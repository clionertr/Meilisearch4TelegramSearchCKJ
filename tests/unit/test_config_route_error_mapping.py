"""Unit tests for config route domain-error mapping."""

import pytest

from tg_search.api.routes.config import _to_http_error
from tg_search.services.contracts import DomainError

pytestmark = [pytest.mark.unit]


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (DomainError("policy_invalid_ids", "invalid ids"), 422),
        (DomainError("policy_version_conflict", "version conflict"), 409),
        (DomainError("policy_store_unavailable", "store unavailable"), 503),
        (DomainError("policy_invalid_action", "invalid action"), 400),
    ],
)
def test_domain_error_to_http_status_mapping(error: DomainError, expected_status: int):
    http_error = _to_http_error(error)
    assert http_error.status_code == expected_status
    assert http_error.detail["error_code"] == error.code
