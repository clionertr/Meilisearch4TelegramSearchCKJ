"""Unified runtime start/stop controller for Bot/API shared task lifecycle."""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable, Callable
from typing import Any

from tg_search.core.logger import setup_logger
from tg_search.services.contracts import DomainError, RuntimeActionResult, RuntimeState, RuntimeStatus

logger = setup_logger()

RuntimeRunner = Callable[[], Awaitable[None]]
RuntimeCleanup = Callable[[], Awaitable[None] | None]
ApiOnlyGetter = Callable[[], bool]


class RuntimeControlService:
    """Single source of truth for runtime task lifecycle control."""

    def __init__(
        self,
        runner: RuntimeRunner,
        *,
        cleanup: RuntimeCleanup | None = None,
        api_only_getter: ApiOnlyGetter | None = None,
    ) -> None:
        self._runner = runner
        self._cleanup = cleanup
        self._api_only_getter = api_only_getter or (lambda: False)

        self._task: asyncio.Task[None] | None = None
        self._state: RuntimeState = "stopped"
        self._last_action_source: str | None = None
        self._last_error: str | None = None
        self._lock = asyncio.Lock()

    def _is_task_running(self) -> bool:
        return self._task is not None and not self._task.done()

    def _is_api_only_mode(self) -> bool:
        try:
            return bool(self._api_only_getter())
        except Exception as exc:
            logger.warning("[RuntimeControlService] api_only_getter failed: %s: %s", type(exc).__name__, exc)
            return False

    def _snapshot(self) -> RuntimeStatus:
        return RuntimeStatus(
            state=self._state,
            is_running=self._is_task_running(),
            last_action_source=self._last_action_source,
            last_error=self._last_error,
            api_only_mode=self._is_api_only_mode(),
        )

    def _on_task_done(self, task: asyncio.Task[None]) -> None:
        """Sync completion state when the runtime task exits unexpectedly."""
        if self._task is not task:
            return

        err_text: str | None = None
        try:
            if task.cancelled():
                err_text = None
            else:
                exc = task.exception()
                if exc is not None:
                    err_text = f"{type(exc).__name__}: {exc}"
        except Exception as exc:  # pragma: no cover - defensive
            err_text = f"{type(exc).__name__}: {exc}"

        self._task = None
        self._state = "stopped"
        if err_text:
            self._last_error = err_text
            logger.error("[RuntimeControlService] runtime task exited with error: %s", err_text)
        else:
            logger.info("[RuntimeControlService] runtime task exited")

    async def _run_cleanup(self) -> None:
        if self._cleanup is None:
            return
        try:
            maybe_awaitable = self._cleanup()
            if inspect.isawaitable(maybe_awaitable):
                await maybe_awaitable
        except Exception as exc:
            self._last_error = f"{type(exc).__name__}: {exc}"
            logger.error("[RuntimeControlService] cleanup failed: %s", self._last_error)
            raise DomainError(
                "runtime_cleanup_failed",
                "runtime cleanup failed",
                detail=str(exc),
            ) from exc

    async def start(self, source: str) -> RuntimeActionResult:
        """Start runtime task idempotently."""
        async with self._lock:
            if self._is_task_running():
                self._state = "running"
                self._last_action_source = source
                return RuntimeActionResult(
                    status="already_running",
                    message="Runtime task is already running",
                    state=self._state,
                    last_action_source=self._last_action_source,
                    last_error=self._last_error,
                )

            if self._is_api_only_mode():
                raise DomainError(
                    "runtime_api_only_mode",
                    "Cannot start runtime task in API-only mode",
                )

            self._state = "starting"
            self._last_action_source = source
            self._last_error = None

            try:
                task: asyncio.Task[None] = asyncio.create_task(self._runner())
            except Exception as exc:
                self._task = None
                self._state = "stopped"
                self._last_error = f"{type(exc).__name__}: {exc}"
                raise DomainError(
                    "runtime_start_failed",
                    "Failed to start runtime task",
                    detail=str(exc),
                ) from exc

            self._task = task
            self._task.add_done_callback(self._on_task_done)
            self._state = "running"

            logger.info("[RuntimeControlService] runtime started by source=%s", source)
            return RuntimeActionResult(
                status="started",
                message="Runtime task started successfully",
                state=self._state,
                last_action_source=self._last_action_source,
                last_error=self._last_error,
            )

    async def stop(self, source: str) -> RuntimeActionResult:
        """Stop runtime task idempotently."""
        async with self._lock:
            self._last_action_source = source

            if not self._is_task_running():
                self._task = None
                self._state = "stopped"
                return RuntimeActionResult(
                    status="already_stopped",
                    message="Runtime task is not running",
                    state=self._state,
                    last_action_source=self._last_action_source,
                    last_error=self._last_error,
                )

            self._state = "stopping"
            task = self._task
            assert task is not None
            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception as exc:
                self._last_error = f"{type(exc).__name__}: {exc}"
                logger.error("[RuntimeControlService] runtime stop failed: %s", self._last_error)
                raise DomainError(
                    "runtime_stop_failed",
                    "Failed to stop runtime task",
                    detail=str(exc),
                ) from exc
            finally:
                self._task = None
                self._state = "stopped"

            await self._run_cleanup()
            logger.info("[RuntimeControlService] runtime stopped by source=%s", source)

            return RuntimeActionResult(
                status="stopped",
                message="Runtime task stopped successfully",
                state=self._state,
                last_action_source=self._last_action_source,
                last_error=self._last_error,
            )

    async def status(self) -> RuntimeStatus:
        """Return current runtime status snapshot."""
        return self._snapshot()

    def set_api_only_getter(self, getter: ApiOnlyGetter) -> None:
        """Update API-only mode getter (mainly for app-lifespan wiring/tests)."""
        self._api_only_getter = getter

    # test-only helper: avoid using in production code paths
    def get_task_for_test(self) -> asyncio.Task[None] | None:
        return self._task
