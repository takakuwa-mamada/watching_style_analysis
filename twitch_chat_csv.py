import os
import re
import pandas as pd
from datetime import datetime, timedelta
import asyncio
from twitchio.ext import commands
import aiohttp

# === 設定 ===
TWITCH_CHANNELS = ['sasatikk']  # ✅ 対象チャンネルを指定
SAVE_DIR = 'data/chat'
TWITCH_TOKEN = 'oauth:h9kr13nqsmfo6r0glfxp0fbj1a34do'  # ✅ Access Token（"oauth:"付き）
TWITCH_NICK = 'mamada_lab'
CLIENT_ID = 'gp762nuuoqcoxypju8c569th9wz7q5'  # ✅ Client ID
CHECK_INTERVAL_SECONDS = 60  # 視聴者数チェック間隔（秒）

# === 保存フォルダ作成 ===
os.makedirs(SAVE_DIR, exist_ok=True)

def sanitize_filename(text):
    return re.sub(r'[\\/*?:"<>|]', "_", text)

# === user_id を自動取得 ===
async def get_user_id(channel_name):
    url = f'https://api.twitch.tv/helix/users?login={channel_name}'
    headers = {
        'Client-ID': CLIENT_ID,
        'Authorization': f'Bearer {TWITCH_TOKEN.replace("oauth:", "")}'
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            data = await resp.json()
            print(f"🔍 Twitch API response for '{channel_name}':", data)

            if 'data' in data and len(data['data']) > 0:
                return data['data'][0]['id']
            else:
                raise ValueError(f"⚠️ user_idが取得できませんでした: {channel_name}")

# === チャット収集Botクラス ===
class ChatCollector(commands.Bot):
    def __init__(self, channel_name, twitch_user_id):
        super().__init__(token=TWITCH_TOKEN, prefix='!', initial_channels=[channel_name])
        self.channel_name = channel_name
        self.twitch_user_id = twitch_user_id  # ← 変数名を変更
        self.chat_data = []
        self.loop_running = True

    async def event_ready(self):
        print(f"✅ 接続完了: {self.channel_name}")

    async def event_message(self, message):
        if message.echo:
            return
        timestamp = datetime.now()
        self.chat_data.append({
            'timestamp': timestamp + timedelta(hours=9),
            'author': message.author.name,
            'author_id': message.author.id,
            'message': message.content
        })

    async def save_and_close(self):
        self.loop_running = False
        df = pd.DataFrame(self.chat_data)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        file_name = f"{SAVE_DIR}/{sanitize_filename(self.channel_name)}_chat_log.csv"
        df.to_csv(file_name, index=False)
        print(f"💾 {self.channel_name} のチャットを保存しました: {file_name}")
        await self.stop()  # ← ここを修正！


    async def monitor_stream(self):
        headers = {
            'Client-ID': CLIENT_ID,
            'Authorization': f'Bearer {TWITCH_TOKEN.replace("oauth:", "")}'
        }
        url = f'https://api.twitch.tv/helix/streams?user_id={self.twitch_user_id}'  # ← 修正

        async with aiohttp.ClientSession() as session:
            while self.loop_running:
                async with session.get(url, headers=headers) as resp:
                    data = await resp.json()
                    is_live = bool(data.get("data"))
                    if not is_live:
                        print(f"🛑 配信が終了したと判断（{self.channel_name}）")
                        await self.save_and_close()
                        break
                    else:
                        print(f"📡 {self.channel_name} 配信中... コメント収集中")
                await asyncio.sleep(CHECK_INTERVAL_SECONDS)

    async def run_forever(self):
        await asyncio.gather(
            self.start(),
            self.monitor_stream()
        )

# === メイン処理 ===
async def main():
    for channel in TWITCH_CHANNELS:
        try:
            print(f"🔍 {channel} の user_id を取得中...")
            user_id = await get_user_id(channel)
            print(f"🔑 {channel} の user_id: {user_id}")

            bot = ChatCollector(channel, user_id)
            await bot.run_forever()
            print(f"✅ {channel} 完了\n")
            await asyncio.sleep(5)

        except Exception as e:
            print(f"❌ エラー: {channel} - {e}")

if __name__ == '__main__':
    asyncio.run(main())
