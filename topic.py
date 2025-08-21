# -*- coding: utf-8 -*-
"""
YouTube/SNSコメントの国別・時系列トピック可視化（改良版）
- 上位10トピックのみを描画（凡例も上位10のみ）
- 日本語フォント自動設定（文字化け対策）
- 似通ったトピック（上位語が高Jaccard）の自動統合 → 凡例ラベルを人間可読に
- Windows での並列起動エラー回避（freeze_support / プロセス数制御）
- BERTopic の代表語抽出で埋め込みが必要になるケースに備え、embedding_model を明示設定
"""

import os
import re
import glob
import itertools
import warnings
from collections import defaultdict, Counter
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

# ===== Matplotlib（描画&日本語） =====
import matplotlib
matplotlib.use("Agg")  # GUI不要の環境でも保存できるように
import matplotlib.pyplot as plt
from matplotlib import font_manager, rcParams

# ---- 日本語フォント設定（文字化け対策） ----
JP_FONT_CANDIDATES = [
    "Meiryo", "Yu Gothic", "Yu Gothic UI", "MS Gothic",
    "Hiragino Sans", "Hiragino Kaku Gothic ProN",
    "Noto Sans CJK JP", "IPAGothic",
]
available_fonts = {f.name for f in font_manager.fontManager.ttflist}
chosen_font = None
for name in JP_FONT_CANDIDATES:
    if name in available_fonts:
        rcParams["font.family"] = name
        chosen_font = name
        break
else:
    # プロジェクト同梱フォント（任意）
    local_font = os.path.join(os.path.dirname(__file__), "fonts", "NotoSansCJKjp-Regular.otf")
    if os.path.exists(local_font):
        font_manager.fontManager.addfont(local_font)
        rcParams["font.family"] = "Noto Sans CJK JP"
        chosen_font = "Noto Sans CJK JP"

rcParams["axes.unicode_minus"] = False
print(f"[Matplotlib] Using font: {chosen_font or '<<not found - text may garble>>'}")

# ===== そのほかライブラリ =====
from langdetect import detect, DetectorFactory
DetectorFactory.seed = 42

from sentence_transformers import SentenceTransformer
from bertopic import BERTopic
from bertopic.representation import MaximalMarginalRelevance  # 代表語をわかりやすく
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics import silhouette_score
from umap import UMAP
from hdbscan import HDBSCAN

from gensim.corpora import Dictionary
from gensim.models.coherencemodel import CoherenceModel

warnings.filterwarnings("ignore", category=UserWarning)

# =====================
# 設定
# =====================
CHAT_DIR = "data/chat"   # チャットCSVの保存ディレクトリ
OUTPUT_DIR = "output"    # 結果出力先
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 多言語埋め込み（翻訳せずに直接ベクトル化）
EMB_NAME = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
embedding_model_global = SentenceTransformer(EMB_NAME)

# BERTopic の下回り（安定寄せ）
vectorizer_model = CountVectorizer(
    token_pattern=r"(?u)\b\w+\b", max_features=4000, min_df=2
)
umap_model = UMAP(
    n_components=5, n_neighbors=15, min_dist=0.00, metric="cosine", random_state=42
)
# Windowsの並列 spawn 回避のため core_dist_n_jobs=1 を強制
hdbscan_model = HDBSCAN(
    min_cluster_size=20,
    min_samples=5,
    metric="euclidean",
    cluster_selection_method="eom",
    prediction_data=True,
    core_dist_n_jobs=1,
)
# MMRは c-TF-IDF ベースで「代表語」が直感的 / embedding 不要
representation_model = MaximalMarginalRelevance(diversity=0.5)

# 参考：シードトピック（任意）
USE_SEED = True
seed_topic_list = [
    ["pitch", "strike", "ball", "fastball", "slider", "pitching"],
    ["bat", "homer", "home run", "slugger", "batting"],
    ["defense", "catch", "outfield", "infield", "double play"],
    ["umpire", "referee", "call", "review", "challenge"],
    ["injury", "hurt", "rehab", "out"],
    ["weather", "rain", "delay"],
    ["cheer", "chant", "song", "boo", "applause"],
    ["strategy", "tactics", "lineup", "substitution"],
]

# =====================
# ユーティリティ
# =====================
def preprocess_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = re.sub(r"http\S+|www\.\S+", " ", text)
    text = re.sub(r"@\w+", " ", text)
    text = re.sub(r"#\w+", " ", text)
    # 絵文字の超簡易置換
    text = (text.replace("😂", " laugh ")
                .replace("😭", " cry ")
                .replace("👏", " clap ")
                .replace("🔥", " fire "))
    # 記号を削除（CJKを残す）
    text = re.sub(r"[^\w\s\u4E00-\u9FFF\u3040-\u30FF\uAC00-\uD7AF]", " ", text)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text

