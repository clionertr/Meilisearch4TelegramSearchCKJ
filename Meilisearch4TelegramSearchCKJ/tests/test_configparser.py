from Meilisearch4TelegramSearchCKJ.src.utils.record_lastest_msg_id import read_config, write_config, get_latest_msg_id

config = read_config()
# write_config(config)
print(get_latest_msg_id(config, 'Qikan2023'))