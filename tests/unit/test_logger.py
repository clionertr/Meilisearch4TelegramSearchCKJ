"""Unit tests for logger setup idempotency."""

import logging

import pytest

from tg_search.core import logger as logger_module

pytestmark = [pytest.mark.unit]


def test_setup_logger_is_idempotent():
    root = logging.getLogger()

    logger_module.setup_logger()
    handler_count_after_first = len(root.handlers)

    logger_module.setup_logger()
    handler_count_after_second = len(root.handlers)

    assert handler_count_after_second == handler_count_after_first
    assert handler_count_after_first > 0


def test_setup_logger_returns_named_logger():
    logger = logger_module.setup_logger("tg_search.tests")
    assert logger.name == "tg_search.tests"
