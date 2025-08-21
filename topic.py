import os
import re
import glob
import math
import random
import itertools
import warnings
from datetime import timedelta

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # GUI不要の環境でも保存できるように
import matplotlib.pyplot as plt

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

from scipy.spatial.distance import jensenshannon
from fastdtw import fastdtw

warnings.filterwarnings("ignore", category=UserWarning)

# =====================
# 設定
# =====================
CHAT_DIR = "data/chat"          # チャットCSVの保存ディレクトリ
OUTPUT_DIR = "output"           # 結果出力先
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 多言語埋め込み（翻訳せずに直接ベクトル化）
EMB_NAME = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
embedding_model = SentenceTransformer(EMB_NAME)

# BERTopicの下回り（安定寄せ）
vectorizer_model = CountVectorizer(
    token_pattern=r"(?u)\b\w+\b", max_features=4000, min_df=2
)
umap_model = UMAP(
    n_components=5, n_neighbors=15, min_dist=0.00, metric="cosine", random_state=42
)
# Windows の並列 spawn 回避のため core_dist_n_jobs=1 を強制
hdbscan_model = HDBSCAN(
    min_cluster_size=20,
    min_samples=5,
    metric="euclidean",
    cluster_selection_method="eom",
    prediction_data=True,
    core_dist_n_jobs=1,
)
representation_model = MaximalMarginalRelevance(diversity=0.5)

# 任意のシードトピック（例: 野球寄り）
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
USE_SEED = True

# =====================
# ユーティリティ
# =====================

def preprocess_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = re.sub(r"http\S+|www\.\S+", " ", text)
    text = re.sub(r"@\w+", " ", text)
    text = re.sub(r"#\w+", " ", text)
    # 絵文字の超簡易置換（必要なら emoji ライブラリで拡張）
    text = (
        text.replace("😂", " laugh ")
        .replace("😭", " cry ")
        .replace("👏", " clap ")
        .replace("🔥", " fire ")
    )
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
    m = re.findall(
        r"(japan|japanese|jpn|india|indian|dominican|usa|korea|korean|mexico|taiwan|china|chinese|france)",
        name.lower(),
    )
    if m:
        return m[-1].capitalize()
    if re.search(r"[\u3040-\u30ff\u4e00-\u9faf]", name):
        return "Japan"
    return "Unknown"


def js_distance(p, q):
    p = np.asarray(p, dtype=float)
    q = np.asarray(q, dtype=float)
    p = p / (p.sum() + 1e-12)
    q = q / (q.sum() + 1e-12)
    return jensenshannon(p, q)  # 0〜1


def dtw_distance(ts1, ts2):
    distance, _ = fastdtw(ts1, ts2, dist=lambda a, b: abs(a - b))
    return distance


def permutation_test_proportion(count_a, n_a, count_b, n_b, n_perm=2000, seed=42):
    rng = np.random.default_rng(seed)
    pooled = np.concatenate(
        [
            np.ones(count_a),
            np.zeros(max(n_a - count_a, 0)),
            np.ones(count_b),
            np.zeros(max(n_b - count_b, 0)),
        ]
    )
    obs = abs(count_a / max(n_a, 1) - count_b / max(n_b, 1))
    more = 0
    for _ in range(n_perm):
        rng.shuffle(pooled)
        sa = pooled[:n_a].mean() if n_a > 0 else 0.0
        sb = pooled[n_a : n_a + n_b].mean() if n_b > 0 else 0.0
        if abs(sa - sb) >= obs:
            more += 1
    return (more + 1) / (n_perm + 1)