def detect_lang_safe(text: str) -> str:
    try:
        return detect(text)
    except Exception:
        return "unk"

def parse_country_from_filename(path: str) -> str:
    name = os.path.basename(path)
    m = re.findall(r"(japan|japanese|jpn|india|indian|dominican|usa|korea|korean|mexico|taiwan|china|chinese|france)", name.lower())
    if m:
        return m[-1].capitalize()
    if re.search(r"[\u3040-\u30ff\u4e00-\u9faf]", name):
        return "Japan"
    return "Unknown"

def read_csv_any(path: str) -> pd.DataFrame:
    """エンコーディングを順に試して読む"""
    encodings = ["utf-8", "utf-8-sig", "cp932", "iso-8859-1"]
    for enc in encodings:
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:
            continue
    return pd.read_csv(path, engine="python")

# ------- トピック重複の自動統合（上位語のJaccardでクラスタリング） -------
def jaccard_set(a: set, b: set) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / (len(a | b) + 1e-12)

def build_topic_groups(words_by_tid: Dict[int, List[Tuple[str, float]]],
                       jaccard_threshold: float = 0.6) -> List[List[int]]:
    """
    上位語の集合が似ているトピックを統合する。
    - words_by_tid: {topic_id: [(word, weight), ...]}
    - return: [[topic_id, ...], ...] のグループ配列
    """
    tids = sorted([t for t in words_by_tid.keys() if t != -1])
    sets = {t: set(w for w, _s in words_by_tid[t][:10]) for t in tids}

    parent = {t: t for t in tids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[ry] = rx

    for i, ti in enumerate(tids):
        for tj in tids[i+1:]:
            if jaccard_set(sets[ti], sets[tj]) >= jaccard_threshold:
                union(ti, tj)

    groups = defaultdict(list)
    for t in tids:
        groups[find(t)].append(t)

    return list(groups.values())

def merged_label(words_by_tid: Dict[int, List[Tuple[str, float]]],
                 members: List[int],
                 max_words: int = 4) -> str:
    """
    グループ内トピックの上位語（重み和）から代表ラベルを作る。
    """
    counter = Counter()
    for t in members:
        for w, s in words_by_tid.get(t, [])[:10]:
            if isinstance(w, str) and w.strip():
                counter[w] += float(s)
    top = [w for w, _ in counter.most_common(max_words)]
    # 日本語・英語混在でも可読なように中黒区切り
    return "・".join(top)

# ------- トピック時系列（統合後）を計算 -------
def compute_group_timeseries(topics_over_time: pd.DataFrame,
                             groups: List[List[int]]) -> pd.DataFrame:
    """
    BERTopicのtopics_over_time（列: ['Topic','Timestamp','Frequency']）を
    グループ（複数topic_idの統合）に合算した時系列(%に換算)へ。
    """
    df = topics_over_time.copy()
    totals = df.groupby("Timestamp", as_index=True)["Frequency"].sum().rename("total")
    # group_id を 0.. に再付与
    gmap = {}
    for gid, members in enumerate(groups):
        for t in members:
            gmap[t] = gid

    df["Group"] = df["Topic"].map(gmap).dropna()
    df_g = df.groupby(["Group", "Timestamp"], as_index=False)["Frequency"].sum()

    # 割合(%)にする
    df_g = df_g.merge(totals, left_on="Timestamp", right_index=True, how="left")
    df_g["Percentage"] = 100.0 * df_g["Frequency"] / df_g["total"].clip(lower=1)
    df_g = df_g.drop(columns=["total"])
    return df_g

# ------- 可視化（上位10グループのみ） -------
def plot_top_groups(df_g: pd.DataFrame,
                    labels: Dict[int, str],
                    out_png: str,
                    title: str,
                    top_k: int = 10):
    # 各グループの総出現で上位Kを選ぶ
    order = (df_g.groupby("Group")["Frequency"].sum()
                 .sort_values(ascending=False))
    top_groups = order.index.tolist()[:top_k]

    plt.figure(figsize=(12, 6))
    for gid in top_groups:
        d = df_g[df_g["Group"] == gid].sort_values("Timestamp")
        if d.empty:
            continue
        label = labels.get(gid, f"G{gid}")
        # 凡例が長過ぎないようにトリム
        if len(label) > 40:
            label = label[:37] + "..."
        plt.plot(d["Timestamp"], d["Percentage"], marker=".", linewidth=1.2, label=label)

    plt.title(title)
    plt.xlabel("Time")
    plt.ylabel("Percentage of comments")
    plt.legend(ncol=2, fontsize=9, frameon=False)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(out_png, dpi=220)
    plt.close()
    print(f"✅ 時系列図: {out_png}")

# =====================
# メイン
# =====================
def main():
    csv_files = glob.glob(os.path.join(CHAT_DIR, "*.csv"))
    if not csv_files:
        print("CSVが見つかりません:", CHAT_DIR)

    all_country_rows = []
    topic_words_rows = []
    metrics_rows = []

    for csv_file in csv_files:
        try:
            df = read_csv_any(csv_file)
            if df.empty or "message" not in df.columns:
                print(f"⚠️ スキップ: {csv_file}")
                continue

            country = parse_country_from_filename(csv_file)

            # 前処理
            df = df.dropna(subset=["message"]).copy()
            df["message_clean"] = df["message"].astype(str).apply(preprocess_text)
            df = df[df["message_clean"].str.len() > 0].copy()
            if df.empty:
                print(f"⚠️ 空データ: {csv_file}")
                continue

            df["lang"] = df["message_clean"].apply(detect_lang_safe)

            # タイムスタンプ
            if "timestamp" in df.columns and not df["timestamp"].isnull().all():
                df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
                df = df.dropna(subset=["timestamp"]).copy()
            else:
                # 疑似タイムスタンプ（均等間隔）
                df["timestamp"] = pd.date_range("2024-01-01", periods=len(df), freq="5S")

            texts = df["message_clean"].tolist()
            if len(texts) < 50:
                print(f"⚠️ データ不足: {csv_file}")
                continue

            # ===== 埋め込み =====
            emb = embedding_model_global.encode(
                texts, batch_size=64, show_progress_bar=False, normalize_embeddings=True
            )

            # ===== BERTopic =====
            topic_model = BERTopic(
                embedding_model=embedding_model_global,        # ← None だと表現抽出でエラーになる場合がある
                vectorizer_model=vectorizer_model,
                umap_model=umap_model,
                hdbscan_model=hdbscan_model,
                calculate_probabilities=False,
                representation_model=representation_model,
                seed_topic_list=seed_topic_list if USE_SEED else None,
                min_topic_size=20,
                nr_topics=None,
                verbose=False,
            )

            topics, _ = topic_model.fit_transform(texts, embeddings=emb)

            # 無効トピック除去
            valid_idx = [i for i, t in enumerate(topics) if t != -1]
            if len(valid_idx) < 30:
                print(f"⚠️ 有効トピックデータ不足: {csv_file}")
                continue

            df_valid = df.iloc[valid_idx].copy()
            topics_valid = [topics[i] for i in valid_idx]

            # 上位語を取得（重み付き）
            words_by_tid: Dict[int, List[Tuple[str, float]]] = {}
            topic_info = topic_model.get_topic_info()
            valid_tids = sorted([t for t in topic_info["Topic"].tolist() if t != -1])
            for tid in valid_tids:
                items = topic_model.get_topic(tid) or []  # [(word, score), ...]
                # 安全にフィルタ（文字列のみ）
                items = [(str(w), float(s)) for w, s in items if isinstance(w, str) and str(w).strip()]
                words_by_tid[tid] = items

            # ===== 時系列: 元のトピック単位 =====
            nr_bins = max(12, min(50, len(df_valid) // 100))
            try:
                tot = topic_model.topics_over_time(
                    docs=df_valid["message_clean"].tolist(),
                    topics=topics_valid,
                    timestamps=df_valid["timestamp"].tolist(),
                    nr_bins=nr_bins,
                    datetime_format=None,
                )
            except Exception:
                tot = topic_model.topics_over_time(
                    docs=df_valid["message_clean"].tolist(),
                    topics=topics_valid,
                    timestamps=df_valid["timestamp"].tolist(),
                    nr_bins=20,
                    datetime_format=None,
                )

            # ===== 似通ったトピックを自動統合 =====
            groups = build_topic_groups(words_by_tid, jaccard_threshold=0.6)
            # グループ代表ラベル
            gid_label: Dict[int, str] = {}
            for gid, members in enumerate(groups):
                gid_label[gid] = merged_label(words_by_tid, members, max_words=4)

            # グループ時系列（%）
            df_g = compute_group_timeseries(tot, groups)

            # ===== 描画：上位10グループのみ =====
            title = f"Topics Over Time (Top-10, merged) : {os.path.basename(csv_file)} [{country}]"
            out_img = os.path.join(
                OUTPUT_DIR, os.path.basename(csv_file).replace(".csv", "_timeline.png")
            )
            plot_top_groups(df_g, gid_label, out_img, title, top_k=10)

            # ===== 国×トピック分布（全体比率）→ まず元トピックで集計 =====
            topic_counts = pd.Series(topics_valid).value_counts().sort_index()
            topic_share = (topic_counts / topic_counts.sum()).rename("share").to_frame()
            topic_share["country"] = country
            topic_share["topic_id"] = topic_share.index
            all_country_rows.append(topic_share.reset_index(drop=True))

            # ===== 出力: 各トピック（統合前）のトップ語（可読性向上の参考）=====
            for tid in valid_tids:
                top_terms = [w for w, _ in words_by_tid.get(tid, [])[:10]]
                topic_words_rows.append({
                    "file": os.path.basename(csv_file),
                    "country": country,
                    "topic_id": tid,
                    "top_words": ", ".join(top_terms),
                })

            # ===== 妥当性評価（エラー回避を厚めに） =====
            tokens = [t.split() for t in df_valid["message_clean"].tolist()]
            dictionary = Dictionary(tokens)
            corpus = [dictionary.doc2bow(toks) for toks in tokens]

            top_words_per_topic = []
            for tid in sorted(topic_counts.index):
                # 代表語（文字列）だけを抽出、2語未満は評価対象外
                words = words_by_tid.get(tid, [])
                top_terms = [w for (w, _s) in words[:10] if isinstance(w, str) and w.strip()]
                if len(top_terms) >= 2:
                    top_words_per_topic.append(top_terms)

            if not top_words_per_topic:
                coh_npmi = float("nan")
                coh_umass = float("nan")
            else:
                # Windowsの並列起動問題を避けるため processes=1 固定
                coh_npmi = CoherenceModel(
                    topics=top_words_per_topic,
                    texts=tokens,
                    dictionary=dictionary,
                    coherence="c_npmi",
                    processes=1
                ).get_coherence()
                coh_umass = CoherenceModel(
                    topics=top_words_per_topic,
                    corpus=corpus,
                    dictionary=dictionary,
                    coherence="u_mass",
                    processes=1
                ).get_coherence()

            # Silhouette（クラスタ分離度）
            try:
                sil = (
                    silhouette_score(np.asarray(embedding_model_global.encode(
                        df_valid["message_clean"].tolist(),
                        batch_size=64, show_progress_bar=False, normalize_embeddings=True
                    )), np.array(topics_valid))
                    if len(set(topics_valid)) > 1 else float("nan")
                )
            except Exception:
                sil = float("nan")

            # 概数メトリクス
            n_unique_topics = int(len(set([t for t in topics_valid if t != -1])))
            metrics_rows.append({
                "file": os.path.basename(csv_file),
                "country": country,
                "n_docs": int(len(df)),
                "n_valid": int(len(df_valid)),
                "n_topics": n_unique_topics,
                "coherence_c_npmi": coh_npmi,
                "coherence_umass": coh_umass,
                "silhouette": sil,
            })

        except Exception as e:
            import traceback
            print(f"❌ エラー: {os.path.basename(csv_file)} - {e}")
            traceback.print_exc()

    # ===== 出力まとめ =====
    if all_country_rows:
        country_topic_share_all = pd.concat(all_country_rows, ignore_index=True)
        # 複数ファイルに跨る場合は平均
        country_topic_share = (
            country_topic_share_all.groupby(["country", "topic_id"], as_index=False)["share"].mean()
        )
        country_topic_share.to_csv(
            os.path.join(OUTPUT_DIR, "country_topic_share.csv"),
            index=False, encoding="utf-8-sig"
        )

    if metrics_rows:
        pd.DataFrame(metrics_rows).to_csv(
            os.path.join(OUTPUT_DIR, "metrics.csv"),
            index=False, encoding="utf-8-sig"
        )

    if topic_words_rows:
        pd.DataFrame(topic_words_rows).to_csv(
            os.path.join(OUTPUT_DIR, "topic_words.csv"),
            index=False, encoding="utf-8-sig"
        )

    print("🎯 すべて完了")


if __name__ == "__main__":
    # Windows の並列起動問題対策
    import multiprocessing as mp
    mp.freeze_support()
    main()
