"""
Runtime Config Store backed by SQLite.

This module keeps the external GlobalConfig contract stable while moving runtime
state persistence from MeiliSearch to SQLite.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from tg_search.core.logger import setup_logger
from tg_search.core.meilisearch import MeiliSearchClient

logger = setup_logger()

_INDEX_NAME = "system_config"
_DOC_ID = "global"
_CACHE_TTL_SEC = 10
_DEFAULT_DB_PATH = os.getenv("CONFIG_DB_PATH", "session/config_store.sqlite3")
_SQLITE_BUSY_TIMEOUT_SEC = float(os.getenv("CONFIG_STORE_SQLITE_BUSY_TIMEOUT_SEC", "5"))
_READ_WARN_MS = int(os.getenv("CONFIG_STORE_SQLITE_READ_WARN_MS", "100"))
_WRITE_WARN_MS = int(os.getenv("CONFIG_STORE_SQLITE_WRITE_WARN_MS", "120"))
_SIGNED_INT32_MAX = 2_147_483_647

_JOURNAL_MODE = os.getenv("CONFIG_STORE_SQLITE_JOURNAL_MODE", "WAL").upper()
if _JOURNAL_MODE not in {"DELETE", "TRUNCATE", "PERSIST", "MEMORY", "WAL", "OFF"}:
    _JOURNAL_MODE = "WAL"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ============ Pydantic Models ============


class DialogSyncState(BaseModel):
    """单个对话的同步状态。"""

    sync_state: str = "inactive"
    date_from: str | None = None
    last_synced_at: str | None = None
    updated_at: str = Field(default_factory=_now_iso)


class SyncConfig(BaseModel):
    """Dialog Sync 相关配置。"""

    dialogs: dict[str, DialogSyncState] = Field(default_factory=dict)
    available_cache_ttl_sec: int = 120


class StorageConfig(BaseModel):
    """Storage 相关配置。"""

    auto_clean_enabled: bool = False
    media_retention_days: int = 30


class AiConfig(BaseModel):
    """AI 供应商配置。"""

    provider: str = "openai_compatible"
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    api_key: str = ""


class PolicySection(BaseModel):
    """运行时同步策略配置。"""

    white_list: list[int] = Field(default_factory=list)
    black_list: list[int] = Field(default_factory=list)


class GlobalConfig(BaseModel):
    """全局配置文档。"""

    id: str = _DOC_ID
    version: int = 0
    updated_at: str = Field(default_factory=_now_iso)
    sync: SyncConfig = Field(default_factory=SyncConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    ai: AiConfig = Field(default_factory=AiConfig)
    policy: PolicySection = Field(default_factory=PolicySection)


# ============ Cache ============


class _Cache:
    """简单内存缓存，支持 TTL 失效。"""

    def __init__(self, ttl_sec: float = _CACHE_TTL_SEC) -> None:
        self._ttl = ttl_sec
        self._value: GlobalConfig | None = None
        self._loaded_at: float = 0.0

    def get(self) -> GlobalConfig | None:
        if self._value is not None and (time.monotonic() - self._loaded_at) < self._ttl:
            return self._value
        return None

    def set(self, config: GlobalConfig) -> None:
        self._value = config
        self._loaded_at = time.monotonic()

    def invalidate(self) -> None:
        self._value = None
        self._loaded_at = 0.0


# ============ ConfigStore ============


class ConfigStore:
    """
    统一配置持久化服务（SQLite 后端）。

    Notes:
    - 保持 `load_config/save_config/update_section` 接口兼容。
    - 将 `sync.dialogs` 和 `latest_msg_id` 合并到 `dialog_state` 表。
    - 在 SQLite 为空时，自动尝试从旧版 MeiliSearch `system_config/sync_offsets` 迁移。
    """

    def __init__(
        self,
        meili: MeiliSearchClient | None,
        index_name: str = _INDEX_NAME,
        *,
        db_path: str | None = None,
    ) -> None:
        self._meili = meili
        self._index_name = index_name
        self._cache = _Cache()
        self._lock = threading.RLock()
        self._db_path = self._resolve_db_path(index_name=index_name, db_path=db_path)
        self._initialize_storage()

    @property
    def db_path(self) -> Path:
        return self._db_path

    @staticmethod
    def _resolve_db_path(index_name: str, db_path: str | None) -> Path:
        base = Path(db_path or os.getenv("CONFIG_DB_PATH", _DEFAULT_DB_PATH))
        if db_path is None and index_name != _INDEX_NAME:
            safe_index = re.sub(r"[^a-zA-Z0-9._-]+", "_", index_name).strip("._")
            if not safe_index:
                safe_index = "default"
            suffix = base.suffix or ".sqlite3"
            base = base.with_name(f"{base.stem}_{safe_index}{suffix}")
        base.parent.mkdir(parents=True, exist_ok=True)
        return base

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(
            self._db_path,
            timeout=_SQLITE_BUSY_TIMEOUT_SEC,
            isolation_level=None,  # autocommit, explicit BEGIN for writes
        )
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute(f"PRAGMA journal_mode={_JOURNAL_MODE}")
            conn.execute("PRAGMA synchronous=NORMAL")
            yield conn
        finally:
            conn.close()

    @staticmethod
    def _create_tables(conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS system_meta (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                version INTEGER NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS dialog_state (
                dialog_id INTEGER PRIMARY KEY,
                sync_state TEXT NOT NULL DEFAULT 'inactive',
                latest_msg_id INTEGER NOT NULL DEFAULT 0,
                date_from TEXT NULL,
                last_synced_at TEXT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_dialog_state_sync_state ON dialog_state(sync_state)")

    @staticmethod
    def _read_meta(conn: sqlite3.Connection) -> tuple[int, str] | None:
        row = conn.execute("SELECT version, updated_at FROM system_meta WHERE id = 1").fetchone()
        if row is None:
            return None
        try:
            return int(row["version"]), str(row["updated_at"])
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _write_meta(conn: sqlite3.Connection, *, version: int, updated_at: str) -> None:
        conn.execute(
            """
            INSERT INTO system_meta (id, version, updated_at)
            VALUES (1, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                version = excluded.version,
                updated_at = excluded.updated_at
            """,
            (version, updated_at),
        )

    @staticmethod
    def _write_section_json(conn: sqlite3.Connection, key: str, value: Any) -> None:
        conn.execute(
            """
            INSERT INTO system_config (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, json.dumps(value, ensure_ascii=False)),
        )

    @staticmethod
    def _read_section_json(conn: sqlite3.Connection, key: str) -> Any | None:
        row = conn.execute("SELECT value FROM system_config WHERE key = ?", (key,)).fetchone()
        if row is None:
            return None
        try:
            return json.loads(str(row["value"]))
        except Exception:
            return None

    @staticmethod
    def _clamp_latest_msg_id(value: Any) -> int:
        try:
            num = int(value)
        except (TypeError, ValueError):
            return 0
        if num < 0 or num > _SIGNED_INT32_MAX:
            return 0
        return num

    def _initialize_storage(self) -> None:
        with self._connect() as conn:
            self._create_tables(conn)
            if self._read_meta(conn) is not None:
                logger.info("[ConfigStore] SQLite store ready: %s", self._db_path)
                return

            migrated = self._try_migrate_from_legacy_meili(conn)
            if not migrated:
                default_cfg = GlobalConfig()
                conn.execute("BEGIN IMMEDIATE")
                try:
                    self._persist_sections(conn, default_cfg)
                    self._write_meta(conn, version=default_cfg.version, updated_at=default_cfg.updated_at)
                    conn.execute("COMMIT")
                except Exception:
                    conn.execute("ROLLBACK")
                    raise

            logger.info("[ConfigStore] SQLite store initialized: %s (migrated=%s)", self._db_path, migrated)

    def _persist_sections(self, conn: sqlite3.Connection, cfg: GlobalConfig) -> None:
        self._write_section_json(conn, "storage", cfg.storage.model_dump())
        self._write_section_json(conn, "ai", cfg.ai.model_dump())
        self._write_section_json(conn, "policy", cfg.policy.model_dump())
        self._write_section_json(conn, "sync_available_cache_ttl_sec", cfg.sync.available_cache_ttl_sec)

    def _read_config_from_conn(self, conn: sqlite3.Connection) -> GlobalConfig:
        meta = self._read_meta(conn)
        if meta is None:
            # Defensive fallback: initialize defaults in-place.
            default_cfg = GlobalConfig()
            self._persist_sections(conn, default_cfg)
            self._write_meta(conn, version=default_cfg.version, updated_at=default_cfg.updated_at)
            return default_cfg

        version, updated_at = meta
        raw_storage = self._read_section_json(conn, "storage")
        raw_ai = self._read_section_json(conn, "ai")
        raw_policy = self._read_section_json(conn, "policy")
        raw_sync_ttl = self._read_section_json(conn, "sync_available_cache_ttl_sec")

        dialogs: dict[str, DialogSyncState] = {}
        for row in conn.execute(
            """
            SELECT dialog_id, sync_state, date_from, last_synced_at, updated_at
            FROM dialog_state
            ORDER BY dialog_id
            """
        ):
            did = int(row["dialog_id"])
            try:
                dialogs[str(did)] = DialogSyncState(
                    sync_state=str(row["sync_state"]),
                    date_from=row["date_from"],
                    last_synced_at=row["last_synced_at"],
                    updated_at=str(row["updated_at"]),
                )
            except ValidationError:
                # Skip broken row and continue.
                continue

        try:
            storage = StorageConfig.model_validate(raw_storage or {})
            ai = AiConfig.model_validate(raw_ai or {})
            policy = PolicySection.model_validate(raw_policy or {})
            available_ttl = int(raw_sync_ttl) if raw_sync_ttl is not None else 120
            sync = SyncConfig(dialogs=dialogs, available_cache_ttl_sec=available_ttl)
            return GlobalConfig(
                id=_DOC_ID,
                version=version,
                updated_at=updated_at,
                sync=sync,
                storage=storage,
                ai=ai,
                policy=policy,
            )
        except Exception as exc:
            logger.warning("[ConfigStore] SQLite document invalid, resetting to defaults. error=%s", exc)
            default_cfg = GlobalConfig()
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute("DELETE FROM system_config")
                conn.execute("DELETE FROM dialog_state")
                self._persist_sections(conn, default_cfg)
                self._write_meta(conn, version=default_cfg.version, updated_at=default_cfg.updated_at)
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
            return default_cfg

    def _replace_dialog_states(self, conn: sqlite3.Connection, dialogs_raw: dict[str, Any]) -> None:
        existing_latest = {
            int(row["dialog_id"]): self._clamp_latest_msg_id(row["latest_msg_id"])
            for row in conn.execute("SELECT dialog_id, latest_msg_id FROM dialog_state")
        }
        conn.execute("DELETE FROM dialog_state")
        for str_id, state_raw in dialogs_raw.items():
            try:
                did = int(str_id)
            except (TypeError, ValueError):
                continue
            try:
                state = DialogSyncState.model_validate(state_raw)
            except ValidationError:
                continue
            conn.execute(
                """
                INSERT INTO dialog_state (
                    dialog_id, sync_state, latest_msg_id, date_from, last_synced_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    did,
                    state.sync_state,
                    existing_latest.get(did, 0),
                    state.date_from,
                    state.last_synced_at,
                    state.updated_at,
                ),
            )

    def _upsert_dialog_states(self, conn: sqlite3.Connection, dialog_states: dict[int | str, Any]) -> None:
        for dialog_id, state_raw in dialog_states.items():
            try:
                did = int(dialog_id)
            except (TypeError, ValueError):
                continue
            state = DialogSyncState.model_validate(state_raw)
            conn.execute(
                """
                INSERT INTO dialog_state (
                    dialog_id, sync_state, latest_msg_id, date_from, last_synced_at, updated_at
                ) VALUES (?, ?, 0, ?, ?, ?)
                ON CONFLICT(dialog_id) DO UPDATE SET
                    sync_state = excluded.sync_state,
                    date_from = excluded.date_from,
                    last_synced_at = excluded.last_synced_at,
                    updated_at = excluded.updated_at
                """,
                (
                    did,
                    state.sync_state,
                    state.date_from,
                    state.last_synced_at,
                    state.updated_at,
                ),
            )

    def _load_legacy_offsets(self) -> dict[int, int]:
        if self._meili is None:
            return {}

        try:
            result = self._meili.search(None, "sync_offsets", limit=1)
            hits = result.get("hits", [])
            if not hits:
                return {}
            raw = hits[0]
        except Exception as exc:
            logger.info("[ConfigStore] legacy sync_offsets not found or unreadable: %s", exc)
            return {}

        offsets: dict[int, int] = {}
        for key, value in raw.items():
            if key == "id":
                continue
            try:
                did = int(key)
            except (TypeError, ValueError):
                continue
            offsets[did] = self._clamp_latest_msg_id(value)
        return offsets

    def _try_migrate_from_legacy_meili(self, conn: sqlite3.Connection) -> bool:
        if self._meili is None:
            return False

        try:
            raw_doc = self._meili.client.index(self._index_name).get_document(_DOC_ID)
        except Exception as exc:
            err = str(exc).lower()
            if "not_found" in err or "document_not_found" in err or "404" in err:
                return False
            logger.warning("[ConfigStore] legacy config read failed: %s", exc)
            return False

        try:
            raw = dict(raw_doc.__dict__) if hasattr(raw_doc, "__dict__") else dict(raw_doc)
            cfg = GlobalConfig.model_validate(raw)
        except Exception as exc:
            logger.warning("[ConfigStore] legacy config invalid, skip migration: %s", exc)
            return False

        legacy_offsets = self._load_legacy_offsets()
        conn.execute("BEGIN IMMEDIATE")
        try:
            self._persist_sections(conn, cfg)
            self._write_meta(conn, version=cfg.version, updated_at=cfg.updated_at)
            self._replace_dialog_states(conn, {k: v.model_dump() for k, v in cfg.sync.dialogs.items()})
            if legacy_offsets:
                for did, latest_msg_id in legacy_offsets.items():
                    conn.execute(
                        """
                        INSERT INTO dialog_state (
                            dialog_id, sync_state, latest_msg_id, date_from, last_synced_at, updated_at
                        ) VALUES (?, 'inactive', ?, NULL, NULL, ?)
                        ON CONFLICT(dialog_id) DO UPDATE SET
                            latest_msg_id = excluded.latest_msg_id
                        """,
                        (did, latest_msg_id, _now_iso()),
                    )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

        logger.info(
            "[ConfigStore] migrated legacy config from Meili index=%s dialogs=%d offsets=%d",
            self._index_name,
            len(cfg.sync.dialogs),
            len(legacy_offsets),
        )
        return True

    # ---- 公开接口 ----

    def load_config(self, refresh: bool = False) -> GlobalConfig:
        """
        读取全局配置。

        Args:
            refresh: True 时强制绕过缓存。
        """
        if not refresh:
            cached = self._cache.get()
            if cached is not None:
                logger.info("[ConfigStore] load_config: cache_hit=true version=%d", cached.version)
                return cached

        t0 = time.monotonic()
        with self._lock:
            with self._connect() as conn:
                config = self._read_config_from_conn(conn)
        elapsed_ms = (time.monotonic() - t0) * 1000
        if elapsed_ms > _READ_WARN_MS:
            logger.warning(
                "[ConfigStore] load_config slow: %.1fms (threshold=%dms) cache_hit=false version=%d",
                elapsed_ms,
                _READ_WARN_MS,
                config.version,
            )
        else:
            logger.info(
                "[ConfigStore] load_config: %.1fms cache_hit=false version=%d",
                elapsed_ms,
                config.version,
            )
        self._cache.set(config)
        return config

    def save_config(
        self,
        patch: dict[str, Any],
        expected_version: int | None = None,
    ) -> GlobalConfig:
        """
        写入配置（兼容旧接口）。

        Args:
            patch: section 级 patch（`sync/storage/ai/policy`）或顶级字段 patch。
            expected_version: 可选 optimistic lock。
        """
        t0 = time.monotonic()
        with self._lock:
            with self._connect() as conn:
                conn.execute("BEGIN IMMEDIATE")
                try:
                    current = self._read_config_from_conn(conn)

                    if expected_version is not None and current.version != expected_version:
                        raise ValueError(
                            f"[ConfigStore] version conflict: expected {expected_version}, got {current.version}"
                        )

                    merged = current.model_dump()
                    for key, value in patch.items():
                        if key in ("sync", "storage", "ai", "policy") and isinstance(value, dict):
                            merged[key].update(value)
                        else:
                            merged[key] = value

                    merged["version"] = current.version + 1
                    merged["updated_at"] = _now_iso()
                    new_config = GlobalConfig.model_validate(merged)

                    self._persist_sections(conn, new_config)
                    if isinstance(patch.get("sync"), dict):
                        sync_patch = patch["sync"]
                        if "dialogs" in sync_patch and isinstance(sync_patch["dialogs"], dict):
                            self._replace_dialog_states(conn, sync_patch["dialogs"])
                    self._write_meta(conn, version=new_config.version, updated_at=new_config.updated_at)
                    conn.execute("COMMIT")
                except Exception:
                    conn.execute("ROLLBACK")
                    raise

        elapsed_ms = (time.monotonic() - t0) * 1000
        if elapsed_ms > _WRITE_WARN_MS:
            logger.warning(
                "[ConfigStore] save_config slow: %.1fms (threshold=%dms) version=%d changed_sections=%s",
                elapsed_ms,
                _WRITE_WARN_MS,
                new_config.version,
                list(patch.keys()),
            )
        else:
            logger.info(
                "[ConfigStore] save_config: %.1fms version=%d changed_sections=%s",
                elapsed_ms,
                new_config.version,
                list(patch.keys()),
            )

        self._cache.invalidate()
        self._cache.set(new_config)
        return new_config

    def update_section(
        self,
        section: Literal["sync", "storage", "ai", "policy"],
        patch: dict[str, Any],
    ) -> GlobalConfig:
        """Section 级更新辅助函数。"""
        return self.save_config({section: patch})

    def upsert_dialog_states(self, dialog_states: dict[int | str, dict[str, Any] | DialogSyncState]) -> GlobalConfig:
        """
        粒度化 upsert 对话状态（不会覆盖其他 dialog 行）。

        每次批量 upsert 仅做一次 version 递增。
        """
        if not dialog_states:
            return self.load_config(refresh=True)

        t0 = time.monotonic()
        with self._lock:
            with self._connect() as conn:
                conn.execute("BEGIN IMMEDIATE")
                try:
                    current = self._read_config_from_conn(conn)
                    self._upsert_dialog_states(conn, dialog_states)
                    next_version = current.version + 1
                    updated_at = _now_iso()
                    self._write_meta(conn, version=next_version, updated_at=updated_at)
                    cfg = self._read_config_from_conn(conn)
                    conn.execute("COMMIT")
                except Exception:
                    conn.execute("ROLLBACK")
                    raise

        elapsed_ms = (time.monotonic() - t0) * 1000
        logger.info(
            "[ConfigStore] upsert_dialog_states count=%d version=%d duration_ms=%.1f",
            len(dialog_states),
            cfg.version,
            elapsed_ms,
        )
        self._cache.invalidate()
        self._cache.set(cfg)
        return cfg

    def delete_dialog_state(self, dialog_id: int) -> bool:
        """删除单个 dialog 同步状态。存在时返回 True。"""
        removed = False
        with self._lock:
            with self._connect() as conn:
                conn.execute("BEGIN IMMEDIATE")
                try:
                    row = conn.execute("DELETE FROM dialog_state WHERE dialog_id = ?", (dialog_id,))
                    removed = row.rowcount > 0
                    if removed:
                        current = self._read_config_from_conn(conn)
                        self._write_meta(conn, version=current.version + 1, updated_at=_now_iso())
                    conn.execute("COMMIT")
                except Exception:
                    conn.execute("ROLLBACK")
                    raise

        if removed:
            self._cache.invalidate()
        return removed

    def get_latest_msg_id(self, dialog_id: int) -> int:
        """获取 dialog 的增量断点（latest_msg_id）。"""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT latest_msg_id FROM dialog_state WHERE dialog_id = ?",
                (dialog_id,),
            ).fetchone()
        if row is None:
            return 0
        return self._clamp_latest_msg_id(row["latest_msg_id"])

    def set_latest_msg_id(self, dialog_id: int, latest_msg_id: int) -> None:
        """
        更新 dialog 的增量断点。

        该更新属于高频运行时状态，不递增 GlobalConfig.version。
        """
        clamped = self._clamp_latest_msg_id(latest_msg_id)
        with self._lock:
            with self._connect() as conn:
                conn.execute("BEGIN IMMEDIATE")
                try:
                    conn.execute(
                        """
                        INSERT INTO dialog_state (
                            dialog_id, sync_state, latest_msg_id, date_from, last_synced_at, updated_at
                        ) VALUES (?, 'inactive', ?, NULL, NULL, ?)
                        ON CONFLICT(dialog_id) DO UPDATE SET
                            latest_msg_id = excluded.latest_msg_id
                        """,
                        (dialog_id, clamped, _now_iso()),
                    )
                    conn.execute("COMMIT")
                except Exception:
                    conn.execute("ROLLBACK")
                    raise

    def get_latest_msg_map(self) -> dict[str, int]:
        """读取所有 dialog 的 latest_msg_id 映射（用于兼容旧调用链）。"""
        with self._connect() as conn:
            rows = conn.execute("SELECT dialog_id, latest_msg_id FROM dialog_state").fetchall()
        result: dict[str, int] = {"id": 0}
        for row in rows:
            did = int(row["dialog_id"])
            result[str(did)] = self._clamp_latest_msg_id(row["latest_msg_id"])
        return result
