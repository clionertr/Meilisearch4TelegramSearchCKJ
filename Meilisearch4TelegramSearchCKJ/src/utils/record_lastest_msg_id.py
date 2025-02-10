import toml


def load_config(file_path='config/settings.toml'):
    """读取 TOML 配置文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        config = toml.load(f)
    return config


def save_config(config, file_path='config/settings.toml'):
    """将配置写回 TOML 文件"""
    with open(file_path, 'w', encoding='utf-8') as f:
        toml.dump(config, f)


def modify_config():
    # 加载现有配置
    config = load_config()
    # 将修改后的配置写回文件
    save_config(config)
    print("配置文件已更新。")


def update_download_incremental(dialog_id, message, config):
    config['download_incremental'][str(dialog_id)] = int(message["id"].split('-')[1])
    save_config(config)

