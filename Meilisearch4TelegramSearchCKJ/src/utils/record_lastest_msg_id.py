import configparser


def read_config(filename="config.ini"):
    """读取配置文件"""
    config = configparser.ConfigParser()
    config.read(filename)
    if "latest_msg_id" not in config:
        config["latest_msg_id"] = {}
    if "latest_msg_date" not in config:
        config["latest_msg_date"] = {}
    return config


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
