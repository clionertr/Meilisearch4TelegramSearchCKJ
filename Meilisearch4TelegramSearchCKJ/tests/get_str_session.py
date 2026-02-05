import os

from telethon.sessions import StringSession
from telethon.sync import TelegramClient

api_id = os.getenv('APP_ID', '12345')
api_hash = os.getenv('APP_HASH', '0123456789abcdef0123456789abcdef')
with TelegramClient(StringSession(), api_id, api_hash) as client:
    print('以下是你的string session（类似登陆密钥）\n')
    print(client.session.save())






