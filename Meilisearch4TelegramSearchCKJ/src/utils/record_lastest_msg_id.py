import configparser

from Meilisearch4TelegramSearchCKJ.src.models.meilisearch_handler import MeiliSearchClient


def read_config(filename="config.ini"):
    """读取配置文件"""
    config = configparser.ConfigParser()
    config.read(filename)
    if "latest_msg_id" not in config:
        config["latest_msg_id"] = {}
    if "latest_msg_date" not in config:
        config["latest_msg_date"] = {}
    return config


def update_latest_msg_config(peer_id, message, config):
    config["latest_msg_id"][str(peer_id)] = str(message["id"].split('-')[1])
    config["latest_msg_date"][str(peer_id)] = str(message["date"])
    write_config(config)


def write_config(config, filename="config.ini"):
    """写入配置文件"""
    with open(filename, 'w') as configfile:
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
    meili.create_index("config")
    try:
        client_bot_config = meili.search(None, "config", limit=1)
        return client_bot_config['hits'][0] if client_bot_config['hits'] else {'id':0}
    except Exception as e:
        print(f"Failed to read config from MeiliSearch: {str(e)}")
        return {'id':0}


def write_config2_meili(meili: MeiliSearchClient, config):
    """写入配置文件到Meilisearch"""
    try:
        meili.add_documents([config], "config")
    except Exception as e:
        print(f"Failed to write config to MeiliSearch: {str(e)}")



def get_latest_msg_id4_meili(config, chat_id: int):
    """获取最新消息ID"""
    try:
        chat_id = str(chat_id)
        return config[chat_id]
    except  KeyError:
        return 0

def update_latest_msg_config4_meili(dialog_id, message, config,meili):
    config[str(dialog_id)] = int(message["id"].split('-')[1])
    write_config2_meili(meili,config)