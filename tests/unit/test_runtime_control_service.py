"""Unit tests for RuntimeControlService."""

from __future__ import annotations

import asyncio

import pytest

from tg_search.services.contracts import DomainError
from tg_search.services.runtime_control_service import RuntimeControlService

pytestmark = [pytest.mark.unit]


@pytest.mark.asyncio
async def test_start_stop_idempotent():
    gate = asyncio.Event()
    started = asyncio.Event()

    async def runner():
        started.set()
        await gate.wait()

    service = RuntimeControlService(runner)

    first_start = await service.start(source="api")
    assert first_start.status == "started"
    await asyncio.wait_for(started.wait(), timeout=1.0)

    second_start = await service.start(source="bot")
    assert second_start.status == "already_running"

    first_stop = await service.stop(source="api")
    assert first_stop.status == "stopped"

    second_stop = await service.stop(source="bot")
    assert second_stop.status == "already_stopped"


@pytest.mark.asyncio
async def test_api_only_mode_rejects_start():
    api_only = True

    async def runner():
        await asyncio.sleep(0)

    service = RuntimeControlService(runner, api_only_getter=lambda: api_only)

    with pytest.raises(DomainError) as exc:
        await service.start(source="api")
    assert exc.value.code == "runtime_api_only_mode"


@pytest.mark.asyncio
async def test_concurrent_starts_only_one_starts():
    started_count = 0
    gate = asyncio.Event()

    async def runner():
        nonlocal started_count
        started_count += 1
        await gate.wait()

    service = RuntimeControlService(runner)

    results = await asyncio.gather(*[service.start(source="api") for _ in range(10)])
    statuses = [r.status for r in results]

    assert statuses.count("started") == 1
    assert statuses.count("already_running") == 9
    assert started_count == 1

    await service.stop(source="api")


@pytest.mark.asyncio
async def test_concurrent_stops_do_not_crash():
    gate = asyncio.Event()

    async def runner():
        await gate.wait()

    service = RuntimeControlService(runner)
    await service.start(source="api")

    results = await asyncio.gather(*[service.stop(source="api") for _ in range(5)])
    statuses = [r.status for r in results]
    assert statuses.count("stopped") == 1
    assert statuses.count("already_stopped") == 4


@pytest.mark.asyncio
async def test_task_failure_updates_last_error():
    async def failing_runner():
        raise RuntimeError("boom")

    service = RuntimeControlService(failing_runner)
    await service.start(source="api")
    await asyncio.sleep(0.05)

    status = await service.status()
    assert status.is_running is False
    assert status.state == "stopped"
    assert status.last_error is not None
    assert "boom" in status.last_error
