# -*- coding: utf-8 -*-
"""
YouTube/SNSコメントの国別・時系列トピック可視化 + ピーク時ワードクラウド
- 上位10トピック（統合後＝凡例と一致）だけを時系列に描画
- 各トピック（統合後）の「最も盛り上がった時間bin」で、そのトピック文だけのワードクラウドを作成
- --files で処理したい CSV を明示指定可能（カンマ区切り）。未指定なら CHAT_DIR を走査
- 日本語フォント自動設定（文字化け対策）
- トピック重複を上位語Jaccardで統合 → 凡例ラベルは代表語（日本語・英語混在対応）
- Windows の並列起動エラー回避（freeze_support / processes=1）
"""

import os
import re
import glob
import argparse
import warnings
from collections import defaultdict, Counter
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

# ===== Matplotlib（描画&日本語） =====
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager, rcParams

# ---- 日本語フォント設定 ----
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
from bertopic.representation import MaximalMarginalRelevance
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics import silhouette_score
from umap import UMAP
from hdbscan import HDBSCAN

from gensim.corpora import Dictionary
from gensim.models.coherencemodel import CoherenceModel

# ワードクラウド
from wordcloud import WordCloud

warnings.filterwarnings("ignore", category=UserWarning)

# =====================
# 設定（必要なら変更）
# =====================
CHAT_DIR = "data/football"   # 既定の検索フォルダ（--files未指定時に使用）
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 多言語埋め込み
EMB_NAME = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
embedding_model_global = SentenceTransformer(EMB_NAME)

# BERTopic 下回り
vectorizer_model = CountVectorizer(
    token_pattern=r"(?u)\b\w+\b", max_features=4000, min_df=2
)
umap_model = UMAP(
    n_components=5, n_neighbors=15, min_dist=0.00, metric="cosine", random_state=42
)
hdbscan_model = HDBSCAN(
    min_cluster_size=20,
    min_samples=5,
    metric="euclidean",
    cluster_selection_method="eom",
    prediction_data=True,
    core_dist_n_jobs=1,
)
representation_model = MaximalMarginalRelevance(diversity=0.5)

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
    text = (text.replace("😂", " laugh ").replace("😭", " cry ")
                 .replace("👏", " clap ").replace("🔥", " fire "))
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
    encodings = ["utf-8", "utf-8-sig", "cp932", "iso-8859-1"]
    for enc in encodings:
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:
            continue
    return pd.read_csv(path, engine="python")

# ------- トピック重複の自動統合（上位語Jaccard） -------
def jaccard_set(a: set, b: set) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / (len(a | b) + 1e-12)

def build_topic_groups(words_by_tid: Dict[int, List[Tuple[str, float]]],
                       jaccard_threshold: float = 0.6) -> List[List[int]]:
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
    counter = Counter()
    for t in members:
        for w, s in words_by_tid.get(t, [])[:10]:
            if isinstance(w, str) and w.strip():
                counter[w] += float(s)
    top = [w for w, _ in counter.most_common(max_words)]
    return "・".join(top) if top else f"group_{min(members)}"

# ------- 時系列(% に換算) -------
def compute_group_timeseries(topics_over_time: pd.DataFrame,
                             groups: List[List[int]]) -> pd.DataFrame:
    df = topics_over_time.copy()
    totals = df.groupby("Timestamp", as_index=True)["Frequency"].sum().rename("total")
    gmap = {}
    for gid, members in enumerate(groups):
        for t in members:
            gmap[t] = gid
    df["Group"] = df["Topic"].map(gmap)
    df = df.dropna(subset=["Group"]).copy()
    df["Group"] = df["Group"].astype(int)

    df_g = df.groupby(["Group", "Timestamp"], as_index=False)["Frequency"].sum()
    df_g = df_g.merge(totals, left_on="Timestamp", right_index=True, how="left")
    df_g["Percentage"] = 100.0 * df_g["Frequency"] / df_g["total"].clip(lower=1)
    df_g = df_g.drop(columns=["total"])
    return df_g

# ------- 可視化（上位K） -------
def plot_top_groups(df_g: pd.DataFrame,
                    labels: Dict[int, str],
                    out_png: str,
                    title: str,
                    top_k: int = 10):
    order = (df_g.groupby("Group")["Frequency"].sum().sort_values(ascending=False))
    top_groups = order.index.tolist()[:top_k]

    plt.figure(figsize=(12, 6))
    for gid in top_groups:
        d = df_g[df_g["Group"] == gid].sort_values("Timestamp")
        if d.empty:
            continue
        label = labels.get(gid, f"G{gid}")
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

