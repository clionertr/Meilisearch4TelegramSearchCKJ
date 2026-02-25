"""Unified runtime whitelist/blacklist policy service."""

from __future__ import annotations

import asyncio
import inspect
import time
from collections.abc import Awaitable, Callable, Sequence
from typing import Literal

from tg_search.config import settings
from tg_search.config.config_store import ConfigStore, GlobalConfig
from tg_search.core.logger import setup_logger
from tg_search.services.contracts import DomainError, PolicyChangeResult, PolicyConfig

logger = setup_logger()


def _normalize_ids(ids: Sequence[int]) -> list[int]:
    """Validate and de-duplicate IDs while preserving order."""
    if not isinstance(ids, Sequence) or isinstance(ids, (str, bytes)):
        raise DomainError("policy_invalid_ids", "ids must be a list of integers")
    if len(ids) == 0:
        raise DomainError("policy_invalid_ids", "ids must not be empty")

    deduped: list[int] = []
    seen: set[int] = set()
    for raw in ids:
        if isinstance(raw, bool) or not isinstance(raw, int):
            raise DomainError("policy_invalid_ids", "ids must contain integers only")
        if raw not in seen:
            seen.add(raw)
            deduped.append(raw)
    return deduped


PolicySubscriber = Callable[[PolicyConfig], Awaitable[None] | None]


