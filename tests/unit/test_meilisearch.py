"""Unit tests for Meili-related helpers in message_tracker."""

from unittest.mock import MagicMock

import pytest

from tg_search.utils.message_tracker import read_config_from_meili, write_config2_meili

pytestmark = [pytest.mark.unit]


def test_read_config_from_meili_returns_first_hit():
    meili = MagicMock()
    meili.search.return_value = {"hits": [{"id": 7, "k": "v"}]}

    result = read_config_from_meili(meili)

    meili.create_index.assert_called_once_with("config")
    assert result == {"id": 7, "k": "v"}


def test_read_config_from_meili_on_error_returns_default():
    meili = MagicMock()
    meili.search.side_effect = RuntimeError("boom")

    result = read_config_from_meili(meili)

    assert result == {"id": 0}


def test_write_config2_meili_adds_single_document():
    meili = MagicMock()
    payload = {"id": "global", "version": 1}

    write_config2_meili(meili, payload)

    meili.add_documents.assert_called_once_with([payload], "config")
