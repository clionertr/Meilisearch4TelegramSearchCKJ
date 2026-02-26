"""Unit tests for ConfigPolicyService."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from tg_search.config.config_store import GlobalConfig
from tg_search.services.config_policy_service import ConfigPolicyService
from tg_search.services.contracts import DomainError

pytestmark = [pytest.mark.unit]


class FakeConfigStore:
    """In-memory ConfigStore compatible stub."""

    def __init__(self, initial: GlobalConfig | None = None):
        self._config = initial or GlobalConfig()

    def load_config(self, refresh: bool = False) -> GlobalConfig:
        # Return a detached copy to emulate real store behavior.
        return GlobalConfig.model_validate(self._config.model_dump())

    def save_config(self, patch: dict, expected_version: int | None = None) -> GlobalConfig:
        current = self.load_config(refresh=True)
        if expected_version is not None and current.version != expected_version:
            raise ValueError("version conflict")

        data = current.model_dump()
        for key, value in patch.items():
            if key in ("sync", "storage", "ai", "policy") and isinstance(value, dict):
                data[key].update(value)
            else:
                data[key] = value
        data["version"] = current.version + 1
        data["updated_at"] = datetime.now(timezone.utc).isoformat()

        self._config = GlobalConfig.model_validate(data)
        return self.load_config(refresh=True)


@pytest.mark.asyncio
async def test_bootstrap_initial_policy_from_defaults():
    store = FakeConfigStore()
    service = ConfigPolicyService(store, bootstrap_white_list=[101], bootstrap_black_list=[202])

    policy = await service.get_policy(refresh=True)

    assert policy.white_list == [101]
    assert policy.black_list == [202]
    assert policy.version == 1


@pytest.mark.asyncio
async def test_add_and_remove_whitelist_idempotent():
    store = FakeConfigStore()
    service = ConfigPolicyService(store, bootstrap_white_list=[], bootstrap_black_list=[])

    add_result = await service.add_whitelist([1, 1, 2], source="api")
    assert add_result.updated_list == [1, 2]
    assert add_result.added == [1, 2]

    add_again = await service.add_whitelist([2], source="api")
    assert add_again.updated_list == [1, 2]
    assert add_again.added == []

    remove_result = await service.remove_whitelist([9, 1], source="api")
    assert remove_result.updated_list == [2]
    assert remove_result.removed == [1]


@pytest.mark.asyncio
async def test_set_blacklist_replaces_entire_list():
    store = FakeConfigStore()
    service = ConfigPolicyService(store, bootstrap_white_list=[], bootstrap_black_list=[1, 2])

    result = await service.set_blacklist([3, 4, 4], source="bot")

    assert result.updated_list == [3, 4]
    assert result.added == [3, 4]
    assert result.removed == [1, 2]


@pytest.mark.asyncio
async def test_invalid_ids_raise_domain_error():
    store = FakeConfigStore()
    service = ConfigPolicyService(store, bootstrap_white_list=[], bootstrap_black_list=[])

    with pytest.raises(DomainError, match="ids must not be empty") as exc:
        await service.add_whitelist([], source="api")
    assert exc.value.code == "policy_invalid_ids"

    with pytest.raises(DomainError, match="integers only") as exc:
        await service.add_blacklist([1, "2"], source="api")  # type: ignore[list-item]
    assert exc.value.code == "policy_invalid_ids"


@pytest.mark.asyncio
async def test_sync_dialogs_active_merged_into_whitelist():
    """sync.dialogs 中 active 的 ID 应被合并到 get_policy().white_list 中。"""
    from tg_search.config.config_store import DialogSyncState, GlobalConfig, SyncConfig

    initial = GlobalConfig(
        policy={"white_list": [100], "black_list": []},
        sync=SyncConfig(
            dialogs={
                "200": DialogSyncState(sync_state="active"),
                "300": DialogSyncState(sync_state="paused"),
                "400": DialogSyncState(sync_state="active"),
            }
        ),
    )
    store = FakeConfigStore(initial)
    service = ConfigPolicyService(store, bootstrap_white_list=[], bootstrap_black_list=[])

    policy = await service.get_policy(refresh=True)

    # 100 来自 policy.white_list，200 和 400 来自 sync.dialogs (active)
    assert 100 in policy.white_list
    assert 200 in policy.white_list
    assert 400 in policy.white_list
    # 300 是 paused，不应出现
    assert 300 not in policy.white_list


@pytest.mark.asyncio
async def test_sync_dialogs_no_duplicate_with_existing_whitelist():
    """sync.dialogs 中已在 policy.white_list 里的 ID 不应重复。"""
    from tg_search.config.config_store import DialogSyncState, GlobalConfig, SyncConfig

    initial = GlobalConfig(
        policy={"white_list": [100], "black_list": []},
        sync=SyncConfig(
            dialogs={
                "100": DialogSyncState(sync_state="active"),  # 已在白名单
            }
        ),
    )
    store = FakeConfigStore(initial)
    service = ConfigPolicyService(store, bootstrap_white_list=[], bootstrap_black_list=[])

    policy = await service.get_policy(refresh=True)

    assert policy.white_list.count(100) == 1

