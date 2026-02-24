"""
Config 包

导出 ConfigStore 及相关模型。
使用延迟导入避免循环引用（config_store → logger → settings → config）。
"""

__all__ = [
    "ConfigStore",
    "GlobalConfig",
    "SyncConfig",
    "StorageConfig",
    "AiConfig",
    "DialogSyncState",
]


def __getattr__(name: str):
    """PEP 562: 延迟导入，避免 config_store ↔ logger ↔ settings 循环引用"""
    if name in __all__:
        from tg_search.config.config_store import (
            AiConfig,
            ConfigStore,
            DialogSyncState,
            GlobalConfig,
            StorageConfig,
            SyncConfig,
        )

        _exports = {
            "ConfigStore": ConfigStore,
            "GlobalConfig": GlobalConfig,
            "SyncConfig": SyncConfig,
            "StorageConfig": StorageConfig,
            "AiConfig": AiConfig,
            "DialogSyncState": DialogSyncState,
        }
        return _exports[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
