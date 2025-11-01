#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
event_comparison.py  (全面改良版)

目的:
- 同一試合を扱う複数の配信者CSVで、トピックを抽出→似トピック統合→時系列(%)
- グループ化トピックの時系列からピークイベント（複数）を抽出
- ストリーム間で「語彙類似(Jaccard) × 時間ずれ」条件で共通イベントとして照合
- 各共通イベントの配信者間コメント内容差を Jensen–Shannon距離で定量化
- すべてのCSV出力に対応する可視化PNGを自動生成（ヒートマップ、距離行列、ワードクラウド、時系列）

使い方例 (PowerShell):
  # フォルダ指定（推奨）
  python event_comparison.py `
    --folder "data/football" `
    --pattern "*.csv" `
    --time-bins 300 `
    --peak-pad 1 `
    --n-events 5 `
    --topk 200 `
    --time-match-th 60 `
    --jaccard-th 0.5 `
    --word-match-th 0.4 `
    --save-json

  # 直接ファイル指定（スペースや日本語パスはPowerShell変数経由が安全）
  $files = Get-ChildItem -Path "data/football" -Filter *.csv | ForEach-Object { $_.FullName }
  python event_comparison.py --files $files --time-bins 300 --n-events 5 --save-json

出力:
- output/event_comparison_results.csv        … 各共通イベントの距離統計
- output/event_comparison_results.png        … 上の距離行列の可視化
- output/event_eventmap.csv                  … 共通イベント×配信者の「有無」ヒートマップ (矩形表)
- output/event_eventmap.png                  … ↑の可視化
- output/event_comments.json                 … （--save-json時）各イベント×配信者の抽出コメント
- output/wordclouds/event_<EID>/WC_<basename>.png   … イベントごとのワードクラウド
- output/timelines/<basename>_timeline.png         … 各配信者のTop-10(統合)時系列
"""

import argparse
import os, re, json
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Optional

# ===== 追加ライブラリ =====
# 言語検出ライブラリ langdetect がインストールされていない環境に対応するため、
# try-import を用いてフォールバックを用意する。
try:
    from langdetect import detect, DetectorFactory  # type: ignore
    DetectorFactory.seed = 42
    _LANGDETECT_AVAILABLE = True
except ImportError:
    _LANGDETECT_AVAILABLE = False
    # ダミー関数を定義
    def detect(text: str) -> str:
        return "unk"
    class DetectorFactory:
        seed = None


import numpy as np
import pandas as pd

# ===== Matplotlib（描画&日本語フォント） =====
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager, rcParams
import unicodedata  # for converting emoji characters to names in charts

# 日本語と絵文字フォントの候補を設定
JP_FONT_CANDIDATES = [
    "Meiryo", "Yu Gothic", "Yu Gothic UI", "MS Gothic",
    "Hiragino Sans", "Hiragino Kaku Gothic ProN",
    "Noto Sans CJK JP", "IPAGothic",
]
EMOJI_FONT_CANDIDATES = [
    "Noto Color Emoji",   # Linux
    "Segoe UI Emoji",     # Windows
    "Apple Color Emoji",  # macOS
    "Twemoji Mozilla",    # Fallback
]

_available = {f.name for f in font_manager.fontManager.ttflist}
_used_jp_font = None
for _name in JP_FONT_CANDIDATES:
    if _name in _available:
        _used_jp_font = _name
        break

# 優先する絵文字フォントのパスを取得
_emoji_font_path: Optional[str] = None
for _ename in EMOJI_FONT_CANDIDATES:
    try:
        _emoji_font_path = font_manager.findfont(_ename, fallback_to_default=False)
        # `findfont` may return a path even if font is not found; ensure name actually matches
        if _ename in _available:
            break
        # If not, still accept the found path
        break
    except Exception:
        continue
# 追加: カラーフォントが見つからなければ、システムディレクトリから直接NotoColorEmoji.ttfを指定する
if not _emoji_font_path or ("Color" not in os.path.basename(_emoji_font_path)):
    possible_color_paths = [
        "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
        "/usr/share/fonts/truetype/noto/NotoColorEmoji-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoColorEmoji-Regular.otf",
    ]
    for _p in possible_color_paths:
        if os.path.exists(_p):
            _emoji_font_path = _p
            break

# Set Matplotlib global font family as list: first Japanese font if available, then sans-serif
families: List[str] = []
if _used_jp_font:
    families.append(_used_jp_font)
# Do not set emoji font globally because color emojis may not render properly in all contexts; instead use per-plot
families.append("sans-serif")
rcParams["font.family"] = families
rcParams["axes.unicode_minus"] = False
print(f"[Matplotlib] Using fonts: {', '.join(families)} (emoji font path: {_emoji_font_path})")

# ---- Label helpers ----
def _abbr_stream_name(path: str, maxlen: int = 12) -> str:
    """Return a short alias from a CSV path (basename without extension, truncated)."""
    base = os.path.basename(path)
    name = base.replace('.csv', '')
    # common noise cleanup
    for noise in ["_chat_log", "chat_log", "_log", "log"]:
        name = name.replace(noise, "")
    return (name if len(name) <= maxlen else (name[:maxlen-1] + "…"))

# ===== Topic関連 =====
from sentence_transformers import SentenceTransformer
from bertopic import BERTopic
from bertopic.representation import MaximalMarginalRelevance
from sklearn.feature_extraction.text import CountVectorizer
from umap import UMAP
from hdbscan import HDBSCAN

# ===== 出力先 =====
OUT_DIR = "output"
os.makedirs(OUT_DIR, exist_ok=True)

# ===== そのほか =====
# 利用するSentenceTransformerモデル。多言語対応性能の高いモデルへ変更し、
# トピック分類の精度向上を図る
EMB_NAME = "sentence-transformers/xlm-r-100langs-bert-base-nli-stsb-mean-tokens"

# 用語正規化（各言語の類義語を共通語に変換）
# スポーツ実況で頻出する得点やホームランなど、国ごとの表現を英語ベースのキーに統合する。
# ここでは主要な例のみを記載しており、必要に応じて拡張してください。
TERM_MAP: Dict[str, str] = {
    # ホームラン
    "ホームラン": "home_run",
    "本塁打": "home_run",
    "ほーむらん": "home_run",
    "homerun": "home_run",
    "home run": "home_run",
    "homer": "home_run",
    "hr": "home_run",
    "jonron": "home_run",
    # 得点・ゴール
    "得点": "score",
    "得点時": "score",
    "ゴール": "score",
    "goal": "score",
    "score": "score",
    "puntuación": "score",
    "gol": "score",
    # アウト
    "アウト": "out",
    "out": "out",
    # ストライク
    "ストライク": "strike",
    "strike": "strike",
    # ボール
    "ボール": "ball",
    "ball": "ball",
    # フォアボール
    "フォアボール": "walk",
    "walk": "walk",
    # ファウル
    "ファウル": "foul",
    "foul": "foul",
    # 退場
    "退場": "ejection",
    "退場処分": "ejection",
    "レッドカード": "ejection",
    "赤紙": "ejection",
    "ejected": "ejection",
    "expulsado": "ejection",
    "expulsion": "ejection",
    "red card": "ejection",
    "tarjeta roja": "ejection",
    "cartão vermelho": "ejection",
    # 審判
    "審判": "umpire",
    "umpire": "umpire",
    # 怪我
    "怪我": "injury",
    "injury": "injury",
    "hurt": "injury",
    # 応援・歓声
    "応援": "cheer",
    "cheer": "cheer",
    "boo": "boo",
    "拍手": "clap",
    # イエローカード（警告）
    "イエローカード": "warning",
    "yellow card": "warning",
    "警告": "warning",
    "tarjeta amarilla": "warning",
    "cartão amarelo": "warning",
    "amarilla": "warning",
    # 交代・選手交代
    "交代": "substitution",
    "選手交代": "substitution",
    "substitution": "substitution",
    "substituição": "substitution",
    "替え": "substitution",
    # ゴールに関する追加表現
    "ゴール！": "score",
    "ゴールだ": "score",
    "goooooal": "score",
    "goool": "score",
    "ゴール": "score",
    "goal": "score",
    "gol": "score",
    "golaço": "score",
    "gole": "score",
    "goal!": "score",
    "goooool": "score",
    # 得点に関する別表現
    "得点!": "score",
    "scored": "score",
    "goal!": "score",
    "goals": "score",
    # ペナルティ（PK）
    "ペナルティ": "penalty",
    "penal": "penalty",
    "penalty": "penalty",
    "pênalti": "penalty",
    "penalti": "penalty",
    "pk": "penalty",
    # フリーキック
    "フリーキック": "free_kick",
    "free kick": "free_kick",
    "tiro libre": "free_kick",
    "tiro livre": "free_kick",
    "tiro de falta": "free_kick",
    # コーナーキック
    "コーナー": "corner",
    "コーナーキック": "corner",
    "corner": "corner",
    "escanteio": "corner",
    "esquina": "corner",
    # オフサイド
    "オフサイド": "offside",
    "offside": "offside",
    "impedimento": "offside",
    "fuera de juego": "offside",
    # ファウル
    "ファウル": "foul",
    "foul": "foul",
    "falta": "foul",
    # 審判／レフェリー
    "審判": "umpire",
    "レフェリー": "umpire",
    "referee": "umpire",
    "árbitro": "umpire",
    # その他
    # ...
}

def normalize_term(word: str) -> str:
    """用語マッピング辞書を用いて単語を正規化する。小文字化して一致させる。"""
    if not isinstance(word, str):
        return word
    w = word.lower()
    # 辞書内にキーがあればその値を返し、なければ元の小文字を返す
    return TERM_MAP.get(w, w)

# -------------------------
# ユーティリティ / 前処理
# -------------------------
def segment_text(text: str) -> str:
    """
    日本語とその他の文字が混在する文字列にスペースを挿入する。

    日本語には通常スペースが入っていないため、
    コメント全体が1トークンになってしまう問題を避けるための簡易手法です。
    漢字・ひらがな・カタカナが連続する部分と、それ以外（ラテン文字や数字など）
    の境界でスペースを挿入します。
    これは厳密な形態素解析ではありませんが、トークン分割を改善します。
    """
    result = []
    prev_jp: Optional[bool] = None
    for ch in text:
        # 日本語（ひらがな・カタカナ・漢字）とそれ以外の境界を検出
        is_jp = (
            ('\u3040' <= ch <= '\u30ff')  # ひらがな・カタカナ
            or ('\u4e00' <= ch <= '\u9fff')  # 漢字
        )
        if prev_jp is None:
            result.append(ch)
        else:
            if is_jp != prev_jp:
                # 境界でスペースを挿入
                result.append(' ')
            result.append(ch)
        prev_jp = is_jp
    return ''.join(result)
def preprocess_text(text: str) -> str:
    """
    コメントテキストの前処理を行う。

    - URL, メンション, ハッシュタグを除去
    - 絵文字の一部を英単語に置き換え
    - 記号をスペースに置換し、複数スペースを単一に
    - 日本語とその他の文字の間にスペースを挿入（簡易分割）
    - 小文字化
    """
    if not isinstance(text, str):
        return ""
    # URLやメンションなどの除去
    text = re.sub(r"http\S+|www\.\S+", " ", text)
    text = re.sub(r"@\w+", " ", text)
    text = re.sub(r"#\w+", " ", text)
    # 一部絵文字を単語に変換
    text = (
        text.replace("😂", " laugh ")
            .replace("😭", " cry ")
            .replace("👏", " clap ")
            .replace("🔥", " fire ")
    )
    # 記号をスペースに
    text = re.sub(r"[^\w\s\u4E00-\u9FFF\u3040-\u30FF\uAC00-\uD7AF]", " ", text)
    # 日本語とその他の文字列境界にスペースを挿入
    text = segment_text(text)
    # 複数スペースを一つに、前後のスペースを削除し小文字化
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text

# -------------------------
# 言語・絵文字関連ユーティリティ
# -------------------------
def detect_lang_safe(text: str) -> str:
    """langdetect の例外を握りつぶして言語コードを返す"""
    try:
        return detect(text)
    except Exception:
        return "unk"

def is_emoji(char: str) -> bool:
    """簡易的な絵文字判定。Unicode の絵文字ブロックに属するかで判定"""
    cp = ord(char)
    # 絵文字は多様だが、以下の範囲をカバーする
    return (
        0x1F600 <= cp <= 0x1F64F  # emoticons
        or 0x1F300 <= cp <= 0x1F5FF  # symbols & pictographs
        or 0x1F680 <= cp <= 0x1F6FF  # transport & map symbols
        or 0x2600 <= cp <= 0x26FF    # miscellaneous symbols
        or 0x2700 <= cp <= 0x27BF    # dingbats
        or 0x1F1E6 <= cp <= 0x1F1FF  # flags
    )

def compute_language_distribution(texts: List[str]) -> Dict[str, int]:
    """コメントリストから言語別件数を数える"""
    counter = defaultdict(int)
    for txt in texts:
        lang = detect_lang_safe(txt)
        counter[lang] += 1
    return counter

def compute_emoji_ratio(texts: List[str]) -> float:
    """コメント内の絵文字比率を計算（文字数ではなく絵文字数/単語数）"""
    total_tokens = 0
    emoji_count = 0
    for txt in texts:
        tokens = txt.split()
        total_tokens += len(tokens)
        for ch in txt:
            if is_emoji(ch):
                emoji_count += 1
    return float(emoji_count) / max(total_tokens, 1)

def js_distance_distribution(counter_a: Dict[str, int], counter_b: Dict[str, int]) -> float:
    """言語分布やカテゴリ分布の Jensen–Shannon 距離を計算"""
    keys = set(counter_a.keys()) | set(counter_b.keys())
    pa = np.array([counter_a.get(k, 0) for k in keys], dtype=float)
    pb = np.array([counter_b.get(k, 0) for k in keys], dtype=float)
    return js_distance(pa, pb)

# -------------------------
# 感情・スタイル（簡易ヒューリスティック）
# -------------------------
EN_POS = set([
    "good","great","amazing","awesome","nice","love","wow","goal","score","win","gg","goat","clutch",
])
EN_NEG = set([
    "bad","terrible","worst","lose","miss","wtf","hate","boo","noob","trash","rigged",
])
JA_POS = set(["すごい","最高","上手い","うまい","勝ち","勝った","ナイス","神","やった","いいね","草","GG"])
JA_NEG = set(["最悪","ひどい","下手","負け","負けた","ダメ","嫌い","くそ","クソ","ブーイング"])

def _count_emoji(text: str) -> int:
    return sum(1 for ch in text if is_emoji(ch))

def compute_sentiment_metrics(texts: List[str]) -> Dict[str, float]:
    """極性/覚醒度の簡易指標を返す。
    polarity: [-1,1]（ポジ-ネガ）
    pos_ratio/neg_ratio: 語彙比率
    arousal: 感情喚起の代理（! と 絵文字密度）
    """
    pos = neg = 0
    tokens_total = 0
    exclam = 0
    emoji_ct = 0
    for txt in texts:
        if not isinstance(txt, str):
            continue
        t = txt.lower()
        tokens = t.split()
        tokens_total += len(tokens)
        exclam += t.count("!")
        emoji_ct += _count_emoji(txt)
        # 簡易極性
        for w in tokens:
            if w in EN_POS:
                pos += 1
            if w in EN_NEG:
                neg += 1
        # 日本語はスペース区切りでないことが多いので文字列包含で判定
        for w in JA_POS:
            if w in txt:
                pos += 1
        for w in JA_NEG:
            if w in txt:
                neg += 1
    s_total = max(pos + neg, 1)
    polarity = float((pos - neg) / s_total)
    pos_ratio = float(pos / max(tokens_total, 1))
    neg_ratio = float(neg / max(tokens_total, 1))
    arousal = float((exclam + emoji_ct) / max(tokens_total, 1))
    return {
        "polarity": polarity,
        "pos_ratio": pos_ratio,
        "neg_ratio": neg_ratio,
        "arousal": arousal,
    }

def compute_style_profile(texts: List[str]) -> Dict[str, float]:
    letters = 0
    upper = 0
    tokens = 0
    uniq = set()
    exclam = ques = 0
    urls = mentions = 0
    for txt in texts:
        if not isinstance(txt, str):
            continue
        t = txt
        tokens_list = t.split()
        tokens += len(tokens_list)
        for w in tokens_list:
            uniq.add(w)
            if w.startswith("http://") or w.startswith("https://"):
                urls += 1
            if w.startswith("@"):
                mentions += 1
        exclam += t.count("!")
        ques += t.count("?")
        letters += sum(1 for ch in t if ch.isalpha())
        upper += sum(1 for ch in t if ch.isupper())
    avg_len = float(tokens / max(len(texts), 1))
    unique_ratio = float(len(uniq) / max(tokens, 1))
    upper_ratio = float(upper / max(letters, 1))
    exclam_ratio = float(exclam / max(tokens, 1))
    ques_ratio = float(ques / max(tokens, 1))
    url_ratio = float(urls / max(tokens, 1))
    mention_ratio = float(mentions / max(tokens, 1))
    return {
        "avg_len": avg_len,
        "unique_ratio": unique_ratio,
        "upper_ratio": upper_ratio,
        "exclam_ratio": exclam_ratio,
        "ques_ratio": ques_ratio,
        "url_ratio": url_ratio,
        "mention_ratio": mention_ratio,
    }

def style_distance(p: Dict[str, float], q: Dict[str, float]) -> float:
    """スタイルプロファイル間の平均絶対差"""
    keys = sorted(set(p.keys()) & set(q.keys()))
    if not keys:
        return 0.0
    diffs = [abs(float(p[k]) - float(q[k])) for k in keys]
    return float(np.mean(diffs))

def read_csv_any(path: str) -> pd.DataFrame:
    encodings = ["utf-8", "utf-8-sig", "cp932", "iso-8859-1"]
    for enc in encodings:
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:
            pass
    return pd.read_csv(path, engine="python", on_bad_lines="skip")

def parse_country_from_filename(path: str) -> str:
    name = os.path.basename(path)
    m = re.findall(r"(japan|japanese|jpn|india|indian|dominican|usa|korea|korean|mexico|taiwan|china|chinese|france)", name.lower())
    if m:
        return m[-1].capitalize()
    if re.search(r"[\u3040-\u30ff\u4e00-\u9faf]", name):
        return "Japan"
    return "Unknown"

# -------------------------
# トピック統合・時系列・ピーク
# -------------------------
def build_topic_model(embedding_model: SentenceTransformer) -> BERTopic:
    # トピック分類の精度向上のためのハイパーパラメータ調整
    # CountVectorizer の特徴数を増やし、単一出現語も対象に含める
    vectorizer_model = CountVectorizer(token_pattern=r"(?u)\b\w+\b", max_features=6000, min_df=1)
    # UMAP の次元数と近傍数を増やし、高次元埋め込みをより詳細に表現する
    umap_model = UMAP(n_components=10, n_neighbors=30, min_dist=0.00, metric="cosine", random_state=42)
    # HDBSCAN のクラスターサイズとサンプル数を小さく設定し、小さなイベントも検出しやすくする
    hdbscan_model = HDBSCAN(min_cluster_size=10, min_samples=2, metric="euclidean",
                            cluster_selection_method="eom", prediction_data=True, core_dist_n_jobs=1)
    representation_model = MaximalMarginalRelevance(diversity=0.5)
    # スポーツ実況に関連するより多様な種トピックを含める
    seed_topic_list = [
        ["pitch", "strike", "ball", "fastball", "slider", "pitching"],
        ["bat", "homer", "home run", "slugger", "batting"],
        ["defense", "catch", "outfield", "infield", "double play"],
        ["umpire", "referee", "call", "review", "challenge"],
        ["injury", "hurt", "rehab", "out"],
        ["weather", "rain", "delay"],
        ["cheer", "chant", "song", "boo", "applause", "clap", "support"],
        ["strategy", "tactics", "lineup", "substitution", "change"],
        # サッカー・野球等共通: 得点に関する種
        ["goal", "score", "goalkeeper", "penalty", "shoot", "free kick", "corner", "offside"],
        # イエローカード・レッドカード・警告
        ["yellow card", "warning", "foul", "penalty", "fine"],
        ["red card", "ejection", "sent off", "expulsion"],
        # 交代・選手交代
        ["substitution", "sub", "change player", "replace", "交代"],
    ]
    return BERTopic(
        embedding_model=embedding_model,
        vectorizer_model=vectorizer_model,
        umap_model=umap_model,
        hdbscan_model=hdbscan_model,
        representation_model=representation_model,
        calculate_probabilities=False,
        seed_topic_list=seed_topic_list,
        # より小さなトピックサイズを許容することでイベント検出を細分化
        min_topic_size=5,
        nr_topics=None,
        verbose=False,
    )

def merge_topics(words_by_tid: Dict[int, List[Tuple[str, float]]], threshold: float) -> List[List[int]]:
    tids = [t for t in words_by_tid.keys() if t != -1]
    # 各トピックの上位語セットを正規化（用語マッピング）してから比較
    sets = {}
    for t in tids:
        raw_words = [w for w, _ in words_by_tid[t][:10] if isinstance(w, str) and w.strip()]
        normalized = {normalize_term(w) for w in raw_words}
        sets[t] = normalized
    parent: Dict[int, int] = {t: t for t in tids}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def union(x, y):
        rx, ry = find(x), find(y)
        if rx != ry: parent[ry] = rx
    for i, ti in enumerate(tids):
        for tj in tids[i+1:]:
            sa, sb = sets[ti], sets[tj]
            if not sa and not sb: 
                continue
            jac = len(sa & sb) / (len(sa | sb) + 1e-12)
            if jac >= threshold: union(ti, tj)
    groups = defaultdict(list)
    for t in tids: groups[find(t)].append(t)
    return list(groups.values())

def compute_topics_over_time(topic_model: BERTopic, docs: List[str], topics: List[int], timestamps: List[pd.Timestamp], nr_bins: int) -> pd.DataFrame:
    return topic_model.topics_over_time(docs=docs, topics=topics, timestamps=timestamps, nr_bins=nr_bins, datetime_format=None)

def build_relative_time_bins(timestamps: pd.Series, nr_bins: int) -> pd.IntervalIndex:
    tmin, tmax = timestamps.min(), timestamps.max()
    edges = pd.date_range(start=tmin, end=tmax, periods=nr_bins + 1)
    return pd.IntervalIndex.from_breaks(edges, closed="left")

def smooth_series(y: np.ndarray, k: int = 3) -> np.ndarray:
    """移動平均で平滑化（端は反射padding）"""
    if k <= 1 or len(y) == 0:
        return y
    pad = k // 2
    ypad = np.pad(y, (pad, pad), mode="reflect")
    ker = np.ones(k) / k
    return np.convolve(ypad, ker, mode="valid")

def local_peaks(y: np.ndarray, n_keep: int = 3) -> List[int]:
    """単純な局所最大（隣より大きい or 同等）を抽出して上位n_keep"""
    if len(y) == 0:
        return []
    idxs = []
    for i in range(len(y)):
        l = y[i-1] if i-1 >= 0 else -np.inf
        r = y[i+1] if i+1 < len(y) else -np.inf
        if y[i] >= l and y[i] >= r:
            idxs.append(i)
    # 強いピーク順
    idxs.sort(key=lambda i: y[i], reverse=True)
    return idxs[:n_keep]

# -------------------------
# データ構造
# -------------------------
class StreamData:
    def __init__(self, file_path: str, country: str, df_valid: pd.DataFrame,
                 topics_valid: List[int], groups: List[List[int]],
                 gid_label: Dict[int, str], group_timeseries: pd.DataFrame,
                 nr_bins: int, group_top_words: Dict[int, List[str]]):
        self.file_path = file_path
        self.country = country
        self.df_valid = df_valid
        self.topics_valid = topics_valid
        self.groups = groups
        self.gid_label = gid_label
        self.group_timeseries = group_timeseries
        self.nr_bins = nr_bins
        self.group_top_words = group_top_words  # {group_id: [str,...]}
        # 言語列が含まれていれば保持
        self.languages = df_valid.get("lang") if "lang" in df_valid.columns else None

# -------------------------
# ストリーム1本の処理
# -------------------------
def process_stream(csv_file: str, embedding_model: SentenceTransformer,
                   jaccard_th: float, nr_bins: int, topk_plot: int = 10) -> Optional[StreamData]:
    df = read_csv_any(csv_file)
    if df.empty or "message" not in df.columns:
        print(f"Skipping {csv_file}: no message column")
        return None

    # タイムスタンプ 正規化（TZ混在対策：すべてtz-naiveへ）
    if "timestamp" in df.columns and not df["timestamp"].isnull().all():
        ts = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
        df["timestamp"] = ts.dt.tz_localize(None)
        df = df.dropna(subset=["timestamp"]).copy()
    else:
        df["timestamp"] = pd.date_range(start="2024-01-01", periods=len(df), freq="5S")

    # 前処理
    df = df.dropna(subset=["message"]).copy()
    df["message_clean"] = df["message"].astype(str).apply(preprocess_text)
    df = df[df["message_clean"].str.len() > 0].copy()
    if df.empty:
        print(f"Skipping {csv_file}: no usable comments")
        return None
    # 言語検出（後でスタイル比較に利用）
    df["lang"] = df["message_clean"].apply(detect_lang_safe)
    texts = df["message_clean"].tolist()

    # 埋め込み & BERTopic
    emb = embedding_model.encode(texts, batch_size=64, show_progress_bar=False, normalize_embeddings=True)
    topic_model = build_topic_model(embedding_model)
    topics, _ = topic_model.fit_transform(texts, embeddings=emb)

    valid_idx = [i for i, t in enumerate(topics) if t != -1]
    if len(valid_idx) < 10:
        print(f"Skipping {csv_file}: too few valid topics")
        return None
    df_valid = df.iloc[valid_idx].reset_index(drop=True)
    topics_valid = [topics[i] for i in valid_idx]

    # 上位語
    topic_info = topic_model.get_topic_info()
    valid_tids = sorted([int(t) for t in topic_info["Topic"].tolist() if int(t) != -1])
    words_by_tid: Dict[int, List[Tuple[str, float]]] = {}
    for tid in valid_tids:
        items = topic_model.get_topic(tid) or []
        items = [(str(w), float(s)) for w, s in items if isinstance(w, str) and str(w).strip()]
        words_by_tid[tid] = items

    # 似トピック統合
    groups = merge_topics(words_by_tid, threshold=jaccard_th)
    gid_label, group_top_words = {}, {}
    for gid, members in enumerate(groups):
        # トピック統合後の代表語を作成：類義語マッピングで正規化し、上位スコア順にカウント
        counter = Counter()
        for t in members:
            for w, s in words_by_tid.get(t, [])[:10]:
                if isinstance(w, str) and w.strip():
                    norm = normalize_term(w)
                    counter[norm] += float(s)
        tops = [w for w, _ in counter.most_common(4)]
        group_top_words[gid] = tops
        gid_label[gid] = "・".join(tops) if tops else f"group_{gid}"

    # 時系列（統合）
    tot = compute_topics_over_time(topic_model, df_valid["message_clean"].tolist(),
                                   topics_valid, df_valid["timestamp"].tolist(), nr_bins)
    # raw topic -> group
    raw2g = {}
    for gid, members in enumerate(groups):
        for t in members: raw2g[t] = gid
    tot["Group"] = tot["Topic"].map(raw2g).astype(int)

    sums = tot.groupby("Timestamp")["Frequency"].sum().rename("total")
    df_g = (tot.groupby(["Group", "Timestamp"], as_index=False)["Frequency"].sum()
              .merge(sums, left_on="Timestamp", right_index=True, how="left"))
    df_g["Percentage"] = 100.0 * df_g["Frequency"] / df_g["total"].clip(lower=1)
    df_g = df_g.drop(columns=["total"])

    # 可視化: 各配信者のTop-10時系列
    plot_top_groups(df_g, gid_label,
                    out_png=os.path.join(OUT_DIR, "timelines", f"{os.path.basename(csv_file).replace('.csv','')}_timeline.png"),
                    title=f"Topics Over Time (Top-{topk_plot}) : {os.path.basename(csv_file)} [{parse_country_from_filename(csv_file)}]",
                    top_k=topk_plot)

    return StreamData(
        file_path=os.path.basename(csv_file),
        country=parse_country_from_filename(csv_file),
        df_valid=df_valid,
        topics_valid=topics_valid,
        groups=groups,
        gid_label=gid_label,
        group_timeseries=df_g,
        nr_bins=nr_bins,
        group_top_words=group_top_words,
    )

def plot_top_groups(df_g: pd.DataFrame, labels: Dict[int, str], out_png: str, title: str, top_k: int = 10):
    os.makedirs(os.path.dirname(out_png), exist_ok=True)
    order = (df_g.groupby("Group")["Frequency"].sum().sort_values(ascending=False))
    top_groups = order.index.tolist()[:top_k]
    plt.figure(figsize=(12,6))
    for gid in top_groups:
        d = df_g[df_g["Group"] == gid].sort_values("Timestamp")
        if d.empty: continue
        label = labels.get(gid, f"G{gid}")
        if len(label) > 40: label = label[:37] + "..."
        plt.plot(d["Timestamp"], d["Percentage"], marker=".", linewidth=1.2, label=label)
    plt.title(title); plt.xlabel("Time"); plt.ylabel("Percentage of comments")
    plt.legend(ncol=2, fontsize=9, frameon=False); plt.xticks(rotation=45)
    plt.tight_layout(); plt.savefig(out_png, dpi=220); plt.close()
    print(f"Saved timeline: {out_png}")

# -------------------------
# イベント抽出・照合・テキスト距離
# -------------------------
def detect_events(stream: StreamData, n_events: int = 5, focus_top: Optional[int] = None) -> List[Dict[str, object]]:
    """
    各グループ（トピック統合）の時系列からピークイベントを抽出する。

    Parameters
    ----------
    stream : StreamData
        1つの配信の解析結果。
    n_events : int
        各グループから抽出するピークの最大数。
    focus_top : int or None
        トピックグループを総出現回数の多い順に限定する数。
        例: 10 を指定すると、コメント数の多い上位10グループのみからピーク検出を行う。
        None の場合はすべてのグループを対象とする。

    Returns
    -------
    List[Dict[str, object]]
        検出されたイベントのリスト。
    """
    events: List[Dict[str, object]] = []
    # 対象グループの決定
    if focus_top is not None and focus_top > 0:
        sums = stream.group_timeseries.groupby("Group")["Frequency"].sum()
        groups_to_use = sums.sort_values(ascending=False).head(focus_top).index.tolist()
    else:
        groups_to_use = sorted(stream.group_timeseries["Group"].unique())
    # Binning 再現
    bins = build_relative_time_bins(stream.df_valid["timestamp"], stream.nr_bins)
    for gid in groups_to_use:
        gdf = stream.group_timeseries[stream.group_timeseries["Group"] == gid]
        if gdf.empty:
            continue
        # Bin assignment
        bin_edges = list(zip(bins.left, bins.right))
        counts = np.zeros(len(bins), dtype=float)
        for _, r in gdf.iterrows():
            ts = r["Timestamp"]
            b = None
            for bi, (lft, rgt) in enumerate(bin_edges):
                if ts >= lft and ts < rgt:
                    b = bi
                    break
            if b is None:
                centers = np.array([iv.left.value for iv in bins], dtype=np.int64)
                b = int(np.argmin(np.abs(centers - int(ts.value))))
            counts[b] += float(r["Frequency"])
        # 平滑化→ピーク抽出
        y = smooth_series(counts, k=5)
        peak_idx = local_peaks(y, n_keep=n_events)
        for b in peak_idx:
            events.append({
                "group_id": int(gid),
                "bin_id": int(b),
                "peak_time": bins[b].left,
                "top_words": stream.group_top_words.get(gid, []),
                "label": stream.gid_label.get(gid, f"group_{gid}")
            })
    return events

def match_events_across_streams(
    events_by_stream: Dict[str, List[Dict[str, object]]],
    word_th: float,
    time_th: int,
    embed_th: Optional[float] = None,
) -> Dict[Tuple[str, int], int]:
    """
    多数のイベントをペアワイズで比較し、類似するイベントを同一IDに統合する。

    比較には以下の条件を使用する：
      1. Top-word集合のJaccard類似度が `word_th` 以上。
      2. 発生binが `time_th` 以下の差で近接している。
      3. イベント埋め込みベクトル（平均コメントベクトル）のコサイン類似度が `embed_th` 以上
         （`embed_th` が None の場合はこの条件を無視）。

    これにより単純なJaccardと時間だけでなく、語句が異なる言語でも内容が近い場合を拾える。

    Parameters
    ----------
    events_by_stream : dict
        ストリームごとに抽出したイベントを格納した辞書。
        各イベントdictには 'top_words', 'bin_id', 'embedding' (optional) などが含まれる必要がある。
    word_th : float
        トピックの上位語集合で計算したJaccard類似度の閾値。
    time_th : int
        イベント発生binの差の許容範囲。
    embed_th : float or None
        イベント埋め込みベクトル同士のコサイン類似度閾値。Noneのときはチェックしない。

    Returns
    -------
    dict
        (stream_key, event_index) -> unified_event_id のマッピング
    """
    items = []
    # Flatten events with their stream key and index
    for key, evts in events_by_stream.items():
        for i, evt in enumerate(evts):
            items.append((key, i, evt))
    # DSU setup
    parent: Dict[Tuple[str,int], Tuple[str,int]] = {(k,i):(k,i) for k,i,_ in items}
    def find(x: Tuple[str,int]) -> Tuple[str,int]:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def union(x: Tuple[str,int], y: Tuple[str,int]) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[ry] = rx
    # Pairwise comparisons
    for a in range(len(items)):
        ka, ia, ea = items[a]
        for b in range(a+1, len(items)):
            kb, ib, eb = items[b]
            # 同一ストリーム内のイベントはマージしない
            if ka == kb:
                continue
            # Jaccard on top words
            # 各イベントの top_words を正規化（用語マッピング）してJaccard類似度を計算
            sa_raw = ea.get("top_words", [])
            sb_raw = eb.get("top_words", [])
            sa = {normalize_term(w) for w in sa_raw if isinstance(w, str) and w.strip()}
            sb = {normalize_term(w) for w in sb_raw if isinstance(w, str) and w.strip()}
            if not sa and not sb:
                continue
            # Jaccard similarity of normalized sets
            jacc = len(sa & sb) / (len(sa | sb) + 1e-12)
            if jacc < word_th:
                continue
            # Time proximity
            if abs(int(ea.get("bin_id", -1)) - int(eb.get("bin_id", -1))) > time_th:
                continue
            # Embedding similarity (optional)
            if embed_th is not None:
                emb_a = ea.get("embedding")
                emb_b = eb.get("embedding")
                # どちらか欠如ならスキップ
                if emb_a is None or emb_b is None:
                    continue
                # 正規化済みベクトルとしてコサイン類似度
                num = float(np.dot(emb_a, emb_b))
                # 既にnormalize_embeddings=Trueで生成しているのでnormは≈1
                if num < embed_th:
                    continue
            # All conditions satisfied → union
            union((ka, ia), (kb, ib))
    # Assign unified IDs
    root2id: Dict[Tuple[str,int], int] = {}
    event_map: Dict[Tuple[str,int], int] = {}
    nxt = 0
    for k,i,_ in items:
        r = find((k,i))
        if r not in root2id:
            root2id[r] = nxt
            nxt += 1
        event_map[(k,i)] = root2id[r]
    return event_map

def extract_event_comments(stream: StreamData, event: Dict[str, object], peak_pad: int) -> Tuple[List[str], List[str]]:
    """
    イベントに該当するコメントとその言語リストを抽出する。
    戻り値は (コメントのリスト, 言語のリスト)
    """
    gid, bin_id = event["group_id"], int(event["bin_id"])
    bins = build_relative_time_bins(stream.df_valid["timestamp"], stream.nr_bins)
    raw2g: Dict[int, int] = {}
    for g_id, members in enumerate(stream.groups):
        for t in members:
            raw2g[t] = g_id
    low, high = max(0, bin_id - peak_pad), min(stream.nr_bins - 1, bin_id + peak_pad)
    comments: List[str] = []
    langs: List[str] = []
    # 1:1対応のため topics_valid は df_valid と同じ順
    for i, row in stream.df_valid.iterrows():
        topic_id = stream.topics_valid[i]
        if topic_id == -1 or raw2g.get(topic_id, -1) != gid:
            continue
        ts = row["timestamp"]
        b = None
        for bi, iv in enumerate(bins):
            if ts >= iv.left and ts < iv.right:
                b = bi
                break
        if b is None:
            centers = np.array([iv.left.value for iv in bins], dtype=np.int64)
            b = int(np.argmin(np.abs(centers - int(ts.value))))
        if low <= b <= high:
            comments.append(row["message_clean"])
            # 言語列があれば取得
            lang = row.get("lang") if isinstance(row, pd.Series) else None
            if lang is None and stream.languages is not None and i < len(stream.languages):
                lang = stream.languages.iloc[i]
            langs.append(lang if isinstance(lang, str) else "unk")
    return comments, langs

def js_distance(p: np.ndarray, q: np.ndarray) -> float:
    p = p.astype(float); q = q.astype(float)
    p = p / (p.sum() + 1e-12); q = q / (q.sum() + 1e-12)
    m = 0.5 * (p + q)
    kl_pm = np.sum(np.where(p > 0, p * np.log((p + 1e-12) / (m + 1e-12)), 0.0))
    kl_qm = np.sum(np.where(q > 0, q * np.log((q + 1e-12) / (m + 1e-12)), 0.0))
    return float(np.sqrt(0.5 * (kl_pm + kl_qm)))

def compute_lexical_distance(comments_a: List[str], comments_b: List[str], top_n: int = 1000) -> float:
    """
    コメントリスト同士の語彙分布差（Jensen–Shannon距離）を計算する。
    トークンは用語マッピング辞書で正規化してから頻度を数えるため、
    言語や表記揺れが異なっても類義語として扱うことができる。
    """
    ca, cb = Counter(), Counter()
    for txt in comments_a:
        for w in txt.split():
            norm = normalize_term(w)
            ca[norm] += 1
    for txt in comments_b:
        for w in txt.split():
            norm = normalize_term(w)
            cb[norm] += 1
    combined = ca + cb
    # 上位単語を最大 top_n まで
    vocab = [w for w, _ in combined.most_common(top_n)]
    if not vocab:
        return 0.0
    va = np.array([ca.get(w, 0) for w in vocab], dtype=float)
    vb = np.array([cb.get(w, 0) for w in vocab], dtype=float)
    return js_distance(va, vb)

# -------------------------
# 可視化: ヒートマップ・距離行列・ワードクラウド
# -------------------------
def save_csv_and_png_heatmap(df: pd.DataFrame, out_csv: str, out_png: str, title: str):
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    # 常に完全な表をCSVに保存
    df.to_csv(out_csv, index=True, encoding="utf-8-sig")
    # 可視化は数値列のみに限定してエラーを防ぐ
    df_plot = df.select_dtypes(include=[np.number])
    if df_plot is None or df_plot.empty:
        print(f"[WARN] Heatmap skipped for {out_png}: no numeric data to plot")
        return
    # 図サイズ調整（論文向けにやや広め）
    fig_width = max(8, 0.6 * len(df_plot.columns) + 3)
    fig_height = max(8, 0.5 * len(df_plot.index) + 3)
    plt.figure(figsize=(fig_width, fig_height))
    vals = df_plot.values.astype(float)
    # presence（0/1）の見やすい配色に自動調整
    unique_vals = np.unique(vals)
    is_binary = set(unique_vals.tolist()) <= {0.0, 1.0}
    if is_binary:
        im = plt.imshow(vals, aspect="auto", cmap="Greens", vmin=0, vmax=1)
    else:
        vmin = float(np.nanmin(vals)) if np.isfinite(vals).any() else 0.0
        vmax = float(np.nanmax(vals)) if np.isfinite(vals).any() else 1.0
        if vmin == vmax:
            vmin, vmax = 0.0, 1.0
        im = plt.imshow(vals, aspect="auto", cmap="viridis", vmin=vmin, vmax=vmax)
    plt.title(title)
    plt.xlabel("Streams")
    plt.ylabel("Events")
    # x軸ラベル: ファイル名（または列名）を改行付きにして長さを調整
    x_labels = []
    for c in df_plot.columns:
        s = os.path.basename(str(c))
        if len(s) > 12:
            s = '\n'.join([s[i:i+12] for i in range(0, len(s), 12)])
        x_labels.append(s)
    plt.xticks(range(len(df_plot.columns)), x_labels, rotation=40, ha="right", fontsize=8)
    # y軸ラベル: イベントラベルが長い場合は改行を挿入（元のindexをそのまま利用）
    y_labels = []
    for idx_label in df_plot.index:
        s = str(idx_label)
        if len(s) > 20:
            s = '\n'.join([s[i:i+20] for i in range(0, len(s), 20)])
        y_labels.append(s)
    plt.yticks(range(len(df_plot.index)), y_labels, fontsize=9)
    cb = plt.colorbar(im); cb.set_label("Similarity" if not is_binary else "Presence")
    # セル注釈（小さめの行列のみ）
    total_cells = vals.shape[0] * vals.shape[1]
    if total_cells <= 400:
        for i in range(vals.shape[0]):
            for j in range(vals.shape[1]):
                v = vals[i, j]
                if is_binary:
                    if v >= 0.5:
                        plt.text(j, i, "1", ha="center", va="center", color="white", fontsize=9, fontweight="bold")
                else:
                    txt_color = "white" if v > (np.nanmin(vals) + np.nanmax(vals)) / 2 else "black"
                    try:
                        plt.text(j, i, f"{v:.2f}", ha="center", va="center", color=txt_color, fontsize=8)
                    except Exception:
                        pass
    # グリッド線
    plt.grid(which='both', color='lightgray', linestyle='-', linewidth=0.3)
    plt.gca().set_xticks(np.arange(-0.5, vals.shape[1], 1), minor=True)
    plt.gca().set_yticks(np.arange(-0.5, vals.shape[0], 1), minor=True)
    plt.grid(which='minor', color='lightgray', linestyle='-', linewidth=0.3)
    plt.gca().tick_params(which='minor', bottom=False, left=False)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(out_png, dpi=220)
    plt.close()
    print(f"Saved heatmap: {out_png}")

def _save_matched_summary_table(presence_df: pd.DataFrame, matched_df: pd.DataFrame, out_png: str, top_k: int = 15) -> None:
    """一致イベントの概要テーブルを PNG で保存。
    列: Time, Best Pair, Similarity, Label
    """
    try:
        if presence_df is None or presence_df.empty or matched_df is None or matched_df.empty:
            return
        # presence の time_label/row_label と matched の (group_id,bin_id) を突合
        lef = presence_df[["group_id","bin_id","time_label","row_label"]].drop_duplicates()
        rig = matched_df.copy()
        # best_pair/best_sim が無い旧データに対応
        if "best_pair" not in rig.columns:
            # best ペアは (lex) が最小のペアから推定
            lex_cols = [c for c in rig.columns if c.endswith("(lex)")]
            if lex_cols:
                best_idx = np.argmin(rig[lex_cols].values, axis=1)
                rig["best_pair"] = [lex_cols[i].replace(" (lex)", "") for i in best_idx]
                rig["best_sim"] = 1.0 - np.take_along_axis(rig[lex_cols].values, best_idx.reshape(-1,1), axis=1).ravel()
        m = pd.merge(rig, lef, on=["group_id","bin_id"], how="left")
        # 表示用列に整形
        view = m[["time_label","best_pair","best_sim","label"]].copy()
        view = view.rename(columns={"time_label":"Time","best_pair":"Best Pair","best_sim":"Similarity","label":"Topic"})
        # 並べ替え（Similarity 降順、Time 昇順）
        if "Similarity" in view.columns:
            view = view.sort_values(["Similarity","Time"], ascending=[False, True])
        else:
            view = view.sort_values(["Time"], ascending=True)
        # 上位のみ
        if len(view) > top_k:
            view = view.head(top_k)
        # 数値の丸め
        if "Similarity" in view.columns:
            view["Similarity"] = view["Similarity"].map(lambda x: f"{x:.2f}")
        # 保存
        save_df_as_table_png(view, out_png, title="Matched Events Summary (Top)")
    except Exception as e:
        print(f"[WARN] failed to save matched summary: {e}")

def save_png_distance_matrix(mat: pd.DataFrame, out_csv: str, out_png: str, title: str):
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    mat.to_csv(out_csv, index=True, encoding="utf-8-sig")
    plt.figure(figsize=(max(6, 0.35*len(mat.columns)+3), max(6, 0.35*len(mat.index)+3)))
    plt.imshow(mat.values, vmin=0, vmax=1)
    plt.title(title); plt.xlabel("Stream"); plt.ylabel("Stream")
    ticks = range(len(mat.columns))
    labels = [os.path.basename(c) for c in mat.columns]
    plt.xticks(ticks, labels, rotation=45, ha="right", fontsize=9)
    plt.yticks(ticks, labels, fontsize=9)
    cb = plt.colorbar(); cb.set_label("Jensen–Shannon distance")
    plt.tight_layout(); plt.savefig(out_png, dpi=220); plt.close()
    print(f"Saved distance matrix: {out_png}")

def save_emoji_timeline_heatmap(df: pd.DataFrame, out_csv: str, out_png: str, title: str):
    """Save an emoji timeline heatmap (time x emoji) per stream.
    df: index=time label (e.g., HH:MM), columns=emoji char, values=counts.
    """
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    df.to_csv(out_csv, index=True, encoding="utf-8-sig")
    if df.empty:
        print(f"[WARN] Emoji timeline empty: {out_png}")
        return
    plt.figure(figsize=(max(8, 0.5*len(df.columns)+3), max(6, 0.35*len(df.index)+2)))
    vals = df.values.astype(float)
    im = plt.imshow(vals, aspect="auto", cmap="magma")
    plt.title(title)
    plt.xlabel("Emoji")
    plt.ylabel("Time")
    plt.xticks(range(len(df.columns)), list(df.columns), rotation=0, fontsize=12)
    plt.yticks(range(len(df.index)), list(df.index), fontsize=9)
    cb = plt.colorbar(im); cb.set_label("Count")
    plt.tight_layout(); plt.savefig(out_png, dpi=200); plt.close()
    print(f"Saved emoji timeline: {out_png}")

def make_wordcloud(texts: List[str], out_png: str):
    from wordcloud import WordCloud
    os.makedirs(os.path.dirname(out_png), exist_ok=True)
    # textsが空、もしくは文字列がない場合はワードクラウドを生成しない
    if not texts:
        print(f"[WARN] Wordcloud skipped for {out_png}: no texts")
        return
    txt = " ".join(texts).strip()
    # トークンが1個未満ならスキップ
    tokens = txt.split()
    if len(tokens) == 0:
        print(f"[WARN] Wordcloud skipped for {out_png}: no tokens to plot")
        return
    # WordCloud 用フォントを自動選択。日本語を含む場合は使用中の日本語フォントからファイルパスを取得する。
    font_path = None
    try:
        if _used_jp_font:
            from matplotlib import font_manager as _fm
            try:
                font_path = _fm.findfont(_used_jp_font, fontext="ttf")
            except Exception:
                font_path = None
    except Exception:
        font_path = None
    # WordCloud生成
    wc = WordCloud(
        width=1200,
        height=800,
        background_color="white",
        font_path=font_path if font_path else None,
        collocations=False,
    )
    try:
        wc.generate(txt)
        wc.to_file(out_png)
        print(f"Saved wordcloud: {out_png}")
    except Exception as e:
        # ワードクラウド生成に失敗した場合は警告のみ出力
        print(f"[WARN] wordcloud failed for {out_png}: {e}")

# -------------------------
# 引数処理
# -------------------------
def parse_args():
    p = argparse.ArgumentParser(description="Compare events across multiple streams for the same match.")
    # 複数ファイル or フォルダ＋パターン
    p.add_argument("--files", nargs="+", help="分析するCSVを複数指定（スペース区切り）")
    p.add_argument("--folder", type=str, help="CSVが入っているフォルダ")
    p.add_argument("--pattern", type=str, default="*.csv", help="ファイルパターン（例: *.csv）")
    # 既存パラメータ
    p.add_argument("--time-bins", type=int, default=300)
    p.add_argument("--peak-pad", type=int, default=1)
    p.add_argument("--jaccard-th", type=float, default=0.6)
    p.add_argument("--word-match-th", type=float, default=0.4)
    p.add_argument("--time-match-th", type=int, default=1)
    # cross-lingual embedding similarity threshold for event matching
    p.add_argument("--embedding-match-th", type=float, default=None,
                   help="埋め込みベクトルのコサイン類似度閾値（Noneならチェックしない）")
    p.add_argument("--n-events", type=int, default=5)
    p.add_argument("--topk", type=int, default=10, help="時系列描画の上位グループ数")
    p.add_argument("--save-json", action="store_true")
    # 可視化の制限: 類似度ヒートマップに表示する一致イベントの上位件数（コメント量の多い順）
    p.add_argument("--top-matched", type=int, default=5,
                   help="matched_event_presence.png に表示する上位イベント数（コメント総数の多い順、0で制限なし）")
    # 上位グループに限定する数（例: 10→コメント数が多い上位10グループのみ）
    p.add_argument("--focus-top", type=int, default=10, help="ピーク検出を行う対象グループ数（Noneの場合は全グループ）")
    # Emoji timeline 可視化設定
    p.add_argument("--emoji-topk", type=int, default=10, help="各配信の絵文字タイムラインに表示する上位絵文字数")
    args = p.parse_args()

    # --folder/--pattern を --files に展開
    if (not args.files) and args.folder:
        from pathlib import Path
        files = sorted(str(p) for p in Path(args.folder).glob(args.pattern))
        if not files:
            raise SystemExit(f"No files matched: {args.folder}/{args.pattern}")
        args.files = files
    if not args.files:
        p.error("either --files or --folder must be provided")
    # フルパス化
    args.files = [os.path.abspath(f) for f in args.files]
    return args

# -------------------------
# メイン
# -------------------------
def main():
    args = parse_args()
    embedding_model = SentenceTransformer(EMB_NAME)

    # ストリーム処理
    streams: Dict[str, StreamData] = {}
    for csv_file in args.files:
        if not os.path.exists(csv_file):
            print(f"File not found: {csv_file}"); continue
        sd = process_stream(csv_file, embedding_model, args.jaccard_th, args.time_bins, topk_plot=args.topk)
        if sd: streams[csv_file] = sd
    if len(streams) < 2:
        print("Need at least two valid streams to compare events."); return

    # 各ストリームでイベント抽出（コメントが多い上位グループを優先）
    events_by_stream: Dict[str, List[Dict[str, object]]] = {}
    for key, sd in streams.items():
        events_by_stream[key] = detect_events(sd, n_events=args.n_events, focus_top=args.focus_top)

    # 各イベントにコメント埋め込みベクトルを付与する
    # まずはイベントのコメントを抽出し、平均埋め込みを計算（normalize_embeddings=Trueであるため平均後も単位長に再正規化）
    for stream_key, evts in events_by_stream.items():
        for evt in evts:
            try:
                comments, _langs = extract_event_comments(streams[stream_key], evt, args.peak_pad)
                if comments:
                    vecs = embedding_model.encode(comments, batch_size=32, show_progress_bar=False, normalize_embeddings=True)
                    # 2D array (n_comments x dim)
                    # 平均した後、再正規化
                    mean_vec = np.mean(vecs, axis=0)
                    norm = np.linalg.norm(mean_vec) + 1e-12
                    mean_vec = mean_vec / norm
                else:
                    # コメントがない場合はゼロベクトル
                    dim = embedding_model.get_sentence_embedding_dimension()
                    mean_vec = np.zeros(dim, dtype=float)
                evt["embedding"] = mean_vec
            except Exception:
                # エラー時はembeddingをNoneに
                evt["embedding"] = None
    # 共通イベント照合
    event_map = match_events_across_streams(
        events_by_stream,
        args.word_match_th,
        args.time_match_th,
        embed_th=args.embedding_match_th,
    )
    if not event_map:
        print("一致する共通イベントが見つかりませんでした。閾値（--time-match-th, --word-match-th, --jaccard-th）を調整して再実行してください。")
        return

    # 共通イベントIDごとにグルーピング
    events_by_id: Dict[int, Dict[str, object]] = defaultdict(lambda: {"streams": {}})
    for stream_key, evts in events_by_stream.items():
        for i, evt in enumerate(evts):
            eid = event_map[(stream_key, i)]
            events_by_id[eid]["label"] = evt["label"]
            events_by_id[eid]["bin_id"] = evt["bin_id"]
            events_by_id[eid]["streams"][stream_key] = evt

    # 各共通イベントのコメント収集 & 距離計算
    results = []
    raw_data = {}
    # ヒートマップ用：イベント×配信者 行列
    stream_names = [os.path.basename(k) for k in streams.keys()]
    event_presence = []
    for eid, info in events_by_id.items():
        # 同じイベントに含まれる配信者が1つしかない場合はスキップ
        # 「同じ時間帯・同じトピックで盛り上がった」もののみ比較対象とするため
        if len(info["streams"]) < 2:
            continue
        label = info["label"]; bin_id = int(info["bin_id"])
        # コメント収集
        streams_comments: Dict[str, List[str]] = {}
        streams_langs: Dict[str, List[str]] = {}
        row_presence = {}
        for stream_key in streams.keys():
            if stream_key in info["streams"]:
                comments, langs = extract_event_comments(streams[stream_key], info["streams"][stream_key], args.peak_pad)
                streams_comments[stream_key] = comments
                streams_langs[stream_key] = langs
                row_presence[os.path.basename(stream_key)] = 1
            else:
                streams_comments[stream_key] = []
                streams_langs[stream_key] = []
                row_presence[os.path.basename(stream_key)] = 0

        # 距離行列（語彙・言語・絵文字のスタイル差）
        keys = list(streams_comments.keys())
        n = len(keys)
        dmat = np.zeros((n, n), dtype=float)
        lang_mat = np.zeros((n, n), dtype=float)
        emoji_mat = np.zeros((n, n), dtype=float)
        for i in range(n):
            for j in range(n):
                if i == j:
                    dmat[i, j] = 0.0
                    lang_mat[i, j] = 0.0
                    emoji_mat[i, j] = 0.0
                elif i < j:
                    # 語彙差
                    d = compute_lexical_distance(streams_comments[keys[i]], streams_comments[keys[j]])
                    dmat[i, j] = d; dmat[j, i] = d
                    # 言語分布差
                    lang_dist_a = compute_language_distribution(streams_langs[keys[i]])
                    lang_dist_b = compute_language_distribution(streams_langs[keys[j]])
                    ld = js_distance_distribution(lang_dist_a, lang_dist_b)
                    lang_mat[i, j] = ld; lang_mat[j, i] = ld
                    # 絵文字比率差
                    er_a = compute_emoji_ratio(streams_comments[keys[i]])
                    er_b = compute_emoji_ratio(streams_comments[keys[j]])
                    emoji_diff = abs(er_a - er_b)
                    emoji_mat[i, j] = emoji_diff; emoji_mat[j, i] = emoji_diff

        # 平均距離などを結果に
        tril = dmat[np.tril_indices(n, k=-1)]
        avg_dist = float(np.mean(tril)) if tril.size else 0.0
        tril_lang = lang_mat[np.tril_indices(n, k=-1)]
        avg_lang_dist = float(np.mean(tril_lang)) if tril_lang.size else 0.0
        tril_emoji = emoji_mat[np.tril_indices(n, k=-1)]
        avg_emoji_diff = float(np.mean(tril_emoji)) if tril_emoji.size else 0.0
        result = {
            "event_id": int(eid),
            "label": label,
            "peak_bin": int(bin_id),
            "avg_js_distance": avg_dist,
            "avg_language_distance": avg_lang_dist,
            "avg_emoji_difference": avg_emoji_diff,
        }
        # 各ペアごとの値を追加
        # 事前に各配信の感情・スタイル特徴を計算
        sentiments = {k: compute_sentiment_metrics(streams_comments[k]) for k in keys}
        styles = {k: compute_style_profile(streams_comments[k]) for k in keys}
        for i in range(n):
            for j in range(i+1, n):
                name = f"{os.path.basename(keys[i])} vs {os.path.basename(keys[j])}"
                result[f"{name} (lex)"] = float(dmat[i, j])
                result[f"{name} (lang)"] = float(lang_mat[i, j])
                result[f"{name} (emoji)"] = float(emoji_mat[i, j])
        results.append(result)

        # JSON用
        if args.save_json:
            raw_data[eid] = {os.path.basename(k): v for k, v in streams_comments.items()}

        # ワードクラウド出力
        evt_dir = os.path.join(OUT_DIR, "wordclouds", f"event_{eid}")
        for stream_key, texts in streams_comments.items():
            out_wc = os.path.join(evt_dir, f"WC_{os.path.basename(stream_key).replace('.csv','')}.png")
            try:
                make_wordcloud(texts, out_wc)
            except Exception as e:
                print(f"[WARN] wordcloud failed for {stream_key}: {e}")

        # イベント×配信者 presence 行
        event_presence.append({"event_id": int(eid), **row_presence})

    # === 出力: イベント比較結果 ===
    # スキップされたイベントがある場合に空の結果を防ぐ
    if results:
        results_df = pd.DataFrame(results).sort_values(["avg_js_distance", "event_id"])
    else:
        results_df = pd.DataFrame(results)
    out_csv = os.path.join(OUT_DIR, "event_comparison_results.csv")
    results_df.to_csv(out_csv, index=False, encoding="utf-8-sig")
    print(f"Saved: {out_csv}")

    # 共通イベント presence ヒートマップ
    if event_presence:
        eventmap_df = pd.DataFrame(event_presence)
        # event_id列が存在する場合はインデックス設定
        if "event_id" in eventmap_df.columns:
            eventmap_df = eventmap_df.set_index("event_id").reindex(sorted(eventmap_df["event_id"].unique()))
        hm_csv = os.path.join(OUT_DIR, "event_eventmap.csv")
        hm_png = os.path.join(OUT_DIR, "event_eventmap.png")
        save_csv_and_png_heatmap(eventmap_df, hm_csv, hm_png, title="Shared Events Presence (1=matched)")
    else:
        print("[INFO] No matched events to create event presence heatmap.")

    # ペア距離の平均 → 平均距離行列（イベントごと平均してもよいが、ここは全イベント平均）
    # 全イベントの距離を合算して平均
    # 構築: ストリーム順 keys に合わせる
    stream_keys = list(streams.keys())
    n = len(stream_keys)
    acc = np.zeros((n, n), dtype=float); cnt = np.zeros((n, n), dtype=int)
    for eid, info in events_by_id.items():
        # 同じイベントに含まれる配信者が2つ未満ならグローバル距離には加算しない
        if len(info["streams"]) < 2:
            continue
        # 各イベントで距離を計算
        comments: Dict[str, List[str]] = {}
        for k in stream_keys:
            if k in info["streams"]:
                cmt, _langs = extract_event_comments(streams[k], info["streams"][k], args.peak_pad)
                comments[k] = cmt
            else:
                comments[k] = []
        for i in range(n):
            for j in range(i+1, n):
                d = compute_lexical_distance(comments[stream_keys[i]], comments[stream_keys[j]])
                acc[i, j] += d; acc[j, i] += d
                cnt[i, j] += 1; cnt[j, i] += 1
    with np.errstate(divide='ignore', invalid='ignore'):
        avg = np.where(cnt>0, acc/np.maximum(cnt,1), 0.0)
    names = [os.path.basename(k) for k in stream_keys]
    dist_df = pd.DataFrame(avg, index=names, columns=names)
    dist_csv = os.path.join(OUT_DIR, "event_comparison_distance_matrix.csv")
    dist_png = os.path.join(OUT_DIR, "event_comparison_results.png")
    save_png_distance_matrix(dist_df, dist_csv, dist_png, title="Average JS Distance across Shared Events")

    # JSON保存
    if args.save_json:
        with open(os.path.join(OUT_DIR, "event_comments.json"), "w", encoding="utf-8") as f:
            json.dump(raw_data, f, ensure_ascii=False, indent=2)
    print(f"Saved: {os.path.join(OUT_DIR, 'event_comments.json')}")

    print("All done")

    # === 新機能: 同時間帯・同トピックで盛り上がったイベント間の比較 ===
    # 複数配信者が同じグループIDとbin ID (ピーク時間帯) で盛り上がっているイベントを抽出し、
    # 語彙・言語・絵文字の違いを定量化して出力します。
    print("Matching events on exact group & bin across streams ...")
    # (group_id, bin_id) -> {stream_key: event_dict}
    events_by_group_bin: Dict[Tuple[int, int], Dict[str, Dict[str, object]]] = defaultdict(dict)
    for stream_key, evts in events_by_stream.items():
        for evt in evts:
            key = (int(evt.get("group_id", -1)), int(evt.get("bin_id", -1)))
            events_by_group_bin[key][stream_key] = evt
    matched_results = []
    matched_presence = []  # 設定: group-binごとのpresence（時間帯・ラベル・類似度の注釈付き）
    matched_similarity = []  # 新規: 参照配信に対する各配信の類似度（1-JS）, 行注釈付き
    matched_meta = []  # 行メタデータ: gid,bin,participants,total_comments
    # 一致したイベントのコメント内容を保存するための辞書
    matched_comments: Dict[str, Dict[str, List[str]]] = {}
    # 詳細情報の保存用: 各マッチイベント×配信者ごとの行を蓄積
    matched_details_all: List[Dict[str, object]] = []
    for (gid, bin_id), evts_dict in events_by_group_bin.items():
        # 2つ以上の配信者が該当する場合のみ比較
        if len(evts_dict) < 2:
            continue
        # グループラベルは代表のものを採用
        label = list(evts_dict.values())[0].get("label", f"group_{gid}")
        # コメント・言語を収集
        comments_by_stream: Dict[str, List[str]] = {}
        langs_by_stream: Dict[str, List[str]] = {}
        presence_row = {"group_id": gid, "bin_id": bin_id, "label": label}
        for stream_key in streams.keys():
            if stream_key in evts_dict:
                comments, langs = extract_event_comments(streams[stream_key], evts_dict[stream_key], args.peak_pad)
                comments_by_stream[stream_key] = comments
                langs_by_stream[stream_key] = langs
                presence_row[os.path.basename(stream_key)] = 1
            else:
                comments_by_stream[stream_key] = []
                langs_by_stream[stream_key] = []
                presence_row[os.path.basename(stream_key)] = 0
        # 距離行列を計算
        keys = list(streams.keys())
        n = len(keys)
        dmat = np.zeros((n, n), dtype=float)
        lang_mat = np.zeros((n, n), dtype=float)
        emoji_mat = np.zeros((n, n), dtype=float)
        for i in range(n):
            for j in range(i+1, n):
                d = compute_lexical_distance(comments_by_stream[keys[i]], comments_by_stream[keys[j]])
                dmat[i, j] = d; dmat[j, i] = d
                ld = js_distance_distribution(
                    compute_language_distribution(langs_by_stream[keys[i]]),
                    compute_language_distribution(langs_by_stream[keys[j]])
                )
                lang_mat[i, j] = ld; lang_mat[j, i] = ld
                ediff = abs(
                    compute_emoji_ratio(comments_by_stream[keys[i]]) - compute_emoji_ratio(comments_by_stream[keys[j]])
                )
                emoji_mat[i, j] = ediff; emoji_mat[j, i] = ediff
        # 感情・スタイル特徴（ペア距離算出用）
        sentiments = {k: compute_sentiment_metrics(comments_by_stream.get(k, [])) for k in keys}
        styles = {k: compute_style_profile(comments_by_stream.get(k, [])) for k in keys}
        # === 追加: この一致イベント（同一group×bin）の"時間帯"と"各配信のラベル(上位語)"、"類似度(1-JS距離)"を注釈として作成 ===
        # 参加配信（コメントが存在する＝presence=1）の抽出
        present_streams_basename: List[str] = []
        present_streams_keys: List[str] = []
        for sk in streams.keys():
            if sk in evts_dict:
                present_streams_keys.append(sk)
                present_streams_basename.append(os.path.basename(sk))
        # 時間帯（絶対時刻の中心: ns since epoch）の代表値（中央値）を算出
        center_ns: List[int] = []
        stream_label_map: Dict[str, str] = {}
        stream_words_map: Dict[str, str] = {}
        for sk in present_streams_keys:
            evt_info = evts_dict[sk]
            stream_obj = streams[sk]
            bins = build_relative_time_bins(stream_obj.df_valid["timestamp"], stream_obj.nr_bins)
            b_local = int(evt_info.get("bin_id", -1))
            if 0 <= b_local < len(bins):
                interval = bins[b_local]
                center_ts = interval.left + (interval.right - interval.left)/2
                try:
                    center_ns.append(int(pd.Timestamp(center_ts).value))
                except Exception:
                    pass
            # 各配信のラベル（短縮版: 上位語 2〜3 語, なければ元ラベルを2語に）
            gid_local = int(evt_info.get("group_id", -1))
            top_words_local = stream_obj.group_top_words.get(gid_local, [])[:3]
            if top_words_local:
                short = ",".join(top_words_local)
            else:
                raw_label = str(evt_info.get("label", ""))
                toks = [normalize_term(w) for w in re.split(r"[\s・,，。!！?？]+", raw_label) if w]
                toks = [t for t in toks if len(t) > 1][:2]
                short = ",".join(toks) if toks else "topic"
            stream_label_map[os.path.basename(sk)] = short
            stream_words_map[os.path.basename(sk)] = short
        time_label = ""
        if center_ns:
            cen = pd.to_datetime(int(np.median(center_ns)))
            try:
                time_label = pd.Timestamp(cen).strftime("%H:%M")
            except Exception:
                # フォールバック: 分丸め
                minutes = int(round((pd.Timestamp(cen).value/1e9) / 60.0))
                time_label = f"{minutes:02d}:00"
        # ペアワイズの語彙類似度(1-JS距離)を計算し、最良ペアを抽出
        pair_sims: List[Tuple[str, str, float]] = []
        key_index = {k: i for i, k in enumerate(keys)}
        for i in range(len(present_streams_keys)):
            for j in range(i+1, len(present_streams_keys)):
                ki = key_index[present_streams_keys[i]]
                kj = key_index[present_streams_keys[j]]
                sim = float(max(0.0, min(1.0, 1.0 - dmat[ki, kj])))
                pair_sims.append((os.path.basename(present_streams_keys[i]), os.path.basename(present_streams_keys[j]), sim))
        best_pair_str = ""
        if pair_sims:
            # 類似度の高い順に
            pair_sims.sort(key=lambda x: x[2], reverse=True)
            a, b, s = pair_sims[0]
            # ラベルを取得
            la = stream_label_map.get(a, "")
            lb = stream_label_map.get(b, "")
            best_pair_str = f"{a}:{la} vs {b}:{lb}, sim={s:.2f}"
        # ペアワイズ類似度（1−JS）を列に展開（簡潔な列名: "A vs B"）
        sim_row: Dict[str, object] = {"group_id": gid, "bin_id": bin_id}
        for i in range(n):
            for j in range(i+1, n):
                base_i = os.path.basename(keys[i]).replace('.csv','')
                base_j = os.path.basename(keys[j]).replace('.csv','')
                name = f"{base_i} vs {base_j}"
                sim_val = float(max(0.0, min(1.0, 1.0 - dmat[i, j])))
                sim_row[name] = sim_val
        # 後段の注釈列は presence_row と揃える
        # 平均を計算
        tril = dmat[np.tril_indices(n, k=-1)]
        avg_lex = float(np.mean(tril)) if tril.size else 0.0
        tril_lang = lang_mat[np.tril_indices(n, k=-1)]
        avg_lang = float(np.mean(tril_lang)) if tril_lang.size else 0.0
        tril_emoji = emoji_mat[np.tril_indices(n, k=-1)]
        avg_emoji = float(np.mean(tril_emoji)) if tril_emoji.size else 0.0
        result: Dict[str, object] = {
            "group_id": gid,
            "bin_id": bin_id,
            "label": label,
            "avg_js_distance": avg_lex,
            "avg_language_distance": avg_lang,
            "avg_emoji_difference": avg_emoji,
        }
        # 各ストリームでの該当イベントの bin_id と label を記録する
        # 存在しない場合は空白にする
        for sk in streams.keys():
            base = os.path.basename(sk)
            if sk in evts_dict:
                evt_info = evts_dict[sk]
                # そのストリーム内でのbinやラベルを保存
                result[f"{base}_bin"] = int(evt_info.get("bin_id", -1))
                result[f"{base}_label"] = str(evt_info.get("label", ""))
            else:
                result[f"{base}_bin"] = ""
                result[f"{base}_label"] = ""
        # 各ペアの詳細を追加
        # ペアごとの詳細を追加（lex/lang/emojiに加え sentiment/style）
        pair_rows = []
        for i in range(n):
            for j in range(i+1, n):
                name = f"{os.path.basename(keys[i])} vs {os.path.basename(keys[j])}"
                lex = float(dmat[i, j])
                langd = float(lang_mat[i, j])
                emj = float(emoji_mat[i, j])
                result[f"{name} (lex)"] = lex
                result[f"{name} (lang)"] = langd
                result[f"{name} (emoji)"] = emj
                # sentiment/style 距離（平均絶対差）
                sdist = style_distance(sentiments[keys[i]], sentiments[keys[j]])
                tdist = style_distance(styles[keys[i]], styles[keys[j]])
                result[f"{name} (sentiment)"] = float(sdist)
                result[f"{name} (style)"] = float(tdist)
                pair_rows.append({
                    "group_id": gid,
                    "bin_id": bin_id,
                    "pair": name,
                    "lex_js": lex,
                    "lang_js": langd,
                    "emoji_diff": emj,
                    "sentiment_dist": float(sdist),
                    "style_dist": float(tdist),
                })
        matched_results.append(result)
        # 注釈情報をpresence_rowに追加（可視化時の行ラベルとして使用）
        if time_label:
            presence_row["time_label"] = time_label
        # 各配信のラベルも行に含めておく（CSVに残すため）
        for base, lab in stream_label_map.items():
            presence_row[f"{base}_label"] = lab
        if time_label and best_pair_str:
            presence_row["row_label"] = f"{time_label}, {best_pair_str}"
        else:
            # 短いラベル（参加配信の上位語から代表を構成）
            short_all = []
            for v in stream_words_map.values():
                for w in str(v).split(","):
                    if w and w not in short_all:
                        short_all.append(w)
            short_join = ",".join(short_all[:3]) if short_all else str(label)
            presence_row["row_label"] = f"{time_label}, {short_join}" if time_label else short_join
        matched_presence.append(presence_row)
        # similarity 行にも注釈を付与
        if time_label:
            sim_row["time_label"] = time_label
        sim_row["row_label"] = presence_row["row_label"]
        matched_similarity.append(sim_row)
        # 行メタ: 参加者数とコメント総数
        participants = int(sum(1 for sk in streams.keys() if sk in evts_dict))
        total_comments = int(sum(len(comments_by_stream.get(sk, [])) for sk in streams.keys()))
        matched_meta.append({
            "group_id": gid,
            "bin_id": bin_id,
            "participants": participants,
            "total_comments": total_comments,
            "time_label": time_label,
            "row_label": presence_row.get("row_label", ""),
        })

        # コメント内容を保存（空の配列も含む）
        evt_key = f"gid{gid}_bin{bin_id}"
        matched_comments[evt_key] = {}
        for sk in streams.keys():
            # 保存する際はファイル名のみをキーとする
            matched_comments[evt_key][os.path.basename(sk)] = comments_by_stream.get(sk, [])

        # イベント全体のコメントを使ってワードクラウドを生成
        # 各ストリームのコメントを結合して1つのリストに
        aggregated_comments: List[str] = []
        for _sk, comms in comments_by_stream.items():
            aggregated_comments.extend(comms)
        # 保存先ディレクトリ
        all_wc_dir = os.path.join(OUT_DIR, "wordclouds_matched", f"gid{gid}_bin{bin_id}")
        os.makedirs(all_wc_dir, exist_ok=True)
        wc_path = os.path.join(all_wc_dir, f"WC_ALL.png")
        try:
            make_wordcloud(aggregated_comments, wc_path)
        except Exception as e:
            print(f"[WARN] wordcloud failed for aggregated event gid{gid}_bin{bin_id}: {e}")

        # --- 詳細情報を収集: 各配信者ごとのbin範囲やラベルなど ---
        # event_id をgidとbin_idに基づいて生成
        event_identifier = f"gid{gid}_bin{bin_id}"
        for sk in streams.keys():
            base_name = os.path.basename(sk)
            if sk in evts_dict:
                evt_info = evts_dict[sk]
                stream_obj = streams[sk]
                # bin境界を取得
                bins = build_relative_time_bins(stream_obj.df_valid["timestamp"], stream_obj.nr_bins)
                b = int(evt_info.get("bin_id", -1))
                if 0 <= b < len(bins):
                    interval = bins[b]
                    t0 = stream_obj.df_valid["timestamp"].min()
                    # 相対秒
                    bin_start_sec = int((interval.left - t0).total_seconds())
                    bin_end_sec = int((interval.right - t0).total_seconds())
                else:
                    bin_start_sec = None
                    bin_end_sec = None
                gid_local = int(evt_info.get("group_id", -1))
                label_local = str(evt_info.get("label", ""))
                top_words_local = stream_obj.group_top_words.get(gid_local, [])[:5]
                matched_details_all.append({
                    "event_id": event_identifier,
                    "stream": base_name,
                    "bin_id": b,
                    "bin_start_sec": bin_start_sec if bin_start_sec is not None else "",
                    "bin_end_sec": bin_end_sec if bin_end_sec is not None else "",
                    "label": label_local,
                    "top_words": " ".join(top_words_local),
                })
            else:
                # このストリームには該当イベントが存在しない
                matched_details_all.append({
                    "event_id": event_identifier,
                    "stream": base_name,
                    "bin_id": "",
                    "bin_start_sec": "",
                    "bin_end_sec": "",
                    "label": "",
                    "top_words": "",
                })
    # 保存
    if matched_results:
        matched_df = pd.DataFrame(matched_results)
        out_csv2 = os.path.join(OUT_DIR, "matched_event_comparison_results.csv")
        matched_df.to_csv(out_csv2, index=False, encoding="utf-8-sig")
        print(f"Saved matched events results: {out_csv2}")
        # presence CSV は保存（従来の 0/1 情報）
        presence_df = pd.DataFrame(matched_presence)
        # presence 側も同じ上位フィルタを適用して、見た目とCSVの整合を取る
        try:
            top_n = int(getattr(args, "top_matched", 5) or 0)
        except Exception:
            top_n = 5
        if top_n and not presence_df.empty and 'group_id' in presence_df.columns and 'bin_id' in presence_df.columns:
            meta_df2 = pd.DataFrame(matched_meta)
            order_keys = (meta_df2.sort_values(["total_comments","participants"], ascending=[False, False])
                                   [["group_id","bin_id"]].apply(tuple, axis=1).tolist()[:top_n])
            keep_idx = set(order_keys)
            presence_df = presence_df[presence_df.apply(lambda r: (r.get("group_id"), r.get("bin_id")) in keep_idx, axis=1)]
        # 保存用CSVは元の形で出力
        pres_csv = os.path.join(OUT_DIR, "matched_event_presence.csv")
        presence_df.to_csv(pres_csv, index=False, encoding="utf-8-sig")
        # 可視化は「ペアワイズ類似度ヒートマップ（1−JS）」を使用
        sim_df = pd.DataFrame(matched_similarity)
        meta_df = pd.DataFrame(matched_meta)
        # 上位フィルタ: コメント総数の多い順に --top-matched 件まで
        try:
            top_n = int(getattr(args, "top_matched", 5) or 0)
        except Exception:
            top_n = 5
        if top_n and not meta_df.empty:
            order_keys = (meta_df.sort_values(["total_comments","participants"], ascending=[False, False])
                                 [["group_id","bin_id"]].apply(tuple, axis=1).tolist()[:top_n])
            keep_idx = set(order_keys)
            # フィルタ適用
            sim_df = sim_df[sim_df.apply(lambda r: (r.get("group_id"), r.get("bin_id")) in keep_idx, axis=1)]
            meta_df = meta_df[meta_df.apply(lambda r: (r.get("group_id"), r.get("bin_id")) in keep_idx, axis=1)]
        # インデックスにラベルを設定
        if "row_label" in sim_df.columns:
            sim_df_for_plot = sim_df.set_index("row_label")
        else:
            sim_df_for_plot = sim_df
        sim_df_for_plot = sim_df_for_plot.drop(columns=["group_id","bin_id","time_label","row_label"], errors="ignore")
        # 列を平均類似度の高い順に並べ替え
        if not sim_df_for_plot.empty:
            col_order = sim_df_for_plot.mean(axis=0).sort_values(ascending=False).index.tolist()
            sim_df_for_plot = sim_df_for_plot[col_order]
        # プロット用CSVとPNGの出力先（ファイル名は互換のため据え置き）
        pres_csv_plot = os.path.join(OUT_DIR, "matched_event_presence_plot.csv")
        pres_png = os.path.join(OUT_DIR, "matched_event_presence.png")
        save_csv_and_png_heatmap(
            sim_df_for_plot,
            pres_csv_plot,
            pres_png,
            title="Pairwise Topic Similarity for Matched Events (1−JS)"
        )
        # 一致イベントのサマリー（見やすいテーブル）も保存
        try:
            summary_png = os.path.join(OUT_DIR, "matched_event_summary.png")
            _save_matched_summary_table(presence_df, matched_df, summary_png, top_k=20)
            print(f"Saved matched events summary: {summary_png}")
        except Exception as e:
            print(f"[WARN] failed to save matched events summary: {e}")
        # ペアワイズ指標をCSV/PNGで保存
        try:
            if pair_rows:
                pair_df = pd.DataFrame(pair_rows)
                pair_dir = os.path.join(OUT_DIR, "matched_event_pairs")
                os.makedirs(pair_dir, exist_ok=True)
                pair_csv = os.path.join(pair_dir, f"gid{gid}_bin{bin_id}_pairs.csv")
                pair_df.to_csv(pair_csv, index=False, encoding="utf-8-sig")
                # 簡易バー図: 各距離の平均
                agg = pair_df[["lex_js","lang_js","emoji_diff","sentiment_dist","style_dist"]].mean()
                plt.figure(figsize=(6,4))
                plt.bar(agg.index, agg.values)
                plt.xticks(rotation=45, ha="right")
                plt.title(f"gid{gid}_bin{bin_id} pairwise metrics (avg)")
                plt.tight_layout()
                plt.savefig(os.path.join(pair_dir, f"gid{gid}_bin{bin_id}_pairs.png"), dpi=200)
                plt.close()
        except Exception as e:
            print(f"[WARN] failed to save pairwise metrics: {e}")

        # JSONにコメント内容を保存
        comments_json_path = os.path.join(OUT_DIR, "matched_event_comments.json")
        try:
            with open(comments_json_path, "w", encoding="utf-8") as f:
                json.dump(matched_comments, f, ensure_ascii=False, indent=2)
            print(f"Saved matched event comments: {comments_json_path}")
        except Exception as e:
            print(f"[WARN] failed to save matched event comments: {e}")
        # 詳細CSVも保存
        if matched_details_all:
            details_df = pd.DataFrame(matched_details_all)
            details_csv = os.path.join(OUT_DIR, "matched_event_details.csv")
            details_df.to_csv(details_csv, index=False, encoding="utf-8-sig")
            print(f"Saved matched event details: {details_csv}")
            # PNGとしてテーブルを保存
            details_png = os.path.join(OUT_DIR, "matched_event_details.png")
            try:
                save_df_as_table_png(details_df, details_png, title="Matched Event Details")
                print(f"Saved matched event details PNG: {details_png}")
            except Exception as e:
                print(f"[WARN] Failed to save matched event details PNG: {e}")
    else:
        print("[INFO] No matched events on exact group & bin across streams.")

    # === 新機能: 類似トピック × 時間が近いイベントをストリーム間で照合し比較 ===
    # `match_events_across_streams` を利用して、Jaccard 類似度と時間差に基づくイベントグループを抽出します。
    print("Matching events across streams by topic similarity and time ...")
    similar_event_map = match_events_across_streams(events_by_stream, args.word_match_th, args.time_match_th)
    similar_results = []
    similar_presence = []
    similar_comments: Dict[int, Dict[str, List[str]]] = {}
    # 類似イベント詳細情報の保存用リスト
    similar_details_all: List[Dict[str, object]] = []
    # Build mapping from event_id to list of (stream_key, event)
    events_by_sim_id: Dict[int, Dict[str, Dict[str, object]]] = defaultdict(dict)
    for stream_key, evts in events_by_stream.items():
        for i, evt in enumerate(evts):
            eid = similar_event_map.get((stream_key, i))
            if eid is None:
                continue
            events_by_sim_id[eid][stream_key] = evt
    for sim_id, evts_dict in events_by_sim_id.items():
        # skip if less than two streams participate
        if len(evts_dict) < 2:
            continue
        # Determine representative label (concatenate top words across streams)
        # Use first stream's label as base
        labels = []
        for evt in evts_dict.values():
            if evt.get("label"):
                labels.append(evt["label"])
        label = labels[0] if labels else f"event_{sim_id}"
        # Collect comments and languages per stream
        comments_by_stream: Dict[str, List[str]] = {}
        langs_by_stream: Dict[str, List[str]] = {}
        presence_row: Dict[str, int] = {}
        for sk in streams.keys():
            if sk in evts_dict:
                comments, langs = extract_event_comments(streams[sk], evts_dict[sk], args.peak_pad)
                comments_by_stream[sk] = comments
                langs_by_stream[sk] = langs
                presence_row[os.path.basename(sk)] = 1
            else:
                comments_by_stream[sk] = []
                langs_by_stream[sk] = []
                presence_row[os.path.basename(sk)] = 0
        # Compute distance matrices
        keys = list(streams.keys())
        n = len(keys)
        dmat = np.zeros((n, n), dtype=float)
        lang_mat = np.zeros((n, n), dtype=float)
        emoji_mat = np.zeros((n, n), dtype=float)
        for i in range(n):
            for j in range(i+1, n):
                d = compute_lexical_distance(comments_by_stream[keys[i]], comments_by_stream[keys[j]])
                dmat[i, j] = d; dmat[j, i] = d
                ld = js_distance_distribution(
                    compute_language_distribution(langs_by_stream[keys[i]]),
                    compute_language_distribution(langs_by_stream[keys[j]])
                )
                lang_mat[i, j] = ld; lang_mat[j, i] = ld
                ediff = abs(
                    compute_emoji_ratio(comments_by_stream[keys[i]]) - compute_emoji_ratio(comments_by_stream[keys[j]])
                )
                emoji_mat[i, j] = ediff; emoji_mat[j, i] = ediff
        # Compute averages
        tril = dmat[np.tril_indices(n, k=-1)]
        avg_lex = float(np.mean(tril)) if tril.size else 0.0
        tril_lang = lang_mat[np.tril_indices(n, k=-1)]
        avg_lang = float(np.mean(tril_lang)) if tril_lang.size else 0.0
        tril_emoji = emoji_mat[np.tril_indices(n, k=-1)]
        avg_emoji = float(np.mean(tril_emoji)) if tril_emoji.size else 0.0
        result = {
            "sim_event_id": sim_id,
            "label": label,
            "avg_js_distance": avg_lex,
            "avg_language_distance": avg_lang,
            "avg_emoji_difference": avg_emoji,
        }
        for i in range(n):
            for j in range(i+1, n):
                name = f"{os.path.basename(keys[i])} vs {os.path.basename(keys[j])}"
                result[f"{name} (lex)"] = float(dmat[i, j])
                result[f"{name} (lang)"] = float(lang_mat[i, j])
                result[f"{name} (emoji)"] = float(emoji_mat[i, j])
        similar_results.append(result)
        similar_presence.append({"sim_event_id": sim_id, "label": label, **presence_row})
        # Save comments
        similar_comments[sim_id] = {os.path.basename(sk): comments_by_stream[sk] for sk in streams.keys()}
        # Generate aggregated wordcloud for this similar event
        aggregated_comments: List[str] = []
        for comms in comments_by_stream.values():
            aggregated_comments.extend(comms)
        all_wc_dir = os.path.join(OUT_DIR, "wordclouds_similar", f"event_{sim_id}")
        os.makedirs(all_wc_dir, exist_ok=True)
        wc_path = os.path.join(all_wc_dir, f"WC_ALL.png")
        try:
            make_wordcloud(aggregated_comments, wc_path)
        except Exception as e:
            print(f"[WARN] wordcloud failed for similar event {sim_id}: {e}")
        # Also per-stream wordclouds
        for sk, comms in comments_by_stream.items():
            wc_stream_path = os.path.join(all_wc_dir, f"WC_{os.path.basename(sk).replace('.csv','')}.png")
            try:
                make_wordcloud(comms, wc_stream_path)
            except Exception as e:
                print(f"[WARN] wordcloud failed for similar event {sim_id}, stream {sk}: {e}")

        # --- 詳細情報を収集: 各配信者ごとのbin範囲やラベルなど ---
        for sk in streams.keys():
            base_name = os.path.basename(sk)
            if sk in evts_dict:
                evt_info = evts_dict[sk]
                stream_obj = streams[sk]
                bins = build_relative_time_bins(stream_obj.df_valid["timestamp"], stream_obj.nr_bins)
                b = int(evt_info.get("bin_id", -1))
                if 0 <= b < len(bins):
                    interval = bins[b]
                    t0 = stream_obj.df_valid["timestamp"].min()
                    bin_start_sec = int((interval.left - t0).total_seconds())
                    bin_end_sec = int((interval.right - t0).total_seconds())
                else:
                    bin_start_sec = None
                    bin_end_sec = None
                gid_local = int(evt_info.get("group_id", -1))
                label_local = str(evt_info.get("label", ""))
                top_words_local = stream_obj.group_top_words.get(gid_local, [])[:5]
                similar_details_all.append({
                    "sim_event_id": sim_id,
                    "stream": base_name,
                    "bin_id": b,
                    "bin_start_sec": bin_start_sec if bin_start_sec is not None else "",
                    "bin_end_sec": bin_end_sec if bin_end_sec is not None else "",
                    "label": label_local,
                    "top_words": " ".join(top_words_local),
                })
            else:
                similar_details_all.append({
                    "sim_event_id": sim_id,
                    "stream": base_name,
                    "bin_id": "",
                    "bin_start_sec": "",
                    "bin_end_sec": "",
                    "label": "",
                    "top_words": "",
                })
    # Save similar event results
    if similar_results:
        similar_df = pd.DataFrame(similar_results)
        csv_path = os.path.join(OUT_DIR, "similar_event_comparison_results.csv")
        similar_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"Saved similar events results: {csv_path}")
        # Save presence and heatmap
        pres_df = pd.DataFrame(similar_presence)
        pres_csv = os.path.join(OUT_DIR, "similar_event_presence.csv")
        pres_df.to_csv(pres_csv, index=False, encoding="utf-8-sig")
        # For heatmap, set index to label
        pres_df_plot = pres_df.set_index("label")
        pres_df_plot = pres_df_plot.drop(columns=["sim_event_id", "label"], errors="ignore")
        pres_csv_plot = os.path.join(OUT_DIR, "similar_event_presence_plot.csv")
        pres_png = os.path.join(OUT_DIR, "similar_event_presence.png")
        save_csv_and_png_heatmap(pres_df_plot, pres_csv_plot, pres_png, title="Similar Events Presence (1=present)")
        # Save comments JSON
        comments_json = os.path.join(OUT_DIR, "similar_event_comments.json")
        with open(comments_json, "w", encoding="utf-8") as f:
            json.dump(similar_comments, f, ensure_ascii=False, indent=2)
        print(f"Saved similar event comments: {comments_json}")
        # 類似イベント詳細CSVを保存
    if similar_details_all:
            sim_details_df = pd.DataFrame(similar_details_all)
            sim_details_csv = os.path.join(OUT_DIR, "similar_event_details.csv")
            sim_details_df.to_csv(sim_details_csv, index=False, encoding="utf-8-sig")
            print(f"Saved similar event details: {sim_details_csv}")
            # PNGとしてテーブルを保存
            sim_details_png = os.path.join(OUT_DIR, "similar_event_details.png")
            try:
                save_df_as_table_png(sim_details_df, sim_details_png, title="Similar Event Details")
                print(f"Saved similar event details PNG: {sim_details_png}")
            except Exception as e:
                print(f"[WARN] Failed to save similar event details PNG: {e}")
    else:
        print("[INFO] No similar events matched across streams under current thresholds.")

    # === Emojiランキング: 各CSVごとに絵文字の出現頻度を集計し、ランキングと棒グラフを出力 ===
    # message_clean では絵文字が除去されてしまうため、元の message 列から絵文字を抽出する。
    try:
        emoji_dir = os.path.join(OUT_DIR, "emoji_rankings")
        os.makedirs(emoji_dir, exist_ok=True)
        rankings_rows: List[Dict[str, object]] = []
        for stream_key, sd in streams.items():
            # stream_key はCSVのファイルパス。元のコメント全体を読み出して絵文字をカウントする
            msgs: List[str] = []
            # まず元ファイルから読み出す
            try:
                full_df = read_csv_any(stream_key)
                if "message" in full_df.columns:
                    msgs = full_df["message"].astype(str).tolist()
            except Exception:
                # 元ファイルが読めない場合は、df_valid の message 列で代用
                try:
                    msgs = sd.df_valid.get("message", pd.Series([], dtype=str)).astype(str).tolist()
                except Exception:
                    msgs = []
            # 絵文字の出現数をカウント
            emoji_counter: Dict[str, int] = defaultdict(int)
            for txt in msgs:
                if not isinstance(txt, str):
                    continue
                for ch in txt:
                    if is_emoji(ch):
                        emoji_counter[ch] += 1
            # 上位10件の絵文字と頻度を取得
            top_emojis = sorted(emoji_counter.items(), key=lambda x: x[1], reverse=True)[:10]
            # 棒グラフあるいはメッセージ付き図を作成
            plt.figure(figsize=(8, 4))
            if top_emojis:
                emojis, freq = zip(*top_emojis)
                plt.bar(range(len(emojis)), freq)
                # Use actual emojis as labels and supply emoji-supporting font if available
                emoji_font_prop = None
                try:
                    if _emoji_font_path:
                        emoji_font_prop = font_manager.FontProperties(fname=_emoji_font_path)
                except Exception:
                    emoji_font_prop = None
                plt.xticks(range(len(emojis)), list(emojis), fontsize=14, rotation=0, fontproperties=emoji_font_prop)
                plt.xlabel("Emoji")
                plt.ylabel("Frequency")
                plt.title(f"Top Emojis in {os.path.basename(stream_key)}")
            else:
                # 1つも絵文字がなかった場合はメッセージを表示
                plt.text(0.5, 0.5, "No emojis found", ha='center', va='center', fontsize=14)
                plt.axis('off')
                plt.title(f"Top Emojis in {os.path.basename(stream_key)}")
            plt.tight_layout()
            chart_fname = f"emoji_ranking_{os.path.basename(stream_key).replace('.csv','')}.png"
            chart_path = os.path.join(emoji_dir, chart_fname)
            plt.savefig(chart_path, dpi=200)
            plt.close()
            # Print saved chart and build ranking row
            print(f"Saved emoji ranking chart: {chart_path}")
            rank_data: Dict[str, object] = {"stream": os.path.basename(stream_key)}
            for idx, (emo, cnt) in enumerate(top_emojis, start=1):
                rank_data[f"emoji_{idx}"] = emo
                rank_data[f"freq_{idx}"] = cnt
            rankings_rows.append(rank_data)
        # After iterating all streams, save rankings CSV
        if rankings_rows:
            emoji_csv = os.path.join(emoji_dir, "emoji_rankings.csv")
            pd.DataFrame(rankings_rows).to_csv(emoji_csv, index=False, encoding="utf-8-sig")
            print(f"Saved emoji rankings CSV: {emoji_csv}")
    except Exception as e:
        print(f"[WARN] Failed to compute emoji rankings: {e}")

    # === Emoji タイムライン: 各配信ごとに時間帯×絵文字のヒートマップを出力 ===
    try:
        topk_emoji = int(getattr(args, "emoji_topk", 10) or 10)
        et_dir = os.path.join(OUT_DIR, "emoji_timelines")
        os.makedirs(et_dir, exist_ok=True)
        for stream_key, sd in streams.items():
            # 元の message と timestamp を読み込み
            try:
                df_full = read_csv_any(stream_key)
            except Exception:
                df_full = sd.df_valid.copy()
            if "timestamp" not in df_full.columns or "message" not in df_full.columns:
                continue
            ts = pd.to_datetime(df_full["timestamp"], errors="coerce", utc=True).dt.tz_localize(None)
            msgs = df_full["message"].astype(str).tolist()
            # 時間bin（5分単位相当: nr_bins で分けたBE RTopicのbinsとは別に、単純化し 20区分）
            # ここでは、ストリーム全体を sd.nr_bins と同じビンに分割して整合
            bins = build_relative_time_bins(ts.dropna(), sd.nr_bins)
            # 各bin×emojiのカウント
            # まず全emojiの総数で上位 topk を選ぶ
            total_emoji_counter: Dict[str, int] = defaultdict(int)
            for txt in msgs:
                for ch in str(txt):
                    if is_emoji(ch):
                        total_emoji_counter[ch] += 1
            top_emojis = [e for e, _ in sorted(total_emoji_counter.items(), key=lambda x: x[1], reverse=True)[:topk_emoji]]
            if not top_emojis:
                continue
            # bin割当とカウント
            # DataFrameにまとめて高速化
            df_tmp = pd.DataFrame({"timestamp": ts, "message": msgs}).dropna(subset=["timestamp"]).reset_index(drop=True)
            # 各行から候補の絵文字のみ抽出
            def _extract_emojis(s: str) -> List[str]:
                return [ch for ch in str(s) if ch in top_emojis and is_emoji(ch)]
            df_tmp["emojis"] = df_tmp["message"].apply(_extract_emojis)
            if df_tmp["emojis"].map(len).sum() == 0:
                continue
            # 各行のbin id を決定
            def _find_bin(t: pd.Timestamp) -> int:
                for i, iv in enumerate(bins):
                    if t >= iv.left and t < iv.right:
                        return i
                centers = np.array([iv.left.value for iv in bins], dtype=np.int64)
                return int(np.argmin(np.abs(centers - int(t.value))))
            df_tmp["bin_id"] = df_tmp["timestamp"].apply(_find_bin)
            # 時間ラベル（HH:MM 中央）を用意
            time_labels: Dict[int, str] = {}
            for i, iv in enumerate(bins):
                center_ts = iv.left + (iv.right - iv.left)/2
                try:
                    time_labels[i] = pd.Timestamp(center_ts).strftime("%H:%M")
                except Exception:
                    time_labels[i] = str(i)
            # 集計: bin×emoji
            rows = []
            for _, r in df_tmp.iterrows():
                if not r["emojis"]:
                    continue
                b = int(r["bin_id"])
                for ch in r["emojis"]:
                    rows.append({"bin_id": b, "emoji": ch, "cnt": 1})
            if not rows:
                continue
            edf = pd.DataFrame(rows)
            pivot = edf.pivot_table(index="bin_id", columns="emoji", values="cnt", aggfunc="sum", fill_value=0)
            pivot = pivot.reindex(range(len(bins)), fill_value=0)
            pivot.index = [time_labels.get(i, str(i)) for i in pivot.index]
            # 出力
            base = os.path.basename(stream_key).replace('.csv','')
            out_csv_t = os.path.join(et_dir, f"emoji_timeline_{base}.csv")
            out_png_t = os.path.join(et_dir, f"emoji_timeline_{base}.png")
            save_emoji_timeline_heatmap(pivot, out_csv_t, out_png_t, title=f"Emoji Timeline: {base}")
    except Exception as e:
        print(f"[WARN] Failed to build emoji timelines: {e}")

def save_df_as_table_png(df: pd.DataFrame, out_png: str, title: str = "") -> None:
    """Save a DataFrame as a table PNG. Adjust figure size based on number of rows and columns."""
    if df is None or df.empty:
        # nothing to save
        return
    # Determine figure size heuristically
    n_rows, n_cols = df.shape
    # base sizes with caps
    width = min(20, 1 + 0.6 * n_cols)
    height = min(20, 1 + 0.3 * n_rows)
    fig, ax = plt.subplots(figsize=(width, height))
    ax.axis('off')
    # build table
    # Convert values to strings to avoid potential formatting issues
    cell_text = [[str(x) for x in row] for row in df.values]
    table = ax.table(cellText=cell_text, colLabels=df.columns, loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 1.5)
    # Optionally set title
    if title:
        plt.title(title)
    plt.tight_layout()
    # Save
    plt.savefig(out_png, dpi=200)
    plt.close(fig)

if __name__ == "__main__":
    main()