def read_csv_any(path: str) -> pd.DataFrame:
    """エンコーディングを順に試して読む"""
    encodings = ["utf-8", "utf-8-sig", "cp932", "iso-8859-1"]
    for enc in encodings:
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:
            continue
    # だめなら pandas に任せる
    return pd.read_csv(path, engine="python")


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
    perm_rows = []

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

            # 埋め込み
            emb = embedding_model.encode(
                texts,
                batch_size=64,
                show_progress_bar=False,
                normalize_embeddings=True,
            )

            # BERTopic（シード使用）
            topic_model = BERTopic(
                embedding_model=None,  # 事前計算したembを渡す
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

            # === 追加: 上位10トピックを決め、凡例名を用意 ===
            topic_counts_all = pd.Series(topics_valid).value_counts().sort_values(ascending=False)
            top10_ids = topic_counts_all.head(5).index.tolist()

            def make_label(tid: int, max_words: int = 3) -> str:
                words = topic_model.get_topic(int(tid)) or []
                top_terms = [w for w, _ in words[:max_words] if isinstance(w, str) and w.strip()]
                return (f"T{tid}: " + ", ".join(top_terms)) if top_terms else f"T{tid}"

            legend_labels = {tid: make_label(tid) for tid in top10_ids}
            # === 追加ここまで ===

            # 時系列割合（%）
            # bin 数をデータ量に応じて自動調整
            nr_bins = max(12, min(50, len(df_valid) // 100))
            try:
                topics_over_time = topic_model.topics_over_time(
                    docs=df_valid["message_clean"].tolist(),
                    topics=topics_valid,
                    timestamps=df_valid["timestamp"].tolist(),
                    nr_bins=nr_bins,
                    datetime_format=None,
                )
            except Exception:
                # フォールバック（bin数を減らす）
                topics_over_time = topic_model.topics_over_time(
                    docs=df_valid["message_clean"].tolist(),
                    topics=topics_valid,
                    timestamps=df_valid["timestamp"].tolist(),
                    nr_bins=20,
                    datetime_format=None,
                )

            totals = topics_over_time.groupby("Timestamp", as_index=True)["Frequency"].sum()
            topics_over_time["Percentage"] = topics_over_time.apply(
                lambda r: 100.0 * r["Frequency"] / max(totals.get(r["Timestamp"], 1), 1), axis=1
            )

            # 図の保存（上位10トピックのみ）
            plt.figure(figsize=(12, 6))
            plot_data = topics_over_time[topics_over_time["Topic"].isin(top10_ids)]
            for t in top10_ids:
                d = plot_data[plot_data["Topic"] == t]
                if d.empty:
                    continue
                plt.plot(
                    d["Timestamp"],
                    d["Percentage"],
                    marker=".",
                    linewidth=1,
                    label=legend_labels.get(t, f"T{t}")
                )
            plt.title(f"Topics Over Time (Top 10 %): {os.path.basename(csv_file)} [{country}]")
            plt.xlabel("Time")
            plt.ylabel("Percentage of comments")
            plt.legend(ncol=2, fontsize=8)
            plt.xticks(rotation=45)
            plt.tight_layout()
            out_img = os.path.join(
                OUTPUT_DIR, os.path.basename(csv_file).replace(".csv", "_timeline.png")
            )
            plt.savefig(out_img, dpi=200)
            plt.close()
            print("✅ 時系列図:", out_img)

            # 国×トピック分布（全体比率）
            topic_counts = pd.Series(topics_valid).value_counts().sort_index()
            topic_share = (topic_counts / topic_counts.sum()).rename("share").to_frame()
            topic_share["country"] = country
            topic_share["topic_id"] = topic_share.index
            all_country_rows.append(topic_share.reset_index(drop=True))

            # トピック語（トップ語とMMR表現）
            topic_info = topic_model.get_topic_info()
            for tid in topic_info["Topic"].tolist():
                if tid == -1:
                    continue
                words = topic_model.get_topic(tid) or []
                top_terms = [w for w, _ in words[:10]]
                topic_words_rows.append(
                    {
                        "file": os.path.basename(csv_file),
                        "country": country,
                        "topic_id": tid,
                        "top_words": ", ".join(top_terms),
                    }
                )

            # ===== 妥当性評価 =====
            tokens = [t.split() for t in df_valid["message_clean"].tolist()]
            dictionary = Dictionary(tokens)
            corpus = [dictionary.doc2bow(toks) for toks in tokens]

            # BERTopic → Gensim 形式に整形（空や不正は除外）
            top_words_per_topic = []
            for tid in sorted(topic_counts.index):
                words = topic_model.get_topic(tid) or []
                top_terms = [w for (w, _s) in words[:10] if isinstance(w, str) and w.strip()]
                if len(top_terms) >= 2:
                    top_words_per_topic.append(top_terms)

            if not top_words_per_topic:
                coh_npmi = float("nan")
                coh_umass = float("nan")
            else:
                # Windowsの並列起動問題を避けるため processes=1 で固定
                coh_npmi = CoherenceModel(
                    topics=top_words_per_topic, texts=tokens, dictionary=dictionary, coherence="c_npmi", processes=1
                ).get_coherence()
                coh_umass = CoherenceModel(
                    topics=top_words_per_topic, corpus=corpus, dictionary=dictionary, coherence="u_mass", processes=1
                ).get_coherence()

            # Silhouette
            try:
                sil = (
                    silhouette_score(np.asarray(emb)[valid_idx], np.array(topics_valid))
                    if len(set(topics_valid)) > 1
                    else float("nan")
                )
            except Exception:
                sil = float("nan")

            # 安定性（軽量ブートストラップ）
            def jaccard(a, b):
                return len(a & b) / (len(a | b) + 1e-12)

            rng = np.random.default_rng(42)
            boot_scores = []
            for _ in range(3):  # 回数は軽め
                sample_idx = rng.choice(len(df_valid), size=len(df_valid), replace=True)
                docs_s = [df_valid["message_clean"].iloc[i] for i in sample_idx]
                emb_s = embedding_model.encode(
                    docs_s, batch_size=64, show_progress_bar=False, normalize_embeddings=True
                )
                tm_s = BERTopic(
                    embedding_model=None,
                    vectorizer_model=vectorizer_model,
                    umap_model=umap_model,
                    hdbscan_model=hdbscan_model,
                    representation_model=representation_model,
                    seed_topic_list=seed_topic_list if USE_SEED else None,
                    calculate_probabilities=False,
                    verbose=False,
                    min_topic_size=20,
                )
                t_s, _ = tm_s.fit_transform(docs_s, embeddings=emb_s)
                # 上位語のJaccard平均（IDは一致しない可能性もあるので共通のIDに限定）
                common_ids = [
                    tid for tid in set(topics_valid) if tid != -1 and tid in tm_s.get_topic_info()["Topic"].values
                ]
                jac = []
                for tid in common_ids:
                    w1 = set([w for w, _ in (topic_model.get_topic(tid) or [])[:10]])
                    w2 = set([w for w, _ in (tm_s.get_topic(tid) or [])[:10]])
                    if w1 and w2:
                        jac.append(jaccard(w1, w2))
                if jac:
                    boot_scores.append(float(np.mean(jac)))
            stability = float(np.mean(boot_scores)) if boot_scores else float("nan")

            n_unique_topics = int(len(set([t for t in topics_valid if t != -1])))

            metrics_rows.append(
                {
                    "file": os.path.basename(csv_file),
                    "country": country,
                    "n_docs": int(len(df)),
                    "n_valid": int(len(df_valid)),
                    "n_topics": n_unique_topics,
                    "coherence_c_npmi": coh_npmi,
                    "coherence_umass": coh_umass,
                    "silhouette": sil,
                    "stability_jaccard": stability,
                }
            )

        except Exception as e:
            import traceback

            print(f"❌ エラー: {os.path.basename(csv_file)} - {e}")
            traceback.print_exc()

    # ===== 国間比較（分布距離・置換検定） =====
    if all_country_rows:
        # 1) 重複（同一 country×topic_id が複数ファイル）を平均集約
        country_topic_share_all = pd.concat(all_country_rows, ignore_index=True)
        country_topic_share = (
            country_topic_share_all.groupby(["country", "topic_id"], as_index=False)["share"].mean()
        )
        country_topic_share.to_csv(
            os.path.join(OUTPUT_DIR, "country_topic_share.csv"), index=False, encoding="utf-8-sig"
        )

        # 2) ピボットで行列化
        mat = country_topic_share.pivot_table(
            index="country", columns="topic_id", values="share", fill_value=0
        ).sort_index(axis=0).sort_index(axis=1)
        countries = mat.index.tolist()
        topic_ids = mat.columns.tolist()

        # 3) JS距離ヒートマップ
        dist_mat = np.zeros((len(countries), len(countries)))
        for i, ca in enumerate(countries):
            pa = mat.loc[ca].values
            for j, cb in enumerate(countries):
                pb = mat.loc[cb].values
                dist_mat[i, j] = js_distance(pa, pb)

        pd.DataFrame(dist_mat, index=countries, columns=countries).to_csv(
            os.path.join(OUTPUT_DIR, "country_distance_js.csv"), encoding="utf-8-sig"
        )

        plt.figure(figsize=(6, 5))
        plt.imshow(dist_mat, interpolation="nearest")
        plt.xticks(range(len(countries)), countries, rotation=45)
        plt.yticks(range(len(countries)), countries)
        plt.title("Jensen–Shannon Distance between Countries (Topic distributions)")
        plt.colorbar()
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, "country_distance_js.png"), dpi=200)
        plt.close()

        # 4) 置換検定（割合差の有意性）
        metrics_df = pd.DataFrame(metrics_rows)
        for (ca, cb) in itertools.combinations(countries, 2):
            na = int(metrics_df.query("country == @ca")["n_valid"].sum() or 1)
            nb = int(metrics_df.query("country == @cb")["n_valid"].sum() or 1)
            for tid in topic_ids:
                count_a = int(round(mat.loc[ca, tid] * na))
                count_b = int(round(mat.loc[cb, tid] * nb))
                pval = permutation_test_proportion(count_a, na, count_b, nb, n_perm=2000)
                perm_rows.append({
                    "country_a": ca,
                    "country_b": cb,
                    "topic_id": int(tid),
                    "p_value": float(pval),
                })

        if perm_rows:
            pd.DataFrame(perm_rows).to_csv(
                os.path.join(OUTPUT_DIR, "permutation_tests.csv"), index=False, encoding="utf-8-sig"
            )

    # ===== 指標類の保存 =====
    if metrics_rows:
        pd.DataFrame(metrics_rows).to_csv(
            os.path.join(OUTPUT_DIR, "metrics.csv"), index=False, encoding="utf-8-sig"
        )
    if topic_words_rows:
        pd.DataFrame(topic_words_rows).to_csv(
            os.path.join(OUTPUT_DIR, "topic_words.csv"), index=False, encoding="utf-8-sig"
        )

    print("🎯 すべて完了")


if __name__ == "__main__":
    # Windows の並列起動問題対策
    import multiprocessing as mp

    mp.freeze_support()
    main()