class ConfigPolicyService:
    """Single source for runtime policy reads/writes."""

    def __init__(
        self,
        config_store: ConfigStore,
        *,
        bootstrap_white_list: Sequence[int] | None = None,
        bootstrap_black_list: Sequence[int] | None = None,
    ) -> None:
        self._store = config_store
        self._lock = asyncio.Lock()
        self._init_lock = asyncio.Lock()
        self._initialized = False
        self._bootstrap_white_list = list(
            bootstrap_white_list if bootstrap_white_list is not None else settings.WHITE_LIST
        )
        self._bootstrap_black_list = list(
            bootstrap_black_list if bootstrap_black_list is not None else settings.BLACK_LIST
        )
        self._subscribers: set[PolicySubscriber] = set()

    async def _load_config(self, refresh: bool = False) -> GlobalConfig:
        try:
            return await asyncio.to_thread(self._store.load_config, refresh)
        except Exception as exc:
            raise DomainError("policy_store_unavailable", "policy store unavailable", detail=str(exc)) from exc

    async def _save_config(self, patch: dict, expected_version: int) -> GlobalConfig:
        try:
            return await asyncio.to_thread(self._store.save_config, patch, expected_version)
        except ValueError as exc:
            raise DomainError("policy_version_conflict", "policy version conflict", detail=str(exc)) from exc
        except Exception as exc:
            raise DomainError("policy_store_unavailable", "policy store unavailable", detail=str(exc)) from exc

    def subscribe(self, subscriber: PolicySubscriber) -> Callable[[], None]:
        """Register a runtime policy subscriber for immediate push updates."""
        self._subscribers.add(subscriber)

        def _unsubscribe() -> None:
            self._subscribers.discard(subscriber)

        return _unsubscribe

    async def _notify_subscribers(self, policy: PolicyConfig) -> None:
        if not self._subscribers:
            return

        coroutines: list[Awaitable[None]] = []
        for subscriber in tuple(self._subscribers):
            try:
                maybe_awaitable = subscriber(policy)
            except Exception as exc:
                logger.warning(
                    "[ConfigPolicyService] subscriber raised synchronously: %s: %s",
                    type(exc).__name__,
                    exc,
                )
                continue
            if inspect.isawaitable(maybe_awaitable):
                coroutines.append(maybe_awaitable)

        if not coroutines:
            return

        results = await asyncio.gather(*coroutines, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                logger.warning(
                    "[ConfigPolicyService] subscriber raised asynchronously: %s: %s",
                    type(result).__name__,
                    result,
                )

    async def ensure_initialized(self) -> None:
        """Bootstrap policy section once when document policy is empty."""
        if self._initialized:
            return

        async with self._init_lock:
            if self._initialized:
                return

            cfg = await self._load_config(refresh=True)
            has_policy_values = bool(cfg.policy.white_list or cfg.policy.black_list)
            has_bootstrap_values = bool(self._bootstrap_white_list or self._bootstrap_black_list)

            if (not has_policy_values) and has_bootstrap_values:
                try:
                    cfg = await self._save_config(
                        {
                            "policy": {
                                "white_list": list(self._bootstrap_white_list),
                                "black_list": list(self._bootstrap_black_list),
                            }
                        },
                        expected_version=cfg.version,
                    )
                except DomainError as exc:
                    # Another worker may win bootstrap race; reload latest in that case.
                    if exc.code == "policy_version_conflict":
                        cfg = await self._load_config(refresh=True)
                    else:
                        raise
                logger.info(
                    "[ConfigPolicyService] bootstrap initialized: white=%d black=%d version=%d",
                    len(cfg.policy.white_list),
                    len(cfg.policy.black_list),
                    cfg.version,
                )

            self._initialized = True

    @staticmethod
    def _to_policy_config(cfg: GlobalConfig, source: Literal["config_store", "bootstrap_defaults"]) -> PolicyConfig:
        return PolicyConfig(
            white_list=list(cfg.policy.white_list),
            black_list=list(cfg.policy.black_list),
            version=cfg.version,
            updated_at=cfg.updated_at,
            source=source,
        )

    async def get_policy(self, refresh: bool = False) -> PolicyConfig:
        t0 = time.monotonic()
        await self.ensure_initialized()
        cfg = await self._load_config(refresh=refresh)
        policy = self._to_policy_config(cfg, source="config_store")
        elapsed_ms = (time.monotonic() - t0) * 1000
        logger.info(
            "[ConfigPolicyService] get_policy refresh=%s white=%d black=%d version=%d duration_ms=%.1f",
            refresh,
            len(policy.white_list),
            len(policy.black_list),
            policy.version,
            elapsed_ms,
        )
        return policy

    async def get_policy_lists(self, refresh: bool = False) -> tuple[list[int], list[int]]:
        policy = await self.get_policy(refresh=refresh)
        return policy.white_list, policy.black_list

    async def _mutate(
        self,
        *,
        target: Literal["white_list", "black_list"],
        action: Literal["add", "remove", "set"],
        ids: Sequence[int],
        source: str,
    ) -> PolicyChangeResult:
        normalized_ids = _normalize_ids(ids)
        await self.ensure_initialized()

        async with self._lock:
            cfg = await self._load_config(refresh=True)

            white = list(cfg.policy.white_list)
            black = list(cfg.policy.black_list)
            current = white if target == "white_list" else black
            before_size = len(current)

            added: list[int] = []
            removed: list[int] = []

            if action == "add":
                added = [item for item in normalized_ids if item not in current]
                updated = current + added
            elif action == "remove":
                removed = [item for item in normalized_ids if item in current]
                updated = [item for item in current if item not in set(normalized_ids)]
            elif action == "set":
                updated = list(normalized_ids)
                added = [item for item in updated if item not in current]
                removed = [item for item in current if item not in set(updated)]
            else:
                raise DomainError("policy_invalid_action", f"unsupported action: {action}")

            if target == "white_list":
                white = updated
            else:
                black = updated

            next_cfg = await self._save_config(
                {"policy": {"white_list": white, "black_list": black}},
                expected_version=cfg.version,
            )

            logger.info(
                "[ConfigPolicyService] source=%s action=%s target=%s before_size=%d after_size=%d version=%d",
                source,
                action,
                target,
                before_size,
                len(updated),
                next_cfg.version,
            )

            await self._notify_subscribers(self._to_policy_config(next_cfg, source="config_store"))

            return PolicyChangeResult(
                updated_list=updated,
                added=added,
                removed=removed,
                version=next_cfg.version,
            )

    async def add_whitelist(self, ids: Sequence[int], source: str = "api") -> PolicyChangeResult:
        return await self._mutate(target="white_list", action="add", ids=ids, source=source)

    async def remove_whitelist(self, ids: Sequence[int], source: str = "api") -> PolicyChangeResult:
        return await self._mutate(target="white_list", action="remove", ids=ids, source=source)

    async def add_blacklist(self, ids: Sequence[int], source: str = "api") -> PolicyChangeResult:
        return await self._mutate(target="black_list", action="add", ids=ids, source=source)

    async def remove_blacklist(self, ids: Sequence[int], source: str = "api") -> PolicyChangeResult:
        return await self._mutate(target="black_list", action="remove", ids=ids, source=source)

    async def set_whitelist(self, ids: Sequence[int], source: str = "bot") -> PolicyChangeResult:
        return await self._mutate(target="white_list", action="set", ids=ids, source=source)

    async def set_blacklist(self, ids: Sequence[int], source: str = "bot") -> PolicyChangeResult:
        return await self._mutate(target="black_list", action="set", ids=ids, source=source)
