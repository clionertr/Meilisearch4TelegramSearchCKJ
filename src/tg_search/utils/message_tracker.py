import configparser
import threading
from typing import Any

from tg_search.core.meilisearch import MeiliSearchClient


def read_config(filename="config.ini"):
    """读取配置文件"""
    config = configparser.ConfigParser()
    config.read(filename)
    if "latest_msg_id" not in config:
        config["latest_msg_id"] = {}
    if "latest_msg_date" not in config:
        config["latest_msg_date"] = {}
    return config


def update_latest_msg_config(
    peer_id: int | str,
    message: dict[str, Any],
    config: configparser.ConfigParser,
) -> None:
    # Message ID format is "{chat_id}-{msg_id}".
    # chat_id may be negative, so split("-")[1] is unsafe for cases like "-123-456".
    config["latest_msg_id"][str(peer_id)] = str(str(message["id"]).rsplit("-", 1)[-1])
    config["latest_msg_date"][str(peer_id)] = str(message["date"])
    write_config(config)


def write_config(config, filename="config.ini"):
    """写入配置文件"""
    with open(filename, "w") as configfile:
        config.write(configfile)


def get_latest_msg_id(config, chat_id: str | int):
    """获取最新消息ID"""
    if isinstance(chat_id, int):
        chat_id = str(chat_id)
        return int(config.get("latest_msg_id", chat_id, fallback=0))
    else:
        return int(config.get("latest_msg_id", chat_id, fallback=0))


def read_config_from_meili(meili: MeiliSearchClient):
    """兼容旧接口：从 SQLite 读取 latest_msg_id 映射。"""
    try:
        store = _get_config_store(meili)
        return store.get_latest_msg_map()
    except Exception as e:
        print(f"Failed to read config from SQLite ConfigStore: {str(e)}")
        return {"id": 0}


def write_config2_meili(meili: MeiliSearchClient, config):
    """兼容旧接口：将 latest_msg_id 映射写入 SQLite。"""
    try:
        store = _get_config_store(meili)
        for key, value in config.items():
            if key == "id":
                continue
            try:
                dialog_id = int(key)
            except (TypeError, ValueError):
                continue
            try:
                latest_msg_id = int(value)
            except (TypeError, ValueError):
                continue
            store.set_latest_msg_id(dialog_id, latest_msg_id)
    except Exception as e:
        print(f"Failed to write config to SQLite ConfigStore: {str(e)}")


def get_latest_msg_id4_meili(config, chat_id: int):
    """获取最新消息ID"""
    try:
        chat_key = str(chat_id)
        value = int(config[chat_key])
        # Telegram GetHistoryRequest.offset_id is signed int32.
        # Old buggy data may contain chat_id values here (e.g. 5121831212), reset to 0.
        if value < 0 or value > 2_147_483_647:
            return 0
        return value
    except KeyError:
        return 0
    except (TypeError, ValueError):
        return 0


async def update_latest_msg_config4_meili(
    dialog_id: int,
    message: dict[str, Any],
    config: dict[str, Any],
    meili: MeiliSearchClient,
) -> None:
    # Message ID format is "{chat_id}-{msg_id}" and chat_id may be negative.
    # Use rsplit to always extract msg_id safely.
    msg_id = int(str(message["id"]).rsplit("-", 1)[-1])
    config[str(dialog_id)] = msg_id
    store = _get_config_store(meili)
    import asyncio

    await asyncio.to_thread(store.set_latest_msg_id, dialog_id, msg_id)


_STORE_LOCK = threading.Lock()
_STORE_CACHE: dict[int, Any] = {}


def _get_config_store(meili: MeiliSearchClient):
    """
    懒加载 ConfigStore（兼容旧 message_tracker API）。

    这里不直接暴露到模块顶层 import，避免启动时引入循环依赖风险。
    """
    cache_key = id(meili)
    with _STORE_LOCK:
        store = _STORE_CACHE.get(cache_key)
        if store is not None:
            return store
        from tg_search.config.config_store import ConfigStore

        store = ConfigStore(meili)
        _STORE_CACHE[cache_key] = store
        return store