# ------- 時間binを再現（topics_over_time と同じ分割を構築） -------
def build_time_bins(ts: pd.Series, nr_bins: int) -> pd.IntervalIndex:
    tmin, tmax = ts.min(), ts.max()
    # BERTopic は等間隔で nr_bins 個に分けるため、境界は nr_bins+1
    edges = pd.date_range(tmin, tmax, periods=nr_bins + 1)
    return pd.IntervalIndex.from_breaks(edges, closed="left")

# ------- ピークbinでワードクラウドを作成（グループごと） -------
def make_wordclouds_for_peaks(
    df_valid: pd.DataFrame,
    topics_valid: List[int],
    groups: List[List[int]],
    df_g: pd.DataFrame,
    gid_label: Dict[int, str],
    nr_bins: int,
    out_prefix: str,
    wc_top_k: int = 10,
    wc_bin_pad: int = 0,
):
    """
    df_valid: message_clean, timestamp を持つ（-1除去済）
    topics_valid: df_valid 各行の元トピックID
    groups: [[topic_id,...], ...]
    df_g: Group時系列（Frequency, Percentage, Timestamp）
    gid_label: {gid: label}
    nr_bins: 時間bin数（topics_over_timeと同じ）
    out_prefix: 出力ファイルの共通プリフィクス
    wc_top_k: ワードクラウドを作る上位グループ数
    wc_bin_pad: ピークbinの前後に何bin含めるか（0=そのbinのみ）
    """
    # 上位グループを Frequency 合計順で取得
    order = (df_g.groupby("Group")["Frequency"].sum().sort_values(ascending=False))
    top_groups = order.index.tolist()[:wc_top_k]

    # ドキュメント側にも bin を付与
    bins = build_time_bins(df_valid["timestamp"], nr_bins)
    # cut の結果を bin 番号(0..nr_bins-1)に直す
    bin_cats = pd.cut(df_valid["timestamp"], bins)
    bin_indexer = {interval: i for i, interval in enumerate(bins)}
    df_valid = df_valid.copy()
    df_valid["bin_id"] = bin_cats.map(bin_indexer)

    # 各行に topic_id を付与
    df_valid["topic_id"] = topics_valid

    # 日本語フォントパス（見つからなければ None）
    font_path = None
    try:
        if chosen_font:
            # Matplotlib に登録されているフォントからパスを推測
            for f in font_manager.fontManager.ttflist:
                if f.name == chosen_font:
                    font_path = f.fname
                    break
        if (not font_path):
            local_font = os.path.join(os.path.dirname(__file__), "fonts", "NotoSansCJKjp-Regular.otf")
            font_path = local_font if os.path.exists(local_font) else None
    except Exception:
        font_path = None

    # 軽いストップワード（お好みで調整）
    stop = set([
        "the","a","an","to","of","and","or","in","on","for","is","are",
        "this","that","it","i","you","we","he","she","they",
        "www","http","https","com",
        # 日本語のよく出る助詞/感嘆も最低限
        "てる","いる","する","ある","ない","こと","もの","です","ます","すごい","やばい","ｗ","w"
    ])

    for gid in top_groups:
        # 1) ピークbinを特定
        d = df_g[df_g["Group"] == gid]
        if d.empty:
            continue
        # Frequency が最大の Timestamp（＝bin中心）を取得
        peak_row = d.iloc[d["Frequency"].values.argmax()]
        peak_ts = peak_row["Timestamp"]

        # Timestamp を bins に当てて bin_id を取得
        peak_bin = None
        for i, interval in enumerate(bins):
            if (peak_ts >= interval.left) and (peak_ts < interval.right):
                peak_bin = i
                break
        if peak_bin is None:
            # 念のため最も近い bin を採用
            centers = np.array([iv.left.value for iv in bins], dtype=np.int64)
            peak_bin = int(np.argmin(np.abs(centers - np.int64(peak_ts.value))))

        # 2) ピークbin（±wc_bin_pad）に入っていて、かつグループ構成トピックに属する文だけ抽出
        members = set(groups[gid])
        valid_bins = set(range(max(0, peak_bin - wc_bin_pad), min(nr_bins - 1, peak_bin + wc_bin_pad) + 1))
        mask = df_valid["bin_id"].isin(valid_bins) & df_valid["topic_id"].isin(members)
        texts_peak = df_valid.loc[mask, "message_clean"].tolist()
        if len(texts_peak) == 0:
            print(f"⚠️ ワードクラウド対象なし: group {gid}")
            continue

        # 3) ワードクラウド生成
        txt = " ".join(texts_peak)
        wc = WordCloud(
            width=1200, height=800, background_color="white",
            font_path=font_path,  # 日本語フォント
            collocations=False,   # 「連語の重複」オフ（単語バラし重視）
            stopwords=stop
        ).generate(txt)

        label = gid_label.get(gid, f"G{gid}")
        if len(label) > 60:  # タイトル長すぎ対策
            label = label[:57] + "..."

        plt.figure(figsize=(10, 6))
        plt.imshow(wc, interpolation="bilinear")
        plt.axis("off")
        plt.title(f"WordCloud at Peak (Group {gid}): {label}")
        out_png = f"{out_prefix}_wordcloud_G{gid}_bin{peak_bin}.png"
        plt.tight_layout(pad=0.3)
        plt.savefig(out_png, dpi=220)
        plt.close()
        print(f"🟦 ワードクラウド: {out_png}")

