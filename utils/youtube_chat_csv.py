import time
import pandas as pd
from datetime import timedelta
from googleapiclient.discovery import build
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import re

# === 設定 ===
API_KEY = "AIzaSyDvT9BJC3NIuGMOQr5L_T9MR9WkjToP13k"  # 🔁 あなたのAPIキーを入力
VIDEO_IDS = ["HiVhpqfzmOQ", "QqbmZw14ar4", "0N77o0cGpZY", "uIWLpqerU80", "5Vn38n97fTE", "hqY5CHZFGE4", "CxELR4SJbfk", "i5O3E89SnsI", "ziwMoyUvAbo", "y71nsIr7kKU"]  # 🔁 任意の動画IDリスト
#Talk Football HD, Real Madrid, YjR, L' immigré parisien, Divyansh, Markaroni, Carrusel Deportivo, Tiempo de Juego COPE, TOTAL FOOTBALL, goat
SAVE_DIR = "data/chat"
INTERVAL_SECONDS = 120
MAX_WORKERS = 10  # 並列数（適宜調整）

# === フォルダ作成 ===
os.makedirs(SAVE_DIR, exist_ok=True)

def sanitize_filename(text):
    return re.sub(r'[\\/*?:"<>|]', '_', text)

def collect_chat_until_end(video_id):
    youtube = build("youtube", "v3", developerKey=API_KEY)
    chat_data = []

    try:
        video_response = youtube.videos().list(
            part="snippet,liveStreamingDetails",
            id=video_id
        ).execute()

        item = video_response["items"][0]
        live_details = item.get("liveStreamingDetails", {})
        title = item["snippet"].get("title", "Untitled")
        title_clean = sanitize_filename(title)
        live_chat_id = live_details.get("activeLiveChatId")

        if not live_chat_id:
            print(f"⚠️ {video_id}（{title}）はすでに終了 or チャット無効です。")
            return

        file_name = f"{SAVE_DIR}/{title_clean}_chat_log.csv"

        print(f"🔁 チャット収集開始: {video_id}（{title}）")

        while True:
            try:
                response = youtube.liveChatMessages().list(
                    liveChatId=live_chat_id,
                    part="snippet,authorDetails",
                    maxResults=200
                ).execute()

                items = response.get("items", [])
                for item in items:
                    snippet = item.get("snippet", {})
                    author_info = item.get("authorDetails", {})
                    message = snippet.get("displayMessage")
                    if message:
                        timestamp = pd.to_datetime(snippet.get("publishedAt")) + timedelta(hours=9)
                        author = author_info.get("displayName", "Unknown")
                        channel_id = author_info.get("channelId", "Unknown")
                        chat_data.append({
                            "timestamp": timestamp,
                            "author": author,
                            "authorChannelId": channel_id,
                            "message": message
                        })

                print(f"[{video_id}] ✅ {len(items)}件取得")
                time.sleep(INTERVAL_SECONDS)

            except Exception as e:
                if "liveChat not found" in str(e) or "403" in str(e):
                    print(f"🛑 {video_id}（{title}）のライブが終了しました。保存に移行します。")
                    break
                else:
                    print(f"⚠️ {video_id} エラー: {e}")
                    time.sleep(10)

        df = pd.DataFrame(chat_data)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df.to_csv(file_name, index=False)
        print(f"💾 保存完了: {file_name}")

    except Exception as e:
        print(f"❌ 初期処理失敗 ({video_id}): {e}")


# === 並列実行 ===
with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    futures = [executor.submit(collect_chat_until_end, vid) for vid in VIDEO_IDS]
    for future in as_completed(futures):
        future.result()