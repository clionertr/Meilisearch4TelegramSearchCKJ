"""Service-layer contracts for runtime policy and runtime-control services."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class DomainError(Exception):
    """Structured domain error used by service layer."""

    def __init__(self, code: str, message: str, detail: str | None = None) -> None:
        self.code = code
        self.message = message
        self.detail = detail
        super().__init__(message if detail is None else f"{message}: {detail}")


class PolicyConfig(BaseModel):
    """Canonical runtime policy snapshot."""

    white_list: list[int] = Field(default_factory=list)
    black_list: list[int] = Field(default_factory=list)
    version: int
    updated_at: str
    source: Literal["config_store", "bootstrap_defaults"] = "config_store"


class PolicyChangeResult(BaseModel):
    """Mutation result for whitelist/blacklist updates."""

    updated_list: list[int] = Field(default_factory=list)
    added: list[int] = Field(default_factory=list)
    removed: list[int] = Field(default_factory=list)
    version: int


RuntimeState = Literal["stopped", "starting", "running", "stopping"]


class RuntimeActionResult(BaseModel):
    """Mutation result for runtime start/stop actions."""

    status: Literal["started", "stopped", "already_running", "already_stopped"]
    message: str
    state: RuntimeState
    last_action_source: str | None = None
    last_error: str | None = None


class RuntimeStatus(BaseModel):
    """Canonical runtime task status snapshot."""

    state: RuntimeState
    is_running: bool
    last_action_source: str | None = None
    last_error: str | None = None
    api_only_mode: bool = False
