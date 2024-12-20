from telethon.sync import TelegramClient
from telethon.sessions import StringSession

from Meilisearch4TelegramSearchCKJ.src.config.env import APP_ID, APP_HASH

api_id = APP_ID
api_hash = APP_HASH
with TelegramClient(StringSession(), api_id, api_hash) as client:
    print('以下是你的string session（类似登陆密钥）\n')
    print(client.session.save())






