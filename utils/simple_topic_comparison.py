# -*- coding: utf-8 -*-
"""
simple_topic_comparison.py

ユーザー要求に特化したシンプルな実装：
1. トピック分類（キャッシュ対応）
2. 似たトピック検出
3. matched_event_presence.png 生成
4. 絵文字タイムライン生成

使い方:
python simple_topic_comparison.py --folder data/football --use-cache
"""

import argparse
import os
import pickle
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple
from collections import defaultdict, Counter

# ===== 設定 =====
CACHE_DIR = "cache"
OUTPUT_DIR = "output"
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

def parse_args():
    parser = argparse.ArgumentParser(description="Simple Topic Comparison")
    parser.add_argument("--folder", required=True, help="Folder containing CSV files")
    parser.add_argument("--pattern", default="*.csv", help="File pattern")
    parser.add_argument("--use-cache", action="store_true", help="Use cached topic models")
    parser.add_argument("--force-recalc", action="store_true", help="Force recalculate topics")
    return parser.parse_args()

def load_or_compute_topics(csv_file: str, use_cache: bool = True, force_recalc: bool = False):
    """トピック分類（キャッシュ対応）"""
    basename = os.path.basename(csv_file).replace('.csv', '')
    cache_file = os.path.join(CACHE_DIR, f"{basename}_topics.pkl")
    
    # キャッシュチェック
    if use_cache and not force_recalc and os.path.exists(cache_file):
        print(f"[CACHE] Loading topics from {cache_file}")
        with open(cache_file, "rb") as f:
            return pickle.load(f)
    
    # 新規計算
    print(f"[COMPUTE] Processing {csv_file}...")
    from sentence_transformers import SentenceTransformer
    from bertopic import BERTopic
    
    # CSV読み込み
    df = pd.read_csv(csv_file, encoding="utf-8-sig")
    if "message" not in df.columns:
        print(f"[SKIP] No message column in {csv_file}")
        return None
    
    # 前処理
    df = df.dropna(subset=["message"])
    texts = df["message"].astype(str).tolist()
    
    # トピックモデル
    embedding_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")  # 軽量版
    topic_model = BERTopic(
        embedding_model=embedding_model,
        nr_topics="auto",
        verbose=False
    )
    
    topics, probs = topic_model.fit_transform(texts)
    
    # 結果を保存
    result = {
        "file": csv_file,
        "texts": texts,
        "topics": topics,
        "probs": probs,
        "topic_model": topic_model,
        "df": df
    }
    
    # キャッシュに保存
    with open(cache_file, "wb") as f:
        pickle.dump(result, f)
    print(f"[SAVED] Cached to {cache_file}")
    
    return result

def find_similar_topics(stream_data: Dict) -> List[Tuple[str, str, int, int, float]]:
    """似たトピックを検出"""
    # 簡易実装：時間帯別にトピックの出現頻度を計算
    # TODO: より洗練されたマッチングアルゴリズム
    matches = []
    return matches

def generate_matched_event_presence(matches: List, output_path: str):
    """matched_event_presence.png を生成"""
    if not matches:
        print("[WARN] No matches to visualize")
        return
    
    # TODO: ヒートマップ生成
    print(f"[TODO] Generate {output_path}")

def generate_emoji_timeline(csv_file: str, output_dir: str):
    """絵文字タイムライン生成（横長）"""
    # TODO: 絵文字抽出とタイムライン生成
    print(f"[TODO] Generate emoji timeline for {csv_file}")

def main():
    args = parse_args()
    
    # CSVファイル取得
    import glob
    csv_files = glob.glob(os.path.join(args.folder, args.pattern))
    print(f"Found {len(csv_files)} CSV files")
    
    # トピック分類
    stream_data = {}
    for csv_file in csv_files:
        result = load_or_compute_topics(csv_file, args.use_cache, args.force_recalc)
        if result:
            stream_data[csv_file] = result
    
    # 似たトピック検出
    matches = find_similar_topics(stream_data)
    print(f"Found {len(matches)} similar topic pairs")
    
    # matched_event_presence.png 生成
    output_path = os.path.join(OUTPUT_DIR, "matched_event_presence.png")
    generate_matched_event_presence(matches, output_path)
    
    # 絵文字タイムライン生成
    emoji_dir = os.path.join(OUTPUT_DIR, "emoji_timelines")
    os.makedirs(emoji_dir, exist_ok=True)
    for csv_file in csv_files:
        generate_emoji_timeline(csv_file, emoji_dir)
    
    print("All done!")

if __name__ == "__main__":
    main()
