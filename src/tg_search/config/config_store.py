"""
P0 Config Store - 统一配置持久化基座

为系统提供基于 MeiliSearch 的运行时配置读写能力，支持：
- 首次启动自动初始化默认配置
- 10s 内存缓存（命中时不访问 MeiliSearch）
- 乐观锁 version 递增控制
- 结构损坏时自动回退默认值
- section 级辅助更新函数

索引：system_config
文档：id = "global"
接口（内部模块，不对外暴露）：
    load_config(refresh: bool = False) -> GlobalConfig
    save_config(patch: dict, expected_version: int | None = None) -> GlobalConfig
    update_section(section: Literal["sync", "storage", "ai"], patch: dict) -> GlobalConfig
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from tg_search.core.logger import setup_logger
from tg_search.core.meilisearch import MeiliSearchClient

logger = setup_logger()

_INDEX_NAME = "system_config"
_DOC_ID = "global"
_CACHE_TTL_SEC = 10


# ============ Pydantic Models (T-P0-CS-01) ============


class DialogSyncState(BaseModel):
    """单个对话的同步状态"""

    sync_state: str = "inactive"
    last_synced_at: str | None = None
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SyncConfig(BaseModel):
    """Dialog Sync 相关配置"""

    dialogs: dict[str, DialogSyncState] = Field(default_factory=dict)
    available_cache_ttl_sec: int = 120


class StorageConfig(BaseModel):
    """Storage 相关配置"""

    auto_clean_enabled: bool = False
    media_retention_days: int = 30


class AiConfig(BaseModel):
    """AI 供应商配置"""

    provider: str = "openai_compatible"
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    api_key: str = ""


class GlobalConfig(BaseModel):
    """全局配置文档（MeiliSearch system_config 索引中的唯一文档）"""

    id: str = _DOC_ID
    version: int = 0
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    sync: SyncConfig = Field(default_factory=SyncConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    ai: AiConfig = Field(default_factory=AiConfig)


# ============ Cache ============


class _Cache:
    """简单内存缓存，支持 TTL 失效"""

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


# ============ ConfigStore (T-P0-CS-02 ~ T-P0-CS-05) ============


class ConfigStore:
    """
    统一配置持久化服务。

    内部缓存 TTL = 10s，写后主动清除缓存。

    Args:
        meili: MeiliSearchClient 实例
        index_name: 使用的索引名（默认 "system_config"，测试可覆盖）
    """

    def __init__(self, meili: MeiliSearchClient, index_name: str = _INDEX_NAME) -> None:
        self._meili = meili
        self._index_name = index_name
        self._cache = _Cache()
        self._ensure_index()

    # ---- 私有方法 ----

    def _ensure_index(self) -> None:
        """T-P0-CS-02: 幂等创建 system_config 索引（已存在时不报错）"""
        try:
            self._meili.client.create_index(self._index_name, {"primaryKey": "id"})
            logger.info(f"[ConfigStore] Index '{self._index_name}' created or already exists")
        except Exception as e:
            # 索引已存在是正常情况，其他错误向上传播
            if "index_already_exists" not in str(e).lower():
                logger.error(f"[ConfigStore] Failed to create index '{self._index_name}': {e}")
                raise

    def _fetch_from_meili(self) -> GlobalConfig:
        """从 MeiliSearch 获取配置文档，并将其解析为 GlobalConfig。若文档不存在或结构损坏则回退默认值。"""
        index = self._meili.client.index(self._index_name)
        try:
            raw_doc = index.get_document(_DOC_ID)
            # MeiliSearch SDK 返回的是 Document 对象（有 __dict__），需要转为普通 dict
            if hasattr(raw_doc, "__dict__"):
                raw: dict[str, Any] = dict(raw_doc.__dict__)
            else:
                raw = dict(raw_doc)
            config = GlobalConfig.model_validate(raw)
            return config
        except ValidationError as e:
            logger.warning(f"[ConfigStore] Config document schema invalid, falling back to defaults. Error: {e}")
            default_config = GlobalConfig()
            self._write_to_meili(default_config)
            return default_config
        except Exception as e:
            err_msg = str(e).lower()
            if "not_found" in err_msg or "document_not_found" in err_msg or "404" in err_msg:
                # 文档不存在 -> 首次启动初始化
                logger.info("[ConfigStore] No config document found, initializing with defaults")
                default_config = GlobalConfig()
                self._write_to_meili(default_config)
                return default_config
            logger.warning(f"[ConfigStore] Unexpected error reading config, falling back to defaults: {e}")
            return GlobalConfig()

    def _write_to_meili(self, config: GlobalConfig) -> None:
        """将 GlobalConfig 写入 MeiliSearch，并记录结构化日志"""
        t0 = time.monotonic()
        index = self._meili.client.index(self._index_name)
        doc = config.model_dump()
        index.add_documents([doc])
        elapsed_ms = (time.monotonic() - t0) * 1000
        # 监控点：写入延迟（规格要求 ≤500ms）
        if elapsed_ms > 500:
            logger.warning(
                "[ConfigStore] _write_to_meili slow: %.1fms (threshold=500ms) version=%d",
                elapsed_ms,
                config.version,
            )
        else:
            logger.info(
                "[ConfigStore] _write_to_meili: %.1fms version=%d",
                elapsed_ms,
                config.version,
            )

    # ---- 公开接口（T-P0-CS-03 / 04 / 05）----

    def load_config(self, refresh: bool = False) -> GlobalConfig:
        """
        T-P0-CS-03: 读取全局配置。

        Args:
            refresh: True 时强制绕过缓存，直接从 MeiliSearch 读取。

        Returns:
            GlobalConfig: 当前配置（缓存命中时返回缓存值）
        """
        if not refresh:
            cached = self._cache.get()
            if cached is not None:
                # 监控点：缓存命中（规格要求 ≤100ms，缓存命中远低于此目标）
                logger.info(
                    "[ConfigStore] load_config: cache_hit=true version=%d",
                    cached.version,
                )
                return cached

        t0 = time.monotonic()
        config = self._fetch_from_meili()
        elapsed_ms = (time.monotonic() - t0) * 1000
        # 监控点：读取延迟（规格要求 ≤100ms，来自 MeiliSearch 而非缓存）
        if elapsed_ms > 100:
            logger.warning(
                "[ConfigStore] load_config slow: %.1fms (threshold=100ms) cache_hit=false version=%d",
                elapsed_ms,
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
        T-P0-CS-04: 写入配置（乐观锁 version 递增控制）。

        Args:
            patch: 要更新的字段，支持 section 级（如 {"storage": {"auto_clean_enabled": True}}）
                   或顶级字段（如 {"version": 5}）。
            expected_version: 若指定，须与当前文档 version 一致，否则抛出 ValueError（并发冲突防护）。

        Returns:
            GlobalConfig: 写入后的新配置

        Raises:
            ValueError: expected_version 与当前 version 不符
        """
        current = self.load_config(refresh=True)

        # 乐观锁检查
        if expected_version is not None and current.version != expected_version:
            raise ValueError(f"[ConfigStore] version conflict: expected {expected_version}, got {current.version}")

        # 合并 patch 到当前配置
        current_dict = current.model_dump()
        for key, value in patch.items():
            if key in ("sync", "storage", "ai") and isinstance(value, dict):
                # Section 级合并
                current_dict[key].update(value)
            else:
                current_dict[key] = value

        # version 递增 + 时间戳更新
        current_dict["version"] = current.version + 1
        current_dict["updated_at"] = datetime.now(timezone.utc).isoformat()

        new_config = GlobalConfig.model_validate(current_dict)

        # 结构化写操作日志
        logger.info(
            "[ConfigStore] save_config: version=%d->%d, changed_sections=%s",
            current.version,
            new_config.version,
            list(patch.keys()),
        )

        self._write_to_meili(new_config)
        # 写后主动失效缓存
        self._cache.invalidate()
        # 更新缓存为最新值
        self._cache.set(new_config)

        return new_config

    def update_section(
        self,
        section: Literal["sync", "storage", "ai"],
        patch: dict[str, Any],
    ) -> GlobalConfig:
        """
        T-P0-CS-05: Section 级更新辅助函数。

        Args:
            section: 要更新的配置节（"sync" | "storage" | "ai"）
            patch: 该节内的字段更新

        Returns:
            GlobalConfig: 写入后的新配置
        """
        return self.save_config({section: patch})
