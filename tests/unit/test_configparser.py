"""Unit tests for message-tracker config helpers."""

import configparser

import pytest

from tg_search.utils import message_tracker as tracker

pytestmark = [pytest.mark.unit]


def test_read_config_creates_required_sections(tmp_path):
    config_file = tmp_path / "config.ini"

    config = tracker.read_config(str(config_file))

    assert "latest_msg_id" in config
    assert "latest_msg_date" in config


def test_write_then_read_latest_msg_id(tmp_path):
    config_file = tmp_path / "config.ini"
    config = tracker.read_config(str(config_file))
    config["latest_msg_id"]["123"] = "456"

    tracker.write_config(config, str(config_file))

    loaded = tracker.read_config(str(config_file))
    assert tracker.get_latest_msg_id(loaded, 123) == 456


def test_update_latest_msg_config_extracts_tail_msg_id(monkeypatch):
    config = configparser.ConfigParser()
    config["latest_msg_id"] = {}
    config["latest_msg_date"] = {}

    monkeypatch.setattr(tracker, "write_config", lambda *_args, **_kwargs: None)

    tracker.update_latest_msg_config(
        peer_id=-100123,
        message={"id": "-100123-789", "date": "2026-02-24T10:00:00Z"},
        config=config,
    )

    assert config["latest_msg_id"]["-100123"] == "789"
    assert config["latest_msg_date"]["-100123"] == "2026-02-24T10:00:00Z"


def test_get_latest_msg_id4_meili_out_of_range_returns_zero():
    # 超出 int32 上限，按实现应回退为 0
    assert tracker.get_latest_msg_id4_meili({"1": "5121831212"}, 1) == 0