# =====================
# メイン
# =====================
def process_one_csv(csv_file: str,
                    wc_top_k: int,
                    wc_bin_pad: int):
    try:
        df = read_csv_any(csv_file)
        if df.empty or "message" not in df.columns:
            print(f"⚠️ スキップ: {csv_file}")
            return None

        country = parse_country_from_filename(csv_file)

        # 前処理
        df = df.dropna(subset=["message"]).copy()
        df["message_clean"] = df["message"].astype(str).apply(preprocess_text)
        df = df[df["message_clean"].str.len() > 0].copy()
        if df.empty:
            print(f"⚠️ 空データ: {csv_file}")
            return None

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
            return None

        # ===== 埋め込み =====
        emb = embedding_model_global.encode(
            texts, batch_size=64, show_progress_bar=False, normalize_embeddings=True
        )

        # ===== BERTopic =====
        topic_model = BERTopic(
            embedding_model=embedding_model_global,
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
            return None

        df_valid = df.iloc[valid_idx].copy()
        topics_valid = [topics[i] for i in valid_idx]

        # 上位語
        words_by_tid: Dict[int, List[Tuple[str, float]]] = {}
        topic_info = topic_model.get_topic_info()
        valid_tids = sorted([t for t in topic_info["Topic"].tolist() if t != -1])
        for tid in valid_tids:
            items = topic_model.get_topic(tid) or []
            items = [(str(w), float(s)) for w, s in items if isinstance(w, str) and str(w).strip()]
            words_by_tid[tid] = items

        # 時系列（元トピック）
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
            nr_bins = 20

        # トピック統合
        groups = build_topic_groups(words_by_tid, jaccard_threshold=0.6)
        gid_label: Dict[int, str] = {}
        for gid, members in enumerate(groups):
            gid_label[gid] = merged_label(words_by_tid, members, max_words=4)

        # グループ時系列（%）
        df_g = compute_group_timeseries(tot, groups)

        # 描画（上位10）
        title = f"Topics Over Time (Top-10, merged) : {os.path.basename(csv_file)} [{country}]"
        out_img = os.path.join(
            OUTPUT_DIR, os.path.basename(csv_file).replace(".csv", "_timeline.png")
        )
        plot_top_groups(df_g, gid_label, out_img, title, top_k=10)

        # ======= ピーク時ワードクラウド =======
        out_prefix = os.path.join(
            OUTPUT_DIR, os.path.splitext(os.path.basename(csv_file))[0]
        )
        make_wordclouds_for_peaks(
            df_valid=df_valid,
            topics_valid=topics_valid,
            groups=groups,
            df_g=df_g,
            gid_label=gid_label,
            nr_bins=nr_bins,
            out_prefix=out_prefix,
            wc_top_k=10 if wc_top_k is None else int(wc_top_k),
            wc_bin_pad=int(wc_bin_pad),
        )

        # ======= 参考指標を最低限保存（従来通り） =======
        topic_counts = pd.Series(topics_valid).value_counts().sort_index()
        topic_share = (topic_counts / topic_counts.sum()).rename("share").to_frame()
        topic_share["country"] = country
        topic_share["topic_id"] = topic_share.index
        topic_share.reset_index(drop=True).to_csv(
            os.path.join(OUTPUT_DIR, os.path.basename(csv_file).replace(".csv", "_topic_share.csv")),
            index=False, encoding="utf-8-sig"
        )

        # トップ語一覧
        rows = []
        for tid in valid_tids:
            top_terms = [w for w, _ in words_by_tid.get(tid, [])[:10]]
            rows.append({
                "file": os.path.basename(csv_file),
                "country": country,
                "topic_id": tid,
                "top_words": ", ".join(top_terms),
            })
        if rows:
            pd.DataFrame(rows).to_csv(
                os.path.join(OUTPUT_DIR, os.path.basename(csv_file).replace(".csv", "_topic_words.csv")),
                index=False, encoding="utf-8-sig"
            )

        # 妥当性（coherence 等）
        tokens = [t.split() for t in df_valid["message_clean"].tolist()]
        dictionary = Dictionary(tokens)
        corpus = [dictionary.doc2bow(toks) for toks in tokens]
        top_words_per_topic = []
        for tid in sorted(topic_counts.index):
            words = words_by_tid.get(tid, [])
            top_terms = [w for (w, _s) in words[:10] if isinstance(w, str) and w.strip()]
            if len(top_terms) >= 2:
                top_words_per_topic.append(top_terms)
        if top_words_per_topic:
            coh_npmi = CoherenceModel(
                topics=top_words_per_topic, texts=tokens, dictionary=dictionary,
                coherence="c_npmi", processes=1
            ).get_coherence()
            coh_umass = CoherenceModel(
                topics=top_words_per_topic, corpus=corpus, dictionary=dictionary,
                coherence="u_mass", processes=1
            ).get_coherence()
        else:
            coh_npmi = float("nan")
            coh_umass = float("nan")
        try:
            sil = (
                silhouette_score(
                    np.asarray(embedding_model_global.encode(
                        df_valid["message_clean"].tolist(),
                        batch_size=64, show_progress_bar=False, normalize_embeddings=True
                    )),
                    np.array(topics_valid)
                ) if len(set(topics_valid)) > 1 else float("nan")
            )
        except Exception:
            sil = float("nan")

        metrics_row = {
            "file": os.path.basename(csv_file),
            "country": country,
            "n_docs": int(len(df)),
            "n_valid": int(len(df_valid)),
            "n_topics": int(len(set([t for t in topics_valid if t != -1]))),
            "coherence_c_npmi": coh_npmi,
            "coherence_umass": coh_umass,
            "silhouette": sil,
        }
        pd.DataFrame([metrics_row]).to_csv(
            os.path.join(OUTPUT_DIR, os.path.basename(csv_file).replace(".csv", "_metrics.csv")),
            index=False, encoding="utf-8-sig"
        )

        print("🎯 完了:", os.path.basename(csv_file))
        return True

    except Exception as e:
        import traceback
        print(f"❌ エラー: {os.path.basename(csv_file)} - {e}")
        traceback.print_exc()
        return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--files", type=str, default=None,
                        help="処理したいCSVのパスをカンマ区切りで指定。未指定なら CHAT_DIR を走査")
    parser.add_argument("--wc-top-k", type=int, default=10,
                        help="ワードクラウドを作成する上位グループ数（既定=10）")
    parser.add_argument("--wc-bin-pad", type=int, default=0,
                        help="ピークbinの前後に何binを含めるか（既定=0）")
    args = parser.parse_args()

    if args.files:
        raw_list = [p.strip() for p in args.files.split(",") if p.strip()]
        csv_files = []
        for p in raw_list:
            if os.path.isabs(p) or os.path.exists(p):
                csv_files.append(p)
            else:
                cand = os.path.join(CHAT_DIR, p)
                csv_files.append(cand)
    else:
        csv_files = glob.glob(os.path.join(CHAT_DIR, "*.csv"))

    if not csv_files:
        print("CSVが見つかりません:", CHAT_DIR)
        return

    for csv in csv_files:
        process_one_csv(csv, wc_top_k=args.wc_top_k, wc_bin_pad=args.wc_bin_pad)

if __name__ == "__main__":
    import multiprocessing as mp
    mp.freeze_support()
    main()
