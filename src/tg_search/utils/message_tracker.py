import configparser
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
    """从Meilisearch读取配置文件"""
    meili.create_index("sync_offsets")
    try:
        client_bot_config = meili.search(None, "sync_offsets", limit=1)
        return client_bot_config["hits"][0] if client_bot_config["hits"] else {"id": 0}
    except Exception as e:
        print(f"Failed to read config from MeiliSearch: {str(e)}")
        return {"id": 0}


def write_config2_meili(meili: MeiliSearchClient, config):
    """写入配置文件到Meilisearch"""
    try:
        meili.add_documents([config], "sync_offsets")
    except Exception as e:
        print(f"Failed to write config to MeiliSearch: {str(e)}")


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
    # This function is called from async download loops; avoid blocking the event loop.
    import asyncio

    await asyncio.to_thread(write_config2_meili, meili, config)
