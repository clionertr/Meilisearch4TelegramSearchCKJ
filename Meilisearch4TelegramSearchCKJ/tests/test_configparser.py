from Meilisearch4TelegramSearchCKJ.src.utils.record_lastest_msg_id import get_latest_msg_id, read_config, write_config

config = read_config()
# write_config(config)
print(get_latest_msg_id(config, 'Qikan2023'))
