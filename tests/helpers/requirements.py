"""Shared requirement checks for integration tests."""

from __future__ import annotations

import os
from pathlib import Path

import httpx

DEFAULT_FAKE_MEILI_KEYS: set[str] = {
    "",
    "test_key",
    "test_master_key",
    "test_master_key_12345",
    "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
}


def load_meili_env_from_dotenv(fake_keys: set[str] | None = None) -> None:
    """Fill MEILI_HOST/MEILI_MASTER_KEY from .env when current values are placeholders."""
    fake_keys = fake_keys or DEFAULT_FAKE_MEILI_KEYS

    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return

    try:
        from dotenv import dotenv_values
    except ImportError:
        return

    values = dotenv_values(env_path)

    if os.environ.get("MEILI_HOST", "") in {"", "http://localhost:7700"}:
        real_host = values.get("MEILI_HOST")
        if real_host:
            os.environ["MEILI_HOST"] = real_host

    if os.environ.get("MEILI_MASTER_KEY", "") in fake_keys:
        real_key = values.get("MEILI_MASTER_KEY", "")
        if real_key and real_key not in fake_keys:
            os.environ["MEILI_MASTER_KEY"] = real_key


def check_meili_available(
    host: str,
    key: str,
    *,
    require_auth: bool,
    fake_keys: set[str] | None = None,
    timeout_sec: float = 3,
) -> str | None:
    """Return None when MeiliSearch is available, otherwise a skip reason."""
    fake_keys = fake_keys or DEFAULT_FAKE_MEILI_KEYS

    if key in fake_keys:
        return f"MEILI_MASTER_KEY 为占位值 ({key!r})，跳过真实 MeiliSearch 测试"

    try:
        if require_auth:
            response = httpx.get(
                f"{host}/indexes",
                headers={"Authorization": f"Bearer {key}"},
                timeout=timeout_sec,
            )
            if response.status_code in (401, 403):
                return f"MEILI_MASTER_KEY 无效（{response.status_code}），跳过（需要有效认证）"
            if response.status_code not in (200, 404):
                return f"MeiliSearch 响应异常: {response.status_code}"
        else:
            response = httpx.get(f"{host}/health", timeout=timeout_sec)
            if response.status_code != 200:
                return f"MeiliSearch health check 失败: {response.status_code}"
    except Exception as exc:  # pragma: no cover - defensive branch
        return f"MeiliSearch 不可达 ({host}): {exc}"

    return None
