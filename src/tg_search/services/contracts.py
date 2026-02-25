"""Service-layer contracts for runtime policy management."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


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
