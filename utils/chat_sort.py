import pandas as pd
import glob
import os

# === チャットCSVのフォルダ ===
CHAT_DIR = "data/chat"
csv_files = glob.glob(os.path.join(CHAT_DIR, "*.csv"))

if not csv_files:
    print("❌ 並び替え対象のCSVが見つかりません。")
else:
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file, parse_dates=["timestamp"])
            df.sort_values(by="timestamp", inplace=True)
            df.to_csv(csv_file, index=False)
            print(f"✅ 並び替え＆保存完了: {csv_file}")
        except Exception as e:
            print(f"⚠️ 処理失敗: {csv_file} - エラー: {e}")
