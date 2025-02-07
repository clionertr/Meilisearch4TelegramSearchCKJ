import os
from telethon.sync import TelegramClient

api_id = os.getenv('APP_ID', '12345')
api_hash = os.getenv('APP_HASH', '0123456789abcdef0123456789abcdef')

with TelegramClient('user_bot_session', api_id, api_hash) as client:
    client.send_message('me', '已生成session文件')
    print(client.download_profile_photo('me'))
    client.run_until_disconnected()
