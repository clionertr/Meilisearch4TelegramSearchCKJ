from tg_search.utils.message_tracker import get_latest_msg_id, read_config, write_config

config = read_config()
# write_config(config)
print(get_latest_msg_id(config, 'Qikan2023'))
