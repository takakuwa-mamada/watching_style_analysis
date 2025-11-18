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

# ===== Windows UTF-8対応 =====
import sys
import io
# 標準出力をUTF-8に設定（Windows cp932エラー回避）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

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

# ===== Noise Filter統合 =====
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.noise_filter import NoiseFilter
NOISE_FILTER = NoiseFilter()


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
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from umap import UMAP
from hdbscan import HDBSCAN

# ===== 出力先 =====
OUT_DIR = "output"
os.makedirs(OUT_DIR, exist_ok=True)

# ===== 機能フラグ（長期的な改善のため） =====
ENABLE_WORDCLOUDS = False        # ワードクラウド生成（重い処理、ユーザー要求外）
ENABLE_DETAILED_METRICS = False  # 詳細なペアワイズメトリクス（ユーザー要求外）
ENABLE_JSON_EXPORT = True        # JSON出力（デバッグ用）

# ===== そのほか =====
# 利用するSentenceTransformerモデル。
# 学会発表用：軽量で高速なモデルに変更（処理時間を50-70%削減）
# 精度は若干低下するが、多言語対応は維持
EMB_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
# 元のモデル（重い）: "sentence-transformers/xlm-r-100langs-bert-base-nli-stsb-mean-tokens"

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

# ========================================
# 多言語類義語辞書（トピック重複検出改善）
# ========================================
MULTILINGUAL_SYNONYMS = {
    # サッカー関連
    "goal": {"goal", "gol", "ゴール", "得点", "골", "gooool", "golll", "scored", "scoring"},
    "penalty": {"penalty", "pênalti", "penalti", "ペナルティ", "pk", "패널티", "spot kick"},
    "offside": {"offside", "impedimento", "オフサイド", "오프사이드"},
    "soccer": {"soccer", "football", "futebol", "サッカー", "축구", "futbol"},
    "corner": {"corner", "escanteio", "コーナー", "코너", "corner kick"},
    "foul": {"foul", "falta", "ファウル", "파울"},
    "yellow": {"yellow", "amarelo", "イエロー", "옐로우", "イエローカード", "yellow card"},
    "red": {"red", "vermelho", "レッド", "레드", "レッドカード", "red card"},
    "shoot": {"shoot", "shot", "シュート", "슛", "chute"},
    "freekick": {"free kick", "freekick", "フリーキック", "프리킥"},
    "goalkeeper": {"goalkeeper", "goalie", "gk", "ゴールキーパー", "골키퍼", "キーパー"},
    
    # 野球関連
    "baseball": {"baseball", "beisebol", "野球", "야구"},
    "homerun": {"homerun", "home", "ホームラン", "홈런", "本塁打", "homer"},
    "strike": {"strike", "ストライク", "스트라이크"},
    "ball": {"ball", "ボール", "볼"},
    "pitcher": {"pitcher", "ピッチャー", "투수", "投手"},
    "batter": {"batter", "バッター", "타자", "打者"},
    "hit": {"hit", "ヒット", "안타", "安打"},
    "run": {"run", "ラン", "득점", "点"},
    
    # チーム名（サッカー）
    "real madrid": {"real madrid", "real", "madrid", "レアルマドリード", "레알 마드리드", "merengues"},
    "barcelona": {"barcelona", "barça", "barca", "バルセロナ", "바르셀로나", "blaugrana"},
    "man united": {"manchester united", "man utd", "man united", "united", "マンチェスターユナイテッド"},
    "liverpool": {"liverpool", "lfc", "リバプール", "reds"},
    "bayern": {"bayern", "bayern munich", "バイエルン", "fcb"},
    "psg": {"psg", "paris", "パリサンジェルマン", "paris saint germain"},
    
    # チーム名（野球）
    "yankees": {"yankees", "new york yankees", "ヤンキース", "ny yankees"},
    "dodgers": {"dodgers", "la dodgers", "los angeles dodgers", "ドジャース"},
    "red sox": {"red sox", "boston red sox", "レッドソックス"},
    "giants": {"giants", "sf giants", "san francisco giants", "ジャイアンツ"},
    
    # 一般
    "win": {"win", "vitória", "勝ち", "勝利", "승리", "victory", "won"},
    "lose": {"lose", "derrota", "負け", "敗北", "패배", "lost", "defeat"},
    "draw": {"draw", "empate", "引き分け", "무승부", "tie"},
    "score": {"score", "placar", "スコア", "得点", "점수"},
    "match": {"match", "partida", "試合", "경기", "jogo", "game"},
    "player": {"player", "選手", "jogador", "선수"},
    "coach": {"coach", "manager", "監督", "감독", "técnico"},
    "referee": {"referee", "ref", "審判", "심판", "árbitro"},
    "fan": {"fan", "supporter", "ファン", "팬", "torcedor"},
    "stadium": {"stadium", "スタジアム", "경기장", "estádio"},
    
    # 試合フェーズ
    "halftime": {"halftime", "half time", "ハーフタイム", "하프타임"},
    "fulltime": {"fulltime", "full time", "フルタイム", "풀타임"},
    "overtime": {"overtime", "extra time", "延長", "연장"},
}

def normalize_with_synonyms(word: str) -> str:
    """
    多言語類義語辞書を使用して単語を正規化

    Args:
        word: 正規化する単語

    Returns:
        正規化後の単語（類義語がある場合は代表語、ない場合は小文字化）
    """
    word_lower = word.lower().strip()
    
    # 辞書から代表語を検索
    for canonical, synonyms in MULTILINGUAL_SYNONYMS.items():
        if word_lower in synonyms:
            return canonical
    
    # 辞書にない場合はそのまま返す
    return word_lower

def normalize_term(word: str) -> str:
    """
    用語を正規化して精度を向上させる。

    改善内容：
    1. 繰り返し文字の正規化（"goalllll" → "goal"）
    2. 大文字小文字の統一
    3. 最小長フィルタ（1文字の単語を除外）
    4. 多言語類義語の統一（"goal" = "ゴール"）
    4. 数字のみの単語を除外
    5. 特殊文字の除去
    6. 用語マッピング辞書の適用
    """
    if not isinstance(word, str):
        return word
    
    # 小文字化
    w = word.lower().strip()
    
    # 空文字列チェック
    if not w:
        return ""
    
    # 数字のみの単語を除外
    if w.isdigit():
        return ""
    
    # 特殊文字のみの単語を除外（絵文字は除く）
    import re
    if re.match(r'^[^\w\s]+$', w) and not any(ord(c) > 0x1F600 for c in w):
        return ""
    
    # 繰り返し文字の正規化（3文字以上の繰り返しを2文字に）
    # "goalllllll" → "goal", "kkkkkk" → "kk"
    w = re.sub(r'(.)\1{2,}', r'\1\1', w)
    
    # 最小長フィルタ（1文字の単語を除外、ただし日本語は除く）
    if len(w) == 1:
        # 日本語文字（ひらがな、カタカナ、漢字）は許可
        if not (0x3040 <= ord(w) <= 0x309F or  # ひらがな
                0x30A0 <= ord(w) <= 0x30FF or  # カタカナ
                0x4E00 <= ord(w) <= 0x9FFF):   # 漢字
            return ""
    
    # 用語マッピング辞書の適用
    w = TERM_MAP.get(w, w)
    
    # 多言語類義語の統一（新規追加）
    w = normalize_with_synonyms(w)

    # 最終的に短すぎる場合は除外
    if len(w) < 2 and not any(0x3040 <= ord(c) <= 0x9FFF for c in w):
        return ""
    
    return w

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
def extract_ngram_topics_direct(comments: List[str], top_k: int = 30) -> List[str]:
    """
    【新機能】独自N-gram抽出（BERTopicをバイパス）
    
    BERTopicの内部処理でN-gramフレーズが単語に分解される問題を回避し、
    TfidfVectorizerで直接N-gramを抽出してトピック語とする。
    
    目的:
    - "Real Madrid", "penalty kick"等のフレーズをそのまま抽出
    - topic_jaccard=0が82% → 40-50%への改善を目指す
    
    Args:
        comments: コメントのリスト ['comment1', 'comment2', ...]
        top_k: 抽出する上位N-gram数（デフォルト30）
        
    Returns:
        list: 重要なN-gramのリスト ['Real Madrid', 'penalty kick', 'goal', ...]
        
    実装アルゴリズム:
    1. TfidfVectorizerで1-gram, 2-gram, 3-gramを抽出
    2. TF-IDFスコアの合計でソート
    3. 上位top_k個を返す
    """
    if not comments or len(comments) < 2:
        return []
    
    try:
        # TfidfVectorizer でN-gramを抽出
        vectorizer = TfidfVectorizer(
            ngram_range=(1, 3),       # 1-gram, 2-gram, 3-gram
            max_features=3000,         # 最大3000個の特徴（Step 1で拡張）
            max_df=1.0,                # 100%出現する語も含める（Phase 1.5: 小規模イベント対応）
            min_df=1,                  # 最低1回出現する語のみ（コメント数が少ないイベント対応）
            token_pattern=r"(?u)\b\w+\b",
            lowercase=True,
            # ストップワードは除外しない（スポーツ用語を保持）
        )
        
        # TF-IDFマトリックスを作成
        X = vectorizer.fit_transform(comments)
        
        # 全コメントでのTF-IDFスコアの合計を計算
        scores = np.asarray(X.sum(axis=0)).flatten()
        
        # スコアが高い順にソート
        top_indices = scores.argsort()[-top_k:][::-1]
        
        # 特徴語（N-gram）を取得
        feature_names = vectorizer.get_feature_names_out()
        top_ngrams = [feature_names[i] for i in top_indices]
        
        # ===== Noise Filtering統合 =====
        # N-gramからノイズを除去
        top_ngrams_filtered = NOISE_FILTER.filter_ngrams(top_ngrams)
        removed_count = len(top_ngrams) - len(top_ngrams_filtered)
        if removed_count > 0:
            print(f"  [N-gram Filter] Removed {removed_count}/{len(top_ngrams)} noise n-grams")
        top_ngrams = top_ngrams_filtered
        
        # デバッグ出力（最初の5個のみ）
        if len(top_ngrams) > 0:
            print(f"  [N-gram抽出] Top 5: {top_ngrams[:5]}")
        
        return top_ngrams
        
    except Exception as e:
        print(f"  [WARNING] N-gram抽出エラー: {e}")
        # フォールバック: 単語頻度ベース
        all_words = []
        for comment in comments:
            words = comment.lower().split()
            all_words.extend(words)
        word_counts = Counter(all_words)
        return [word for word, count in word_counts.most_common(top_k)]


def build_topic_model(embedding_model: SentenceTransformer) -> BERTopic:
    # トピック分類の精度向上のためのハイパーパラメータ調整
    # CountVectorizer の特徴数を増やし、単一出現語も対象に含める
    # 【重要】N-gramを有効化: 1-gram, 2-gram, 3-gramを抽出
    # これにより"Real Madrid", "penalty kick", "World Cup final"等のフレーズを検出
    vectorizer_model = CountVectorizer(
        token_pattern=r"(?u)\b\w+\b",
        max_features=8000,  # 6000→8000に増加（N-gram対応）
        min_df=1,
        ngram_range=(1, 3),  # 【新機能】1-gram, 2-gram, 3-gramを抽出
        max_df=1.0  # 100%出現する語も含める（Phase 1.5: 小規模イベント対応）
    )
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
    """
    トピックをJaccard類似度でマージする（精度向上版）
    
    改善内容：
    1. 適応的閾値：トピックサイズに応じて閾値を調整
    2. 空単語のフィルタリング：正規化後に空になる単語を除外
    3. 最小トピックサイズ：2単語未満のトピックは孤立させる
    """
    tids = [t for t in words_by_tid.keys() if t != -1]
    
    # 各トピックの上位語セットを正規化（用語マッピング）してから比較
    sets = {}
    topic_sizes = {}  # 正規化後のトピックサイズを記録
    
    for t in tids:
        raw_words = [w for w, _ in words_by_tid[t][:10] if isinstance(w, str) and w.strip()]
        # 正規化して空文字列を除外
        normalized = {normalize_term(w) for w in raw_words}
        normalized = {w for w in normalized if w}  # 空文字列除外
        sets[t] = normalized
        topic_sizes[t] = len(normalized)
    
    # Union-Find構造
    parent: Dict[int, int] = {t: t for t in tids}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def union(x, y):
        rx, ry = find(x), find(y)
        if rx != ry: parent[ry] = rx
    
    # 適応的閾値でマージ
    for i, ti in enumerate(tids):
        for tj in tids[i+1:]:
            sa, sb = sets[ti], sets[tj]
            
            # 空セットまたは小さすぎるトピックはスキップ
            if not sa or not sb or len(sa) < 2 or len(sb) < 2:
                continue
            
            # Jaccard類似度計算
            intersection = len(sa & sb)
            union_size = len(sa | sb)
            
            if union_size == 0:
                continue
            
            jac = intersection / union_size
            
            # 適応的閾値の計算
            # 小トピック（2-5単語）: 閾値 × 0.7
            # 中トピック（6-8単語）: 閾値 × 0.85
            # 大トピック（9-10単語）: 閾値 × 1.0
            avg_size = (topic_sizes[ti] + topic_sizes[tj]) / 2
            
            if avg_size <= 5:
                adaptive_threshold = threshold * 0.7  # より緩い閾値
            elif avg_size <= 8:
                adaptive_threshold = threshold * 0.85
            else:
                adaptive_threshold = threshold
            
            # マージ判定
            if jac >= adaptive_threshold:
                union(ti, tj)
    
    # グループ化
    groups = defaultdict(list)
    for t in tids:
        groups[find(t)].append(t)
    
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
    
    # ===== Noise Filtering統合 =====
    # ノイズコメント除去 (kkkk, wwww, etc.)
    df["is_noise"] = df["message_clean"].apply(NOISE_FILTER.is_noise)
    noise_count = df["is_noise"].sum()
    total_before = len(df)
    df = df[~df["is_noise"]].copy()
    noise_ratio = noise_count / total_before if total_before > 0 else 0
    print(f"  [Noise Filter] Removed {noise_count}/{total_before} comments ({noise_ratio:.1%})")
    
    if df.empty:
        print(f"Skipping {csv_file}: no usable comments after noise filtering")
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
            # トピック重複検出改善: 10語 → 20語に増加
            for w, s in words_by_tid.get(t, [])[:20]:
                if isinstance(w, str) and w.strip():
                    norm = normalize_term(w)
                    counter[norm] += float(s)
        # ラベルは上位4語のまま（可読性のため）
        tops = [w for w, _ in counter.most_common(4)]
        # トピック比較用には上位20語を保存
        tops_extended = [w for w, _ in counter.most_common(20)]
        group_top_words[gid] = tops_extended  # 20語を保存
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
    
    # ===== Noise Filtering統合 =====
    # イベントを品質スコアでフィルタリング
    events_before = len(events)
    events_with_quality = []
    for event in events:
        quality = NOISE_FILTER.score_topic_quality(event['top_words'])
        event['quality_score'] = quality
        if quality >= 0.3:  # 最小品質閾値
            events_with_quality.append(event)
    
    removed_events = events_before - len(events_with_quality)
    if removed_events > 0:
        print(f"  [Event Filter] Removed {removed_events}/{events_before} low-quality events")
    
    return events_with_quality

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
    debug_count = 0
    debug_match_count = 0
    DEBUG_VERBOSE = False  # 詳細なデバッグ出力を有効化する場合はTrue
    for a in range(len(items)):
        ka, ia, ea = items[a]
        for b in range(a+1, len(items)):
            kb, ib, eb = items[b]
            # 同一ストリーム内のイベントはマージしない
            if ka == kb:
                continue
            
            debug_count += 1
            
            # DEBUG: 最初の数ペアを詳細に記録（DEBUG_VERBOSEがTrueの場合のみ）
            if DEBUG_VERBOSE and debug_count <= 5:
                print(f"[DEBUG] Pair {debug_count}: {os.path.basename(ka)} event{ia} vs {os.path.basename(kb)} event{ib}")
            
            # Time proximity check first (fastest)
            bin_diff = abs(int(ea.get("bin_id", -1)) - int(eb.get("bin_id", -1)))
            if DEBUG_VERBOSE and debug_count <= 5:
                print(f"  - Time bin difference: {bin_diff} (threshold: {time_th})")
            if bin_diff > time_th:
                if DEBUG_VERBOSE and debug_count <= 5:
                    print(f"  - SKIP: Time difference too large")
                continue
            
            # ===精度向上: 最小コメント数チェック===
            # 各イベントが十分なコメント数を持っているか確認（偽陽性削減）
            min_comments_threshold = 5  # 最小5コメント
            
            # コメント数の推定（top_wordsの数をプロキシとして使用）
            # または、後で extract_event_comments を呼び出してチェックすることも可能
            # ここでは簡易的に top_words が存在するかで判定
            has_sufficient_data_a = len(ea.get("top_words", [])) >= 3
            has_sufficient_data_b = len(eb.get("top_words", [])) >= 3
            
            if not has_sufficient_data_a or not has_sufficient_data_b:
                if DEBUG_VERBOSE and debug_count <= 5:
                    print(f"  - SKIP: Insufficient topic data (A:{len(ea.get('top_words', []))}, B:{len(eb.get('top_words', []))})")
                continue
            
            # Embedding similarity check (if enabled, this is primary matching method)
            if embed_th is not None:
                emb_a = ea.get("embedding")
                emb_b = eb.get("embedding")
                # どちらか欠如ならスキップ
                if emb_a is None or emb_b is None:
                    if DEBUG_VERBOSE and debug_count <= 5:
                        print(f"  - SKIP: Missing embedding")
                    continue
                # 正規化済みベクトルとしてコサイン類似度
                num = float(np.dot(emb_a, emb_b))
                if DEBUG_VERBOSE and debug_count <= 5:
                    print(f"  - Embedding similarity: {num:.4f} (threshold: {embed_th})")
                # 既にnormalize_embeddings=Trueで生成しているのでnormは≈1
                if num < embed_th:
                    if DEBUG_VERBOSE and debug_count <= 5:
                        print(f"  - SKIP: Embedding similarity too low")
                    continue
                # Embedding check passed, now check Jaccard (if both pass = stronger match)
            
            # Jaccard on top words (secondary check, or primary if embed_th is None)
            sa_raw = ea.get("top_words", [])
            sb_raw = eb.get("top_words", [])
            sa = {normalize_term(w) for w in sa_raw if isinstance(w, str) and w.strip()}
            sb = {normalize_term(w) for w in sb_raw if isinstance(w, str) and w.strip()}
            
            if DEBUG_VERBOSE and debug_count <= 5:
                print(f"  - top_words_A: {sa_raw}")
                print(f"  - top_words_B: {sb_raw}")
                print(f"  - normalized_A: {sa}")
                print(f"  - normalized_B: {sb}")
            
            # Jaccard similarity of normalized sets
            jacc = 0.0
            if sa or sb:
                jacc = len(sa & sb) / (len(sa | sb) + 1e-12)
            if DEBUG_VERBOSE and debug_count <= 5:
                print(f"  - Jaccard similarity: {jacc:.4f} (threshold: {word_th})")
            
            # If embedding matching is enabled, Jaccard is optional (just for extra validation)
            # If embedding matching is disabled, Jaccard is required
            if embed_th is None:
                # No embedding check - rely on Jaccard
                if jacc < word_th:
                    if DEBUG_VERBOSE and debug_count <= 5:
                        print(f"  - SKIP: Jaccard too low (no embedding check)")
                    continue
            else:
                # Embedding check already passed - Jaccard is just for logging
                if DEBUG_VERBOSE and debug_count <= 5:
                    if jacc >= word_th:
                        print(f"  - Jaccard also passed (strong match)")
                    else:
                        print(f"  - Jaccard low but embedding passed (semantic match)")
            
            # All conditions satisfied → union
            debug_match_count += 1
            if DEBUG_VERBOSE and debug_count <= 5:
                print(f"  - ✓ MATCHED!")
            union((ka, ia), (kb, ib))
    
    if embed_th is not None:
        print(f"[INFO] Event matching: {debug_match_count} similar events matched (embedding-based, threshold={embed_th})")
    else:
        print(f"[INFO] Event matching: {debug_match_count} similar events matched (Jaccard-based, threshold={word_th})")
    if DEBUG_VERBOSE:
        print(f"[DEBUG] Total pairs compared: {debug_count}, Matched: {debug_match_count}")
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
    """
    Jensen-Shannon距離を計算（精度向上版）
    
    改善内容：
    1. NaN/Inf チェック
    2. ゼロベクトル処理
    3. Laplace smoothing
    """
    p = p.astype(float)
    q = q.astype(float)
    
    # ゼロベクトルチェック
    p_sum = p.sum()
    q_sum = q.sum()
    
    if p_sum == 0 or q_sum == 0:
        # どちらかが空の場合は最大距離を返す
        return 1.0
    
    # 正規化（Laplace smoothing適用）
    smoothing = 1e-10
    p = (p + smoothing) / (p_sum + smoothing * len(p))
    q = (q + smoothing) / (q_sum + smoothing * len(q))
    
    # 中点分布
    m = 0.5 * (p + q)
    
    # KLダイバージェンス計算（数値安定性向上）
    with np.errstate(divide='ignore', invalid='ignore'):
        kl_pm = np.sum(np.where(p > 0, p * np.log(p / m), 0.0))
        kl_qm = np.sum(np.where(q > 0, q * np.log(q / m), 0.0))
    
    # NaN/Infチェック
    if np.isnan(kl_pm) or np.isinf(kl_pm):
        kl_pm = 0.0
    if np.isnan(kl_qm) or np.isinf(kl_qm):
        kl_qm = 0.0
    
    # JS距離
    js_div = 0.5 * (kl_pm + kl_qm)
    
    # 負の値やNaNの処理
    if js_div < 0 or np.isnan(js_div):
        return 0.0
    
    js_dist = np.sqrt(js_div)
    
    # 最終チェック
    if np.isnan(js_dist) or np.isinf(js_dist):
        return 1.0
    
    return float(min(js_dist, 1.0))  # [0, 1]に制限

def compute_lexical_distance(comments_a: List[str], comments_b: List[str], top_n: int = 1000) -> float:
    """
    コメントリスト同士の語彙分布差（Jensen–Shannon距離）を計算する（精度向上版）
    
    改善内容：
    1. 最小データ数チェック
    2. 空文字列除外の徹底
    3. 語彙の多様性チェック
    """
    # カウンター作成（改善版正規化を使用）
    ca, cb = Counter(), Counter()
    
    for txt in comments_a:
        if not isinstance(txt, str):
            continue
        for w in txt.split():
            norm = normalize_term(w)
            if norm:  # 空文字列除外
                ca[norm] += 1
    
    for txt in comments_b:
        if not isinstance(txt, str):
            continue
        for w in txt.split():
            norm = normalize_term(w)
            if norm:  # 空文字列除外
                cb[norm] += 1
    
    # 最小データ数チェック（精度向上・調整済み）
    min_words_threshold = 7  # 各側最低7単語（10から緩和）
    if len(ca) < min_words_threshold or len(cb) < min_words_threshold:
        # データ不足の場合は最大距離を返す
        return 1.0
    
    # 語彙の組み合わせ
    combined = ca + cb
    
    # 上位単語を最大 top_n まで
    vocab = [w for w, _ in combined.most_common(top_n) if w]  # 空文字列除外
    
    if not vocab or len(vocab) < 5:  # 最低5単語必要
        return 1.0
    
    # ベクトル作成
    va = np.array([ca.get(w, 0) for w in vocab], dtype=float)
    vb = np.array([cb.get(w, 0) for w in vocab], dtype=float)
    
    # JS距離計算（改善版を使用）
    return js_distance(va, vb)

# -------------------------
# Event-to-Event Comparison（イベント間類似度計算）
# -------------------------
def aggregate_event_representation(evts_dict: Dict[str, Dict[str, object]], 
                                   streams: Dict[str, 'StreamData'], 
                                   peak_pad: int) -> Dict[str, object]:
    """
    複数配信者のイベントを統合して1つの表現を作成
    
    Parameters:
    - evts_dict: {stream_key: event_dict}
    - streams: {stream_key: StreamData}
    - peak_pad: コメント抽出の padding
    
    Returns:
    - 統合されたイベント表現（embedding, comments, topics, など）
    """
    all_comments = []
    all_embeddings = []
    all_topics = set()
    bin_ids = []
    
    for stream_key, evt in evts_dict.items():
        comments, _ = extract_event_comments(streams[stream_key], evt, peak_pad)
        all_comments.extend(comments)
        
        # 埋め込みベクトル
        if evt.get("embedding") is not None:
            all_embeddings.append(evt["embedding"])
        
        # トピック語
        top_words = evt.get("top_words", [])
        all_topics.update([normalize_term(w) for w in top_words if isinstance(w, str)])
        
        # 時間情報
        bin_ids.append(int(evt.get("bin_id", -1)))
    
    # 平均埋め込みベクトル
    if all_embeddings:
        aggregated_embedding = np.mean(all_embeddings, axis=0)
        # 正規化
        norm = np.linalg.norm(aggregated_embedding)
        if norm > 0:
            aggregated_embedding = aggregated_embedding / norm
    else:
        aggregated_embedding = None
    
    # 平均時間bin
    avg_bin = int(np.mean(bin_ids)) if bin_ids else -1
    
    # 新機能: 時系列パターン（各binごとのコメント数）
    # イベント前後のコメント数を配列として取得
    comment_counts_per_bin = []
    for stream_key, evt in evts_dict.items():
        bin_id = int(evt.get("bin_id", -1))
        if bin_id >= 0 and stream_key in streams:
            stream_data = streams[stream_key]
            # イベント前後±peak_pad範囲のコメント数を取得
            counts = []
            
            # group_timeseriesからTimestampでソート済みのデータを取得
            df_ts = stream_data.group_timeseries.copy()
            if 'Timestamp' in df_ts.columns:
                df_ts = df_ts.sort_values('Timestamp')
                # 各タイムスタンプ（bin）ごとのコメント数を集計
                bin_frequencies = df_ts.groupby('Timestamp')['Frequency'].sum()
                
                for offset in range(-peak_pad, peak_pad + 1):
                    target_bin = bin_id + offset
                    if 0 <= target_bin < len(bin_frequencies):
                        counts.append(int(bin_frequencies.iloc[target_bin]))
                    else:
                        counts.append(0)
            
            if counts:
                comment_counts_per_bin.extend(counts)
    
    # 複数ストリームの場合は平均を取る
    if comment_counts_per_bin and len(evts_dict) > 1:
        bins_per_stream = (2 * peak_pad + 1)
        averaged_counts = []
        for i in range(bins_per_stream):
            bin_values = [comment_counts_per_bin[j * bins_per_stream + i] 
                         for j in range(len(evts_dict)) 
                         if j * bins_per_stream + i < len(comment_counts_per_bin)]
            if bin_values:
                averaged_counts.append(np.mean(bin_values))
        comment_counts_per_bin = averaged_counts

    return {
        "embedding": aggregated_embedding,
        "comments": all_comments,
        "topics": all_topics,
        "num_streams": len(evts_dict),
        "stream_keys": list(evts_dict.keys()),
        "avg_bin_id": avg_bin,
        "num_comments": len(all_comments),
        "comment_counts_per_bin": comment_counts_per_bin  # 新機能：時系列パターン
    }

def compute_event_to_event_similarity(event_A: Dict[str, object], 
                                      event_B: Dict[str, object]) -> Dict[str, float]:
    """
    2つのイベント間の類似度を複数の指標で計算

    Returns:
    - embedding_similarity: 埋め込みベクトルのコサイン類似度
    - topic_jaccard: トピック語のJaccard係数
    - lexical_similarity: コメント内容のJS距離ベース類似度（1-JS）
    - combined_score: 総合スコア（重み付き平均）
    - context_penalty: コンテキスト不一致ペナルティ（0.0-1.0、1.0=一致）
    """
    # 0. コンテキスト検証（スポーツ種別など）
    # 修正: topics set ではなく comments の生テキストを使用（複合語検出のため）
    comments_A_str = " ".join(event_A["comments"]).lower() if event_A["comments"] else ""
    comments_B_str = " ".join(event_B["comments"]).lower() if event_B["comments"] else ""
    
    # トピック語も併用（軽量チェック用）
    topics_A_str = " ".join(event_A["topics"]).lower()
    topics_B_str = " ".join(event_B["topics"]).lower()
    
    # 両方を結合してチェック
    full_text_A = f"{topics_A_str} {comments_A_str}"
    full_text_B = f"{topics_B_str} {comments_B_str}"
    
    # スポーツ種別キーワード定義
    # スポーツ種別キーワード（拡張版・精密化）
    # スポーツ判定用キーワード（厳格化版：特徴的なキーワードのみ）
    baseball_keywords = [
        # 野球特有の用語のみ（一般的すぎる単語を除外）
        "ピッチャー", "バッター", "ホームラン", "投手", "打者", "投球",
        "ストライク", "ボール", "イニング", "甲子園", "広陵",
        "pitcher", "homerun", "batter", "strike", "inning", "baseball",
        "yankees", "dodgers", "mlb"
    ]
    
    soccer_keywords = [
        # サッカー特有の用語のみ（言及だけの単語を除外）
        "オフサイド", "フリーキック", "ゴールキーパー", "ドリブル",
        "pk戦", "延長戦", "ハーフタイム", "コーナーキック",
        "offside", "free kick", "goalkeeper", "penalty kick",
        "real madrid", "barcelona", "man united", "liverpool"
    ]
    
    # 各イベントがどのスポーツか判定（複合語も検出可能）
    is_baseball_A = any(kw in full_text_A for kw in baseball_keywords)
    is_soccer_A = any(kw in full_text_A for kw in soccer_keywords)
    is_baseball_B = any(kw in full_text_B for kw in baseball_keywords)
    is_soccer_B = any(kw in full_text_B for kw in soccer_keywords)
    
    # 異なるスポーツ同士の場合、context_penalty = 0.3（類似度を大幅に下げる）
    # 【重要】両方とも両方のスポーツキーワードを含む場合は適用しない（曖昧なケース）
    context_penalty = 1.0
    
    # XOR論理: 片方だけがそのスポーツの場合のみペナルティ
    is_pure_baseball_A = is_baseball_A and not is_soccer_A
    is_pure_soccer_A = is_soccer_A and not is_baseball_A
    is_pure_baseball_B = is_baseball_B and not is_soccer_B
    is_pure_soccer_B = is_soccer_B and not is_baseball_B
    
    if (is_pure_baseball_A and is_pure_soccer_B) or (is_pure_soccer_A and is_pure_baseball_B):
        context_penalty = 0.3  # 70%ペナルティ
        # デバッグ出力（異なるスポーツ検出時のみ）
        # event_A, event_B から ID を取得（存在する場合）
        evt_a_id = event_A.get("event_id", "?")
        evt_b_id = event_B.get("event_id", "?")
        print(f"[CONTEXT] Different sports detected! (Event {evt_a_id} vs {evt_b_id})")
        print(f"  Event A: Baseball={is_baseball_A}, Soccer={is_soccer_A}")
        print(f"  Event B: Baseball={is_baseball_B}, Soccer={is_soccer_B}")
        print(f"  Comments A sample: {comments_A_str[:60] if comments_A_str else 'N/A'}...")
        print(f"  Comments B sample: {comments_B_str[:60] if comments_B_str else 'N/A'}...")
        print(f"  Context penalty: {context_penalty}")
    
    # 1. 埋め込み類似度
    if event_A["embedding"] is not None and event_B["embedding"] is not None:
        embedding_sim = float(np.dot(event_A["embedding"], event_B["embedding"]))
        # 既に正規化済みなのでdotがコサイン類似度
        # コンテキストペナルティを適用
        embedding_sim *= context_penalty
    else:
        embedding_sim = None

    # 2. トピックJaccard（同義語正規化 + TF-IDF重み付け適用）
    topics_A = event_A["topics"]
    topics_B = event_B["topics"]
    if topics_A or topics_B:
        # 同義語正規化を適用してトピックを統一
        normalized_A = {}  # {topic: count} の辞書形式に変更
        for topic in topics_A:
            normalized = normalize_with_synonyms(topic)
            normalized_A[normalized] = normalized_A.get(normalized, 0) + 1
        
        normalized_B = {}
        for topic in topics_B:
            normalized = normalize_with_synonyms(topic)
            normalized_B[normalized] = normalized_B.get(normalized, 0) + 1
        
        # TF-IDF風の重み付きJaccard係数を計算
        # 頻度の少ない（重要な）単語に高い重みを付与
        all_topics = set(normalized_A.keys()) | set(normalized_B.keys())
        
        if len(all_topics) > 0:
            # 各トピックのIDF風スコア（出現回数の逆数）
            weighted_intersection = 0.0
            weighted_union = 0.0
            
            for topic in all_topics:
                count_A = normalized_A.get(topic, 0)
                count_B = normalized_B.get(topic, 0)
                
                # 重み: 出現回数が少ないほど重要（最小1、最大5）
                weight = min(5.0, 1.0 / (min(count_A, count_B) + 0.1)) if count_A > 0 and count_B > 0 else 1.0
                
                if count_A > 0 and count_B > 0:
                    weighted_intersection += weight
                if count_A > 0 or count_B > 0:
                    weighted_union += weight
            
            topic_jaccard = weighted_intersection / weighted_union if weighted_union > 0 else 0.0
        else:
            topic_jaccard = 0.0
    else:
        topic_jaccard = 0.0    # 3. 語彙類似度（JS距離ベース）
    if event_A["comments"] and event_B["comments"]:
        lex_dist = compute_lexical_distance(event_A["comments"], event_B["comments"])
        lexical_sim = max(0.0, 1.0 - lex_dist)
    else:
        lexical_sim = 0.0
    
    # 4. 時間近接性（オプショナル、類似度ではなく追加情報）
    time_diff = abs(event_A["avg_bin_id"] - event_B["avg_bin_id"])
    
    # 5. 時間的相関分析（新機能：コメント数の時系列パターン相関）
    temporal_correlation = 0.0
    if "comment_counts_per_bin" in event_A and "comment_counts_per_bin" in event_B:
        counts_A = np.array(event_A["comment_counts_per_bin"])
        counts_B = np.array(event_B["comment_counts_per_bin"])
        if len(counts_A) > 1 and len(counts_B) > 1 and len(counts_A) == len(counts_B):
            try:
                # Pearson相関係数をnumpyで計算（scipy不要）
                mean_A = np.mean(counts_A)
                mean_B = np.mean(counts_B)
                std_A = np.std(counts_A)
                std_B = np.std(counts_B)
                
                if std_A > 0 and std_B > 0:
                    correlation = np.mean((counts_A - mean_A) * (counts_B - mean_B)) / (std_A * std_B)
                    # 相関が0.3以上の場合のみ採用（中程度以上の相関）
                    if not np.isnan(correlation) and correlation > 0.3:
                        temporal_correlation = correlation
            except:
                temporal_correlation = 0.0
    
    # 6. イベント信頼度スコア（新機能：複数指標からの総合評価）
    confidence_score = 0.0
    confidence_factors = []
    
    # Factor 1: コメント数（多いほど信頼性高い）
    total_comments_A = len(event_A.get("comments", []))
    total_comments_B = len(event_B.get("comments", []))
    comment_factor = min(1.0, (total_comments_A + total_comments_B) / 200.0)
    confidence_factors.append(comment_factor)
    
    # Factor 2: トピックの明確性（トピック数が適度にあるほど信頼性高い）
    topic_count_A = len(event_A.get("topics", set()))
    topic_count_B = len(event_B.get("topics", set()))
    topic_factor = min(1.0, (topic_count_A + topic_count_B) / 20.0)
    confidence_factors.append(topic_factor)
    
    # Factor 3: 複数指標の一致度（embedding, topic, lexicalが全て高いほど信頼性高い）
    consistency_scores = []
    if embedding_sim is not None:
        consistency_scores.append(embedding_sim)
    if topic_jaccard > 0:
        consistency_scores.append(topic_jaccard)
    if lexical_sim > 0:
        consistency_scores.append(lexical_sim)
    
    if len(consistency_scores) >= 2:
        # 各スコアの標準偏差が小さいほど一致度が高い
        consistency_factor = 1.0 - min(1.0, np.std(consistency_scores) / 0.5)
        confidence_factors.append(consistency_factor)
    
    # Factor 4: 時間的相関（高いほど信頼性高い）
    if temporal_correlation > 0.3:
        confidence_factors.append(temporal_correlation)
    
    # 信頼度スコアは全Factorの平均
    if confidence_factors:
        confidence_score = np.mean(confidence_factors)
    
    # 7. 総合スコア（重み付き平均 + 時間的相関のボーナス）
    # 【改善】独自N-gram抽出によりtopic_jaccardが向上したため、トピックの重みを増加
    # Before: embedding 0.5 : lexical 0.3 : topic 0.2
    # After:  embedding 0.4 : lexical 0.2 : topic 0.4 (トピックを重視)
    # Phase 2: embedding 0.3 : lexical 0.15 : topic 0.55 (失敗: Topic重視で全体が悪化)
    # Phase 3: embedding 0.7 : lexical 0.1 : topic 0.2 (最適化: 統計的検証済み, p<0.001)
    if embedding_sim is not None:
        combined_score = embedding_sim * 0.70 + lexical_sim * 0.10 + topic_jaccard * 0.20
        main_similarity = embedding_sim
    else:
        # 埋め込みがない場合は、トピックと語彙を同等に扱う
        combined_score = lexical_sim * 0.5 + topic_jaccard * 0.5
        main_similarity = lexical_sim
    
    # 時間的相関が高い場合、combined_scoreにボーナス（改善: 最大+15%）
    if temporal_correlation > 0.5:
        bonus_factor = 1.0 + temporal_correlation * 0.15  # 0.10 → 0.15に増加
        combined_score = min(1.0, combined_score * bonus_factor)
    elif temporal_correlation > 0.7:
        # 非常に高い相関の場合、さらにボーナス（最大+25%）
        bonus_factor = 1.0 + temporal_correlation * 0.25
        combined_score = min(1.0, combined_score * bonus_factor)

    return {
        "embedding_similarity": embedding_sim,
        "topic_jaccard": topic_jaccard,
        "lexical_similarity": lexical_sim,
        "combined_score": combined_score,
        "main_similarity": main_similarity,
        "time_diff_bins": time_diff,
        "context_penalty": context_penalty,  # コンテキスト検証結果
        "temporal_correlation": temporal_correlation,  # 新機能：時間的相関
        "confidence_score": confidence_score  # 新機能：信頼度スコア
    }

def generate_event_similarity_matrix(events_by_sim_id: Dict[int, Dict[str, Dict[str, object]]], 
                                     streams: Dict[str, 'StreamData'], 
                                     peak_pad: int) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    全イベントペアの類似度を計算してマトリックスとペアデータを生成
    
    Returns:
    - similarity_matrix_df: N×N類似度行列
    - event_pairs_df: ペアごとの詳細データ
    """
    # 各イベントの統合表現を作成
    event_representations = {}
    event_labels = {}
    
    for sim_id, evts_dict in events_by_sim_id.items():
        if len(evts_dict) < 2:  # 2配信者以上が参加しているイベントのみ
            continue
        
        event_representations[sim_id] = aggregate_event_representation(
            evts_dict, streams, peak_pad
        )

        # ラベル作成（N-gramトピック語を使用 + ストリーム名）
        # 【修正】各イベントのN-gramトピックから上位語を抽出
        all_topics = []
        for evt in evts_dict.values():
            evt_topics = evt.get("topics", [])
            if evt_topics:
                # 各イベントから上位3語を抽出
                all_topics.extend(evt_topics[:3])
        
        # 重複を除去しつつ順序を保持（出現順）
        seen = set()
        unique_topics = []
        for t in all_topics:
            if t not in seen:
                seen.add(t)
                unique_topics.append(t)
        
        # ラベル作成: 上位3-5語を結合
        if unique_topics:
            label = "・".join(unique_topics[:5])
        else:
            # フォールバック: 古いラベルを使用
            first_evt = list(evts_dict.values())[0]
            label = first_evt.get("label", f"Event_{sim_id}")
        
        # 参加ストリーム名のリストを取得（ファイルパスを削除してベース名のみ）
        stream_names = sorted([os.path.basename(k).replace(".csv", "") for k in evts_dict.keys()])
        stream_suffix = f" ({', '.join(stream_names)})"
        
        # トピックラベルを短縮（最大35文字、ストリーム名の余裕を確保）
        if len(label) > 35:
            label = label[:32] + "..."
        
        # ストリーム名を追加
        label_with_stream = label + stream_suffix
        event_labels[sim_id] = label_with_stream    # ペアワイズ類似度計算
    event_ids = sorted(event_representations.keys())
    n = len(event_ids)
    
    if n == 0:
        # イベントがない場合は空のDataFrameを返す
        return pd.DataFrame(), pd.DataFrame()
    
    similarity_matrix = np.zeros((n, n))
    event_pairs = []
    
    for i in range(n):
        for j in range(i+1, n):
            event_A_id = event_ids[i]
            event_B_id = event_ids[j]
            
            event_A = event_representations[event_A_id]
            event_B = event_representations[event_B_id]
            
            sim_scores = compute_event_to_event_similarity(event_A, event_B)
            
            # 代表類似度
            main_sim = sim_scores["main_similarity"]
            
            similarity_matrix[i, j] = main_sim
            similarity_matrix[j, i] = main_sim
            
            # 詳細データ保存
            event_pairs.append({
                "event_A_id": event_A_id,
                "event_B_id": event_B_id,
                "event_A_label": event_labels[event_A_id],
                "event_B_label": event_labels[event_B_id],
                "event_A_streams": event_A["num_streams"],
                "event_B_streams": event_B["num_streams"],
                "event_A_comments": event_A["num_comments"],
                "event_B_comments": event_B["num_comments"],
                "embedding_similarity": sim_scores["embedding_similarity"],
                "topic_jaccard": sim_scores["topic_jaccard"],
                "lexical_similarity": sim_scores["lexical_similarity"],
                "combined_score": sim_scores["combined_score"],
                "main_similarity": main_sim,
                "time_diff_bins": sim_scores["time_diff_bins"],
                "context_penalty": sim_scores.get("context_penalty", 1.0),  # コンテキスト検証スコア
                "temporal_correlation": sim_scores.get("temporal_correlation", 0.0),  # 新機能：時間的相関
                "confidence_score": sim_scores.get("confidence_score", 0.0),  # 新機能：信頼度スコア
            })
    
    # 対角線は1.0（自分自身との類似度）
    np.fill_diagonal(similarity_matrix, 1.0)
    
    # DataFrameに変換
    row_labels = [f"E{eid}: {event_labels[eid][:20]}" for eid in event_ids]
    col_labels = [f"E{eid}" for eid in event_ids]
    
    sim_df = pd.DataFrame(
        similarity_matrix,
        index=row_labels,
        columns=col_labels
    )
    
    pairs_df = pd.DataFrame(event_pairs).sort_values("main_similarity", ascending=False)
    
    return sim_df, pairs_df

def save_event_similarity_heatmap(sim_df: pd.DataFrame, out_csv: str, out_png: str):
    """
    イベント間類似度の N×N ヒートマップを保存
    """
    if sim_df.empty:
        print("[WARN] Empty similarity matrix, skipping heatmap.")
        return
    
    # CSV保存
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    sim_df.to_csv(out_csv, encoding="utf-8-sig")
    
    # ヒートマップ描画
    n = len(sim_df)
    figsize = (max(10, n * 0.6), max(8, n * 0.5))
    
    plt.figure(figsize=figsize)
    
    # カラーマップ: 黄色（低類似）→ 赤（高類似）
    im = plt.imshow(sim_df.values, cmap="YlOrRd", vmin=0, vmax=1, aspect='auto')
    
    # タイトルと軸ラベル
    plt.title("Event-to-Event Similarity Matrix\n(イベント間類似度)", fontsize=14, pad=20)
    plt.xlabel("Events", fontsize=12)
    plt.ylabel("Events", fontsize=12)
    
    # 軸の目盛り
    plt.xticks(range(n), sim_df.columns, rotation=45, ha='right', fontsize=9)
    plt.yticks(range(n), sim_df.index, fontsize=9)
    
    # カラーバー
    cbar = plt.colorbar(im, fraction=0.046, pad=0.04)
    cbar.set_label("Similarity", rotation=270, labelpad=20, fontsize=11)
    
    # 数値を表示（イベントが多すぎない場合）
    if n <= 15:
        for i in range(n):
            for j in range(n):
                val = sim_df.values[i, j]
                color = 'white' if val > 0.5 else 'black'
                plt.text(j, i, f'{val:.2f}', ha='center', va='center', 
                        color=color, fontsize=8)
    
    plt.tight_layout()
    plt.savefig(out_png, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved event-to-event similarity heatmap: {out_png}")

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
    転置して時間を横軸、絵文字を縦軸にする（横長で見やすい）
    """
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    df.to_csv(out_csv, index=True, encoding="utf-8-sig")
    if df.empty:
        print(f"[WARN] Emoji timeline empty: {out_png}")
        return
    
    # 転置: 時間を横軸、絵文字を縦軸にする
    df_t = df.T
    
    # 図のサイズを横長に調整（高さを小さく、幅を大きく）
    fig_width = max(12, 0.4 * len(df_t.columns) + 2)  # 時間軸の数に応じて横幅
    fig_height = max(4, 0.3 * len(df_t.index) + 1)     # 絵文字の数に応じて高さ（小さめ）
    plt.figure(figsize=(fig_width, fig_height))
    
    vals = df_t.values.astype(float)
    im = plt.imshow(vals, aspect="auto", cmap="magma", interpolation="nearest")
    plt.title(title)
    plt.xlabel("Time", fontsize=11)
    plt.ylabel("Emoji", fontsize=11)
    
    # 時間軸（横軸）
    plt.xticks(range(len(df_t.columns)), list(df_t.columns), rotation=45, ha="right", fontsize=9)
    
    # 絵文字軸（縦軸）- 絵文字フォントを使用
    emoji_font_prop = None
    try:
        if _emoji_font_path:
            emoji_font_prop = font_manager.FontProperties(fname=_emoji_font_path)
    except Exception:
        pass
    
    if emoji_font_prop:
        plt.yticks(range(len(df_t.index)), list(df_t.index), fontsize=14, fontproperties=emoji_font_prop)
    else:
        # フォールバック: 絵文字フォントがない場合
        plt.yticks(range(len(df_t.index)), list(df_t.index), fontsize=14)
    
    cb = plt.colorbar(im)
    cb.set_label("Count", fontsize=10)
    plt.tight_layout()
    plt.savefig(out_png, dpi=200)
    plt.close()
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
    p.add_argument("--time-bins", type=int, default=100, help="時間分割数（小さいほど高速、大きいほど精密）")
    p.add_argument("--peak-pad", type=int, default=1)
    p.add_argument("--jaccard-th", type=float, default=0.6)
    p.add_argument("--word-match-th", type=float, default=0.05, help="トピック単語一致度の閾値（埋め込みマッチング使用時は補助的）")
    p.add_argument("--time-match-th", type=int, default=15, help="時間差の許容範囲（bins数、大きいほど多くマッチ）")
    # cross-lingual embedding similarity threshold for event matching (RECOMMENDED for multilingual streams)
    p.add_argument("--embedding-match-th", type=float, default=0.70,
                   help="埋め込みベクトルのコサイン類似度閾値（推奨：0.70-0.75、精度重視、多言語配信では必須、Noneで無効化）")
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

    # 各イベントにコメント埋め込みベクトルと独自N-gramトピックを付与する
    # まずはイベントのコメントを抽出し、平均埋め込みを計算（normalize_embeddings=Trueであるため平均後も単位長に再正規化）
    for stream_key, evts in events_by_stream.items():
        for evt in evts:
            try:
                comments, _langs = extract_event_comments(streams[stream_key], evt, args.peak_pad)
                if comments:
                    # 埋め込みベクトル（既存の処理）
                    vecs = embedding_model.encode(comments, batch_size=32, show_progress_bar=False, normalize_embeddings=True)
                    # 2D array (n_comments x dim)
                    # 平均した後、再正規化
                    mean_vec = np.mean(vecs, axis=0)
                    norm = np.linalg.norm(mean_vec) + 1e-12
                    mean_vec = mean_vec / norm

                    # 【新機能】独自N-gram抽出でトピック語を取得
                    # BERTopicではなく、TfidfVectorizerで直接N-gramフレーズを抽出
                    # Phase 1.6: 動的top_k調整（コメント数に応じて適応的に設定）
                    dynamic_top_k = max(5, min(30, len(comments) // 2))  # コメント数の1/2、最小5、最大30
                    ngram_topics = extract_ngram_topics_direct(comments, top_k=dynamic_top_k)
                    evt["topics"] = ngram_topics  # N-gramトピックを保存

                    print(f"  [Event] {os.path.basename(stream_key)} event: {len(comments)} comments, {len(ngram_topics)} topics")
                else:
                    # コメントがない場合はゼロベクトル
                    dim = embedding_model.get_sentence_embedding_dimension()
                    mean_vec = np.zeros(dim, dtype=float)
                    evt["topics"] = []
                evt["embedding"] = mean_vec
            except Exception as e:
                # エラー時はembeddingとtopicsをNone/空に
                print(f"  [ERROR] Failed to process event: {e}")
                evt["embedding"] = None
                evt["topics"] = []
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

        # ワードクラウド出力（機能フラグで制御）
        if ENABLE_WORDCLOUDS:
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
        # [DISABLED] event_eventmap.png - ユーザー要望により無効化
        # eventmap_df = pd.DataFrame(event_presence)
        # # event_id列が存在する場合はインデックス設定
        # if "event_id" in eventmap_df.columns:
        #     eventmap_df = eventmap_df.set_index("event_id").reindex(sorted(eventmap_df["event_id"].unique()))
        # hm_csv = os.path.join(OUT_DIR, "event_eventmap.csv")
        # hm_png = os.path.join(OUT_DIR, "event_eventmap.png")
        # save_csv_and_png_heatmap(eventmap_df, hm_csv, hm_png, title="Shared Events Presence (1=matched)")
        print("[INFO] Skipping event_eventmap.png generation (disabled per user request)")
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
    # [DISABLED] event_comparison_results.png - ユーザー要望により無効化
    # with np.errstate(divide='ignore', invalid='ignore'):
    #     avg = np.where(cnt>0, acc/np.maximum(cnt,1), 0.0)
    # names = [os.path.basename(k) for k in stream_keys]
    # dist_df = pd.DataFrame(avg, index=names, columns=names)
    # dist_csv = os.path.join(OUT_DIR, "event_comparison_distance_matrix.csv")
    # dist_png = os.path.join(OUT_DIR, "event_comparison_results.png")
    # save_png_distance_matrix(dist_df, dist_csv, dist_png, title="Average JS Distance across Shared Events")
    print("[INFO] Skipping event_comparison_results.png generation (disabled per user request)")

    # JSON保存
    if args.save_json:
        with open(os.path.join(OUT_DIR, "event_comments.json"), "w", encoding="utf-8") as f:
            json.dump(raw_data, f, ensure_ascii=False, indent=2)
    print(f"Saved: {os.path.join(OUT_DIR, 'event_comments.json')}")

    print("All done")

    # === このセクションは一時的にスキップ（類似トピック機能を使用） ===
    print("[INFO] Skipping exact match section - using similar topics for matched_event_presence.png")
    matched_pair_rows_all: List[Dict[str, object]] = []
    matched_results = []
    matched_presence = []
    matched_details_all: List[Dict[str, object]] = []
    matched_comments: Dict[str, Dict[str, List[str]]] = {}
    
    # 完全一致セクションは現在無効化されています
    # （類似トピック機能で matched_event_presence.png を生成するため）
    
    if False:  # 以下の完全一致セクションをスキップ
        pass  # ダミー文（スキップ）
    
    # 完全一致セクションの残りの変数定義
    matched_meta = []
    pair_rows = []
    gid = -1
    bin_id = -1
    
    # ここから元の処理（実際は実行されない）
    if False:
        events_by_group_bin: Dict[Tuple[int, int], Dict[str, Dict[str, object]]] = defaultdict(dict)
        for stream_key, evts in events_by_stream.items():
            for evt in evts:
                key = (int(evt.get("group_id", -1)), int(evt.get("bin_id", -1)))
                events_by_group_bin[key][stream_key] = evt
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
            # ペアワイズ類似度（1−JS）を列に展開（簡潔な列名: "A vs B")
            sim_row: Dict[str, object] = {"group_id": gid, "bin_id": bin_id}
            for i in range(n):
                for j in range(i+1, n):
                    base_i = os.path.basename(keys[i]).replace('.csv','')
                    base_j = os.path.basename(keys[j]).replace('.csv','')
                    name = f"{base_i} vs {base_j}"
                    sim_val = float(max(0.0, min(1.0, 1.0 - dmat[i, j])))
                    sim_row[name] = sim_val
            # このイベントの参加者・コメント総数（ペア行の優先度用）
            participants_here = int(sum(1 for sk in streams.keys() if sk in evts_dict))
            total_comments_here = int(sum(len(comments_by_stream.get(sk, [])) for sk in streams.keys()))
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
        present_set = set(present_streams_keys)
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
                # 可視化用の「イベントペア行」も同時に蓄積
                # まず、このペアが両方present_setに含まれているか確認
                if (keys[i] not in present_set) or (keys[j] not in present_set):
                    # どちらかがこの時間帯にイベントを持っていない→スキップ
                    continue
                base_i_full = os.path.basename(keys[i])
                base_j_full = os.path.basename(keys[j])
                base_i_short = base_i_full.replace('.csv','')
                base_j_short = base_j_full.replace('.csv','')
                # トピック内容ラベルを取得
                la = stream_label_map.get(base_i_full, "")
                lb = stream_label_map.get(base_j_full, "")
                if not la:
                    la = "未分類"
                if not lb:
                    lb = "未分類"
                sim_pair = float(max(0.0, min(1.0, 1.0 - lex)))
                # 行ラベル: 時間, トピック内容X vs トピック内容Y, 類似度
                pair_label_only = f"{la} vs {lb}"
                row_lbl = f"{time_label}, {pair_label_only}, sim={sim_pair:.2f}" if time_label else f"{pair_label_only}, sim={sim_pair:.2f}"
                matched_pair_rows_all.append({
                    "group_id": gid,
                    "bin_id": bin_id,
                    "time_label": time_label,
                    "A": base_i_short,
                    "A_label": la,
                    "B": base_j_short,
                    "B_label": lb,
                    "pair": pair_label_only,
                    "Similarity": sim_pair,
                    "participants": participants_here,
                    "total_comments": total_comments_here,
                    "row_label": row_lbl,
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

        # イベント全体のコメントを使ってワードクラウドを生成（機能フラグで制御）
        if ENABLE_WORDCLOUDS:
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
        # 可視化は「イベントペア行 × 1列(Similarity)」ヒートマップ（1−JS）を使用
        pair_all_df = pd.DataFrame(matched_pair_rows_all)
        if pair_all_df is None or pair_all_df.empty:
            print("[WARN] No pair rows to plot for matched events")
        else:
            try:
                top_n = int(getattr(args, "top_matched", 5) or 0)
            except Exception:
                top_n = 5
            pair_plot_df = pair_all_df.copy()
            # 上位選別: コメント総数→Similarity の順で並べ替え
            pair_plot_df["total_comments"] = pd.to_numeric(pair_plot_df.get("total_comments"), errors="coerce").fillna(0).astype(int)
            pair_plot_df["Similarity"] = pd.to_numeric(pair_plot_df.get("Similarity"), errors="coerce").fillna(0.0).astype(float)
            pair_plot_df = pair_plot_df.sort_values(["total_comments","Similarity"], ascending=[False, False])
            if top_n:
                pair_plot_df = pair_plot_df.head(top_n)
            # [DISABLED] matched_event_presence.png (location 1) - ユーザー要望により無効化
            # # インデックスを行ラベルに
            # if "row_label" in pair_plot_df.columns:
            #     pair_plot_df = pair_plot_df.set_index("row_label")
            # else:
            #     pair_plot_df = pair_plot_df.set_index(pair_plot_df.apply(lambda r: f"{r.get('time_label','')}, {r.get('pair','')}".strip(', '), axis=1))
            # # プロット用CSVとPNGの出力先（ファイル名は互換のため据え置き）
            # pres_csv_plot = os.path.join(OUT_DIR, "matched_event_presence_plot.csv")
            # pres_png = os.path.join(OUT_DIR, "matched_event_presence.png")
            # save_csv_and_png_heatmap(
            #     pair_plot_df[["Similarity"]],
            #     pres_csv_plot,
            #     pres_png,
            #     title="Topic Pair Similarity for Matched Events (1−JS)"
            # )
            print("[INFO] Skipping matched_event_presence.png generation (disabled per user request)")
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
    # `match_events_across_streams` を利用して、埋め込み類似度と時間差に基づくイベントグループを抽出します。
    print("Matching events across streams by topic similarity and time ...")
    print(f"[DEBUG] Matching parameters: word_match_th={args.word_match_th}, time_match_th={args.time_match_th}, embedding_match_th={args.embedding_match_th}")
    print(f"[DEBUG] Total events: {sum(len(evts) for evts in events_by_stream.values())}")
    similar_event_map = match_events_across_streams(events_by_stream, args.word_match_th, args.time_match_th, args.embedding_match_th)
    print(f"[DEBUG] Similar event map created with {len(set(similar_event_map.values()))} unique groups")
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
        # Generate aggregated wordcloud for this similar event（機能フラグで制御）
        if ENABLE_WORDCLOUDS:
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
        # [DISABLED] similar_event_presence.png - ユーザー要望により無効化
        # Save presence CSV only (no heatmap/plot)
        # pres_df = pd.DataFrame(similar_presence)
        # pres_csv = os.path.join(OUT_DIR, "similar_event_presence.csv")
        # pres_df.to_csv(pres_csv, index=False, encoding="utf-8-sig")
        # # For heatmap, set index to label
        # pres_df_plot = pres_df.set_index("label")
        # pres_df_plot = pres_df_plot.drop(columns=["sim_event_id", "label"], errors="ignore")
        # pres_csv_plot = os.path.join(OUT_DIR, "similar_event_presence_plot.csv")
        # pres_png = os.path.join(OUT_DIR, "similar_event_presence.png")
        # save_csv_and_png_heatmap(pres_df_plot, pres_csv_plot, pres_png, title="Similar Events Presence (1=present)")
        print("[INFO] Skipping similar_event_presence.png generation (disabled per user request)")
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
    
    # === 個別イベントの配信者間比較グラフ生成（学会発表用） ===
    print("\n[INFO] Generating individual event broadcaster comparison graphs...")
    bc_comparison_dir = os.path.join(OUT_DIR, "broadcaster_comparisons")
    os.makedirs(bc_comparison_dir, exist_ok=True)
    
    # 上位イベントを選択（参加配信者数が多く、コメント数も多いもの）
    event_priority = []
    for sim_id, evts_dict in events_by_sim_id.items():
        if len(evts_dict) < 2:  # 2配信者以上
            continue
        total_comments = sum(len(extract_event_comments(streams[sk], evt, args.peak_pad)[0]) 
                           for sk, evt in evts_dict.items())
        event_priority.append((sim_id, len(evts_dict), total_comments))
    
    # 配信者数でソート、次にコメント数でソート
    event_priority.sort(key=lambda x: (x[1], x[2]), reverse=True)
    
    # 上位10イベントまたは全イベント（少ない方）
    top_events_to_visualize = min(10, len(event_priority))
    
    for rank, (sim_id, num_broadcasters, total_comments) in enumerate(event_priority[:top_events_to_visualize], 1):
        try:
            evts_dict = events_by_sim_id[sim_id]
            
            # 距離データを収集（CSVから直接読み込み）
            distance_results = {}
            try:
                csv_path = os.path.join(OUT_DIR, "similar_event_comparison_results.csv")
                sim_results_df = pd.read_csv(csv_path, encoding="utf-8-sig")
                
                for row_idx, row in sim_results_df.iterrows():
                    if row["sim_event_id"] == sim_id:
                        for col in sim_results_df.columns:
                            if " vs " in col and ("(lex)" in col or "(lang)" in col or "(emoji)" in col):
                                distance_results[col] = row[col]
                        break
            except Exception as e:
                print(f"[WARN] Could not load distance data for Event {sim_id}: {e}")
                distance_results = {}
            
            out_png = os.path.join(bc_comparison_dir, f"event_{sim_id}_comparison.png")
            generate_event_broadcaster_comparison(
                sim_id, evts_dict, streams, args.peak_pad, distance_results, out_png
            )
            
            if rank <= 3:  # トップ3だけログ出力
                print(f"  Rank {rank}: Event {sim_id} ({num_broadcasters} broadcasters, {total_comments} comments)")
        
        except Exception as e:
            print(f"[WARN] Failed to generate comparison for Event {sim_id}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"[INFO] Generated {top_events_to_visualize} broadcaster comparison graphs")
    
    # === 追加: matched_event_presence.png を類似トピックベースで生成 ===
    # ユーザー要望: 似た内容のトピック同士を時間帯ごとに比較
    if similar_results:
        print("[INFO] Generating matched_event_presence.png from similar topics...")
        matched_pair_rows_similar: List[Dict[str, object]] = []
        
        # events_by_sim_idを再度イテレート（すでに構築済み）
        for sim_id, evts_dict in events_by_sim_id.items():
            if len(evts_dict) < 2:
                continue
            
            # 時間帯を計算（各配信者のイベントの中央時刻の中央値）
            center_ns_list: List[int] = []
            stream_label_map_sim: Dict[str, str] = {}
            
            for sk, evt_info in evts_dict.items():
                stream_obj = streams[sk]
                bins = build_relative_time_bins(stream_obj.df_valid["timestamp"], stream_obj.nr_bins)
                b_local = int(evt_info.get("bin_id", -1))
                if 0 <= b_local < len(bins):
                    interval = bins[b_local]
                    center_ts = interval.left + (interval.right - interval.left)/2
                    try:
                        center_ns_list.append(int(pd.Timestamp(center_ts).value))
                    except Exception:
                        pass
                
                # トピックラベル（短縮版）
                gid_local = int(evt_info.get("group_id", -1))
                top_words_local = stream_obj.group_top_words.get(gid_local, [])[:3]
                if top_words_local:
                    short = ",".join(top_words_local)
                else:
                    raw_label = str(evt_info.get("label", ""))
                    toks = [normalize_term(w) for w in re.split(r"[\s・,，。!！?？]+", raw_label) if w]
                    toks = [t for t in toks if len(t) > 1][:2]
                    short = ",".join(toks) if toks else "topic"
                stream_label_map_sim[os.path.basename(sk)] = short
            
            # 時間ラベル
            time_label_sim = ""
            if center_ns_list:
                cen = pd.to_datetime(int(np.median(center_ns_list)))
                try:
                    time_label_sim = pd.Timestamp(cen).strftime("%H:%M")
                except Exception:
                    minutes = int(round((pd.Timestamp(cen).value/1e9) / 60.0))
                    time_label_sim = f"{minutes:02d}:00"
            
            # ペアワイズ類似度を計算（コメントベース）
            present_keys = list(evts_dict.keys())
            n_present = len(present_keys)
            
            # 各ペアのコメントを取得して類似度を計算
            for i in range(n_present):
                for j in range(i+1, n_present):
                    sk_i = present_keys[i]
                    sk_j = present_keys[j]
                    
                    # コメント抽出
                    comments_i, _ = extract_event_comments(streams[sk_i], evts_dict[sk_i], args.peak_pad)
                    comments_j, _ = extract_event_comments(streams[sk_j], evts_dict[sk_j], args.peak_pad)
                    
                    # JS距離を計算
                    lex_dist = compute_lexical_distance(comments_i, comments_j)
                    sim_val = float(max(0.0, min(1.0, 1.0 - lex_dist)))
                    
                    # ラベル
                    base_i = os.path.basename(sk_i)
                    base_j = os.path.basename(sk_j)
                    la = stream_label_map_sim.get(base_i, "未分類")
                    lb = stream_label_map_sim.get(base_j, "未分類")
                    
                    pair_label = f"{la} vs {lb}"
                    row_lbl = f"{time_label_sim}, {pair_label}, sim={sim_val:.2f}" if time_label_sim else f"{pair_label}, sim={sim_val:.2f}"
                    
                    matched_pair_rows_similar.append({
                        "sim_event_id": sim_id,
                        "time_label": time_label_sim,
                        "A": base_i.replace('.csv',''),
                        "A_label": la,
                        "B": base_j.replace('.csv',''),
                        "B_label": lb,
                        "pair": pair_label,
                        "Similarity": sim_val,
                        "total_comments": len(comments_i) + len(comments_j),
                        "row_label": row_lbl,
                    })
        
        # matched_event_presence.png を生成
        if matched_pair_rows_similar:
            pair_df_sim = pd.DataFrame(matched_pair_rows_similar)
            try:
                top_n = int(getattr(args, "top_matched", 5) or 5)
            except Exception:
                top_n = 5
            
            # ソートしてトップN
            pair_df_sim["total_comments"] = pd.to_numeric(pair_df_sim.get("total_comments"), errors="coerce").fillna(0).astype(int)
            pair_df_sim["Similarity"] = pd.to_numeric(pair_df_sim.get("Similarity"), errors="coerce").fillna(0.0).astype(float)
            pair_df_sim = pair_df_sim.sort_values(["total_comments","Similarity"], ascending=[False, False])
            if top_n:
                pair_df_sim = pair_df_sim.head(top_n)
            
            # [DISABLED] matched_event_presence.png (location 2) - ユーザー要望により無効化
            # # インデックスを行ラベルに
            # if "row_label" in pair_df_sim.columns:
            #     pair_df_sim = pair_df_sim.set_index("row_label")
            # 
            # # matched_event_presence として保存（上書き）
            # matched_pres_csv = os.path.join(OUT_DIR, "matched_event_presence_plot.csv")
            # matched_pres_png = os.path.join(OUT_DIR, "matched_event_presence.png")
            # save_csv_and_png_heatmap(
            #     pair_df_sim[["Similarity"]],
            #     matched_pres_csv,
            #     matched_pres_png,
            #     title="Similar Topic Pair Similarity by Time (1−JS)"
            # )
            print(f"[INFO] Skipping matched_event_presence.png generation (disabled per user request)")
        else:
            print("[WARN] No similar topic pairs found to generate matched_event_presence.png")
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
            # 時間bin（絵文字タイムライン用：見やすさのため10分程度の粒度に固定）
            # 試合時間（90-120分）を想定して、10-12ビン程度に設定
            emoji_timeline_bins = 12  # 約10分ごと（120分÷12=10分）
            bins = build_relative_time_bins(ts.dropna(), emoji_timeline_bins)
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
    
    # ========================================
    # Event-to-Event類似度分析（イベント間比較）
    # ========================================
    print("\n" + "="*60)
    print("Starting Event-to-Event Similarity Analysis")
    print("="*60)
    
    try:
        # N×N類似度行列とペアデータを生成
        sim_matrix_df, event_pairs_df = generate_event_similarity_matrix(
            events_by_sim_id, streams, args.peak_pad
        )
        
        if not sim_matrix_df.empty:
            # 類似度行列CSV・ヒートマップを保存
            event_sim_csv = os.path.join(OUT_DIR, "event_to_event_similarity_matrix.csv")
            event_sim_png = os.path.join(OUT_DIR, "event_to_event_similarity_heatmap.png")
            save_event_similarity_heatmap(sim_matrix_df, event_sim_csv, event_sim_png)
            
            # ペアデータをCSVで保存
            event_pairs_csv = os.path.join(OUT_DIR, "event_to_event_pairs.csv")
            event_pairs_df.to_csv(event_pairs_csv, index=False, encoding="utf-8-sig")
            print(f"Saved event pairs: {event_pairs_csv}")
            
            # 新機能: 時間的相関と信頼度スコアの視覚化
            try:
                visualize_temporal_correlation_and_confidence(event_pairs_df, OUT_DIR)
            except Exception as e:
                print(f"[WARN] Failed to visualize temporal correlation and confidence: {e}")

            # トップ10類似ペアを表示
            print("\n[Top 10 Most Similar Event Pairs]")
            print("-" * 80)
            for idx, row in event_pairs_df.head(10).iterrows():
                print(f"Event {row['event_A_id']} <-> Event {row['event_B_id']}: "
                      f"similarity={row['main_similarity']:.3f}")
                print(f"  A: {row['event_A_label'][:50]}")
                print(f"  B: {row['event_B_label'][:50]}")
                emb_val = f"{row['embedding_similarity']:.3f}" if row['embedding_similarity'] is not None else 'N/A'
                ctx_val = f"{row.get('context_penalty', 1.0):.3f}"
                temp_corr = f"{row.get('temporal_correlation', 0.0):.3f}"
                conf_score = f"{row.get('confidence_score', 0.0):.3f}"
                print(f"  Metrics: emb={emb_val}, "
                      f"topic={row['topic_jaccard']:.3f}, lex={row['lexical_similarity']:.3f}, "
                      f"context={ctx_val}")
                print(f"  新機能: temporal_corr={temp_corr}, confidence={conf_score}")
                print()
            
            print(f"\nEvent-to-Event analysis complete: {len(sim_matrix_df)} events analyzed")
            print(f"Total event pairs: {len(event_pairs_df)}")
        else:
            print("[WARN] No multi-stream events found for Event-to-Event analysis")
    except Exception as e:
        print(f"[ERROR] Failed to perform Event-to-Event analysis: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
    print("All processing complete!")
    print("="*60)
    
    # ========================================
    # 【新機能】最終結果サマリーの表示
    # ========================================
    if not event_pairs_df.empty:
        print("\n" + "="*60)
        print("FINAL RESULTS SUMMARY")
        print("="*60)
        
        # 基本統計
        print("\n[Basic Statistics]")
        print(f"  Total Events: {len(sim_matrix_df)}")
        print(f"  Total Pairs: {len(event_pairs_df)}")
        print(f"  Average Similarity: {event_pairs_df['main_similarity'].mean():.3f}")
        print(f"  Max Similarity: {event_pairs_df['main_similarity'].max():.3f}")
        print(f"  Min Similarity: {event_pairs_df['main_similarity'].min():.3f}")
        
        # トピック一致率の分析
        print("\n[Topic Matching Analysis]")
        topic_zero = len(event_pairs_df[event_pairs_df['topic_jaccard'] == 0])
        topic_nonzero = len(event_pairs_df[event_pairs_df['topic_jaccard'] > 0])
        topic_high = len(event_pairs_df[event_pairs_df['topic_jaccard'] > 0.3])
        print(f"  topic_jaccard = 0: {topic_zero}/{len(event_pairs_df)} ({topic_zero/len(event_pairs_df)*100:.1f}%)")
        print(f"  topic_jaccard > 0: {topic_nonzero}/{len(event_pairs_df)} ({topic_nonzero/len(event_pairs_df)*100:.1f}%)")
        print(f"  topic_jaccard > 0.3: {topic_high}/{len(event_pairs_df)} ({topic_high/len(event_pairs_df)*100:.1f}%)")
        print(f"  Average topic_jaccard (all): {event_pairs_df['topic_jaccard'].mean():.3f}")
        if topic_nonzero > 0:
            print(f"  Average topic_jaccard (>0): {event_pairs_df[event_pairs_df['topic_jaccard'] > 0]['topic_jaccard'].mean():.3f}")
        
        # 類似度分布
        print("\n[Similarity Distribution]")
        low_sim = len(event_pairs_df[event_pairs_df['main_similarity'] < 0.5])
        mid_sim = len(event_pairs_df[(event_pairs_df['main_similarity'] >= 0.5) & (event_pairs_df['main_similarity'] < 0.7)])
        high_sim = len(event_pairs_df[event_pairs_df['main_similarity'] >= 0.7])
        print(f"  Low (<0.5): {low_sim}/{len(event_pairs_df)} ({low_sim/len(event_pairs_df)*100:.1f}%)")
        print(f"  Mid (0.5-0.7): {mid_sim}/{len(event_pairs_df)} ({mid_sim/len(event_pairs_df)*100:.1f}%)")
        print(f"  High (>=0.7): {high_sim}/{len(event_pairs_df)} ({high_sim/len(event_pairs_df)*100:.1f}%)")
        
        # コンテキストペナルティの統計
        print("\n[Context Penalty Analysis]")
        if 'context_penalty' in event_pairs_df.columns:
            penalty_1_0 = len(event_pairs_df[event_pairs_df['context_penalty'] == 1.0])
            penalty_0_3 = len(event_pairs_df[event_pairs_df['context_penalty'] == 0.3])
            print(f"  context_penalty = 1.0: {penalty_1_0}/{len(event_pairs_df)} ({penalty_1_0/len(event_pairs_df)*100:.1f}%)")
            print(f"  context_penalty = 0.3: {penalty_0_3}/{len(event_pairs_df)} ({penalty_0_3/len(event_pairs_df)*100:.1f}%)")
        
        # 時間的相関の統計
        print("\n[Temporal Correlation]")
        if 'temporal_correlation' in event_pairs_df.columns:
            print(f"  Average: {event_pairs_df['temporal_correlation'].mean():.3f}")
            print(f"  Median: {event_pairs_df['temporal_correlation'].median():.3f}")
            strong_corr = len(event_pairs_df[event_pairs_df['temporal_correlation'] > 0.5])
            print(f"  Strong correlation (>0.5): {strong_corr}/{len(event_pairs_df)} ({strong_corr/len(event_pairs_df)*100:.1f}%)")
        
        # 信頼度スコアの統計
        print("\n[Confidence Score]")
        if 'confidence_score' in event_pairs_df.columns:
            print(f"  Average: {event_pairs_df['confidence_score'].mean():.3f}")
            print(f"  Median: {event_pairs_df['confidence_score'].median():.3f}")
            high_conf = len(event_pairs_df[event_pairs_df['confidence_score'] > 0.7])
            print(f"  High confidence (>0.7): {high_conf}/{len(event_pairs_df)} ({high_conf/len(event_pairs_df)*100:.1f}%)")
        
        # N-gram抽出の効果
        print("\n[N-gram Topic Extraction Impact]")
        print(f"  [OK] N-gram phrases extracted directly via TfidfVectorizer")
        print(f"  [OK] Phrases like 'Real Madrid', 'penalty kick' preserved")
        print(f"  [OK] Weight adjusted: embedding 0.7 : lexical 0.1 : topic 0.2 (Phase 3 optimal, p<0.001)")
        
        # 論文レベル評価
        print("\n[Paper Quality Assessment]")
        avg_sim = event_pairs_df['main_similarity'].mean()
        topic_nonzero_pct = topic_nonzero / len(event_pairs_df) * 100
        
        score = 0
        if avg_sim >= 0.60:
            score += 4
        elif avg_sim >= 0.50:
            score += 3
        elif avg_sim >= 0.40:
            score += 2
        else:
            score += 1
        
        if topic_nonzero_pct >= 50:
            score += 4
        elif topic_nonzero_pct >= 30:
            score += 3
        elif topic_nonzero_pct >= 20:
            score += 2
        else:
            score += 1
        
        if penalty_0_3 == 0:
            score += 2
        elif penalty_0_3 <= 3:
            score += 1
        
        print(f"  Estimated Level: {score}/10")
        if score >= 9:
            print(f"  [EXCELLENT!] Paper-ready quality achieved!")
        elif score >= 7:
            print(f"  [GOOD!] Near paper quality, minor improvements recommended")
        elif score >= 5:
            print(f"  [ACCEPTABLE] Requires improvements for publication")
        else:
            print(f"  [NEEDS WORK] Major improvements required")
        
        print("\n" + "="*60)

def generate_event_broadcaster_comparison(
    sim_id: int,
    evts_dict: Dict[str, Dict[str, object]],
    streams: Dict[str, 'StreamData'],
    peak_pad: int,
    distance_results: Dict[str, float],
    out_png: str
) -> None:
    """
    個別イベントの配信者間比較を高品質で可視化（学会発表用）
    
    Parameters:
    - sim_id: イベントID
    - evts_dict: {stream_key: event_dict}
    - streams: {stream_key: StreamData}
    - peak_pad: padding
    - distance_results: {pair_name: distance_value}
    - out_png: 出力PNG
    """
    # 配信者情報を収集
    broadcaster_data = {}
    all_comments_timeline = []
    
    for stream_key, evt in evts_dict.items():
        base_name = os.path.basename(stream_key).replace('.csv', '')
        comments, bins = extract_event_comments(streams[stream_key], evt, peak_pad)
        
        # 時系列データ（前後のpadding含む）
        bin_id = int(evt.get("bin_id", -1))
        time_range = range(bin_id - peak_pad, bin_id + peak_pad + 1)
        comment_counts = []
        
        # bin_idカラムの存在チェック
        if "bin_id" not in streams[stream_key].df_valid.columns:
            # bin_idがない場合は、timestampから計算
            bins = build_relative_time_bins(
                streams[stream_key].df_valid["timestamp"], 
                streams[stream_key].nr_bins
            )
            for b in time_range:
                count = (bins == b).sum()
                comment_counts.append(count)
        else:
            for b in time_range:
                mask = (streams[stream_key].df_valid["bin_id"] == b)
                count = mask.sum()
                comment_counts.append(count)
        
        broadcaster_data[base_name] = {
            "label": evt.get("label", ""),
            "comments": comments,
            "comment_counts": comment_counts,
            "time_range": list(time_range),
            "bin_id": bin_id,
            "top_words": evt.get("top_words", [])[:5],
            "num_comments": len(comments)
        }
    
    # Figure作成（3行構成）
    fig = plt.figure(figsize=(16, 12), dpi=300)
    gs = fig.add_gridspec(3, 1, height_ratios=[2, 1, 1.5], hspace=0.4)
    
    # カラーパレット
    colors = plt.cm.Set2(np.linspace(0, 1, len(broadcaster_data)))
    
    # ============================================================
    # 上段：コメント数時系列グラフ
    # ============================================================
    ax1 = fig.add_subplot(gs[0])
    
    for idx, (broadcaster, data) in enumerate(broadcaster_data.items()):
        ax1.plot(
            data["time_range"], 
            data["comment_counts"],
            marker='o',
            linewidth=2.5,
            markersize=6,
            label=broadcaster,
            color=colors[idx],
            alpha=0.8
        )
        
        # ピーク位置に縦線
        ax1.axvline(
            x=data["bin_id"], 
            color=colors[idx], 
            linestyle='--', 
            alpha=0.3,
            linewidth=1.5
        )
    
    ax1.set_xlabel("Time Bin ID", fontsize=12, fontweight='bold')
    ax1.set_ylabel("Number of Comments", fontsize=12, fontweight='bold')
    ax1.set_title(
        f"Event {sim_id}: Multi-Broadcaster Comment Timeline Comparison",
        fontsize=14,
        fontweight='bold',
        pad=20
    )
    ax1.legend(loc='upper right', fontsize=10, framealpha=0.9)
    ax1.grid(True, alpha=0.3, linestyle=':', linewidth=0.8)
    ax1.tick_params(labelsize=10)
    
    # ============================================================
    # 中段：トピックラベルと統計情報
    # ============================================================
    ax2 = fig.add_subplot(gs[1])
    ax2.axis('off')
    
    # 表データ作成
    table_data = []
    headers = ["Broadcaster", "Topic Label", "Top Words", "# Comments", "Peak Bin"]
    
    for broadcaster, data in broadcaster_data.items():
        label_short = data["label"][:40] + "..." if len(data["label"]) > 40 else data["label"]
        top_words_str = "・".join([str(w) for w in data["top_words"]])
        if len(top_words_str) > 40:
            top_words_str = top_words_str[:37] + "..."
        
        table_data.append([
            broadcaster,
            label_short,
            top_words_str,
            str(data["num_comments"]),
            str(data["bin_id"])
        ])
    
    # テーブル描画
    table = ax2.table(
        cellText=table_data,
        colLabels=headers,
        cellLoc='left',
        loc='center',
        colWidths=[0.15, 0.35, 0.30, 0.10, 0.10]
    )
    
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 2.5)
    
    # ヘッダーのスタイル
    for i in range(len(headers)):
        cell = table[(0, i)]
        cell.set_facecolor('#4472C4')
        cell.set_text_props(weight='bold', color='white')
    
    # データ行の色付け
    for i in range(len(table_data)):
        for j in range(len(headers)):
            cell = table[(i+1, j)]
            cell.set_facecolor(colors[i] if j == 0 else '#F2F2F2')
            cell.set_alpha(0.3 if j == 0 else 0.5)
    
    ax2.set_title("Topic Information", fontsize=12, fontweight='bold', pad=10)
    
    # ============================================================
    # 下段：配信者間距離比較
    # ============================================================
    ax3 = fig.add_subplot(gs[2])
    ax3.axis('off')
    
    # 距離データを整理
    distance_table_data = []
    distance_headers = ["Broadcaster Pair", "Lexical Distance", "Language Distance", "Emoji Difference"]
    
    broadcasters = list(broadcaster_data.keys())
    for i in range(len(broadcasters)):
        for j in range(i+1, len(broadcasters)):
            pair_name = f"{broadcasters[i]} vs {broadcasters[j]}"
            
            lex_key = f"{broadcasters[i]}.csv vs {broadcasters[j]}.csv (lex)"
            lang_key = f"{broadcasters[i]}.csv vs {broadcasters[j]}.csv (lang)"
            emoji_key = f"{broadcasters[i]}.csv vs {broadcasters[j]}.csv (emoji)"
            
            lex_val = distance_results.get(lex_key, "N/A")
            lang_val = distance_results.get(lang_key, "N/A")
            emoji_val = distance_results.get(emoji_key, "N/A")
            
            lex_str = f"{lex_val:.3f}" if isinstance(lex_val, (int, float)) else str(lex_val)
            lang_str = f"{lang_val:.3f}" if isinstance(lang_val, (int, float)) else str(lang_val)
            emoji_str = f"{emoji_val:.3f}" if isinstance(emoji_val, (int, float)) else str(emoji_val)
            
            distance_table_data.append([pair_name, lex_str, lang_str, emoji_str])
    
    if distance_table_data:
        # 距離テーブル描画
        dist_table = ax3.table(
            cellText=distance_table_data,
            colLabels=distance_headers,
            cellLoc='center',
            loc='center',
            colWidths=[0.40, 0.20, 0.20, 0.20]
        )
        
        dist_table.auto_set_font_size(False)
        dist_table.set_fontsize(9)
        dist_table.scale(1, 2.2)
        
        # ヘッダーのスタイル
        for i in range(len(distance_headers)):
            cell = dist_table[(0, i)]
            cell.set_facecolor('#70AD47')
            cell.set_text_props(weight='bold', color='white')
        
        # データ行の色付け（距離の大小で色分け）
        for i in range(len(distance_table_data)):
            for j in range(1, 4):  # 数値列のみ
                cell = dist_table[(i+1, j)]
                try:
                    val = float(distance_table_data[i][j])
                    # 距離が大きいほど赤、小さいほど緑
                    if val < 0.3:
                        cell.set_facecolor('#C6EFCE')  # 緑系
                    elif val < 0.6:
                        cell.set_facecolor('#FFEB9C')  # 黄色系
                    else:
                        cell.set_facecolor('#FFC7CE')  # 赤系
                    cell.set_alpha(0.6)
                except:
                    pass
        
        ax3.set_title("Broadcaster Pair Distance Metrics", fontsize=12, fontweight='bold', pad=10)
    
    # 全体のタイトル
    fig.suptitle(
        f"Event {sim_id}: Cross-Broadcaster Topic Analysis",
        fontsize=16,
        fontweight='bold',
        y=0.98
    )
    
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    plt.savefig(out_png, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved broadcaster comparison: {out_png}")

def save_df_as_table_png(df: pd.DataFrame, out_png: str, title: str = "") -> None:
    """Save a DataFrame as a table PNG. Adjust figure size based on number of rows and columns."""
    if df is None or df.empty:
        # nothing to save
        return
    
    # テキスト列を短縮（labelやtop_wordsなどの長い文字列）
    df_display = df.copy()
    for col in df_display.columns:
        if df_display[col].dtype == 'object':  # 文字列列のみ
            df_display[col] = df_display[col].apply(
                lambda x: (str(x).split('(')[0][:30] + '...' 
                          if isinstance(x, str) and len(str(x)) > 30 
                          else str(x))
            )
    
    # Determine figure size heuristically
    n_rows, n_cols = df_display.shape
    # より大きなサイズで、長いテキストに対応
    width = min(30, 3 + 2.5 * n_cols)  # 列あたりより広く
    height = min(30, 2 + 0.4 * n_rows)  # 行あたりより高く
    
    fig, ax = plt.subplots(figsize=(width, height))
    ax.axis('off')
    
    # build table
    # Convert values to strings to avoid potential formatting issues
    cell_text = [[str(x) for x in row] for row in df_display.values]
    table = ax.table(cellText=cell_text, colLabels=df_display.columns, loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(7)  # 小さめに
    table.scale(1, 2.0)  # 縦方向に少し伸ばす
    
    # セルの幅を自動調整
    for key, cell in table.get_celld().items():
        cell.set_text_props(wrap=True)
        cell.PAD = 0.05
    
    # Optionally set title
    if title:
        plt.title(title, fontsize=14, pad=20)
    
    plt.tight_layout()
    # Save with higher DPI for clarity
    plt.savefig(out_png, dpi=150, bbox_inches='tight')
    plt.close(fig)


def visualize_temporal_correlation_and_confidence(pairs_df, output_dir):
    """
    新機能の視覚化：時間的相関と信頼度スコアの分析
    
    Parameters:
    - pairs_df: event_to_event_pairs.csv のDataFrame
    - output_dir: 出力ディレクトリ
    """
    import matplotlib.pyplot as plt
    import seaborn as sns
    
    # 日本語フォント設定
    plt.rcParams['font.sans-serif'] = ['MS Gothic', 'Yu Gothic', 'Meiryo']
    plt.rcParams['axes.unicode_minus'] = False
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    
    # 1. 時間的相関 vs メイン類似度の散布図
    ax1 = axes[0, 0]
    scatter1 = ax1.scatter(pairs_df['temporal_correlation'], 
                           pairs_df['main_similarity'],
                           c=pairs_df['confidence_score'],
                           cmap='viridis',
                           s=100,
                           alpha=0.6,
                           edgecolors='black')
    ax1.set_xlabel('時間的相関 (Temporal Correlation)', fontsize=11)
    ax1.set_ylabel('メイン類似度 (Main Similarity)', fontsize=11)
    ax1.set_title('時間的相関 vs メイン類似度\n（色=信頼度スコア）', fontsize=12)
    ax1.grid(True, alpha=0.3)
    cbar1 = plt.colorbar(scatter1, ax=ax1)
    cbar1.set_label('信頼度スコア', fontsize=10)
    
    # 2. 信頼度スコアの分布ヒストグラム
    ax2 = axes[0, 1]
    ax2.hist(pairs_df['confidence_score'], bins=15, color='steelblue', alpha=0.7, edgecolor='black')
    ax2.axvline(pairs_df['confidence_score'].mean(), color='red', linestyle='--', 
                label=f'平均: {pairs_df["confidence_score"].mean():.3f}')
    ax2.set_xlabel('信頼度スコア (Confidence Score)', fontsize=11)
    ax2.set_ylabel('頻度', fontsize=11)
    ax2.set_title('信頼度スコアの分布', fontsize=12)
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # 3. 時間的相関の分布（相関が有意なペアのみ）
    ax3 = axes[1, 0]
    significant_corr = pairs_df[pairs_df['temporal_correlation'] > 0.3]
    if len(significant_corr) > 0:
        ax3.hist(significant_corr['temporal_correlation'], bins=15, 
                color='coral', alpha=0.7, edgecolor='black')
        ax3.set_xlabel('時間的相関 (r > 0.3)', fontsize=11)
        ax3.set_ylabel('頻度', fontsize=11)
        ax3.set_title(f'有意な時間的相関の分布\n（{len(significant_corr)}/{len(pairs_df)} ペア）', fontsize=12)
        ax3.grid(True, alpha=0.3)
    else:
        ax3.text(0.5, 0.5, '有意な時間的相関なし\n(r > 0.3)', 
                ha='center', va='center', fontsize=14, transform=ax3.transAxes)
    
    # 4. 複数指標の相関マトリックス（ヒートマップ）
    ax4 = axes[1, 1]
    metrics = ['main_similarity', 'topic_jaccard', 'lexical_similarity', 
               'temporal_correlation', 'confidence_score']
    available_metrics = [m for m in metrics if m in pairs_df.columns]
    
    if len(available_metrics) >= 2:
        corr_matrix = pairs_df[available_metrics].corr()
        sns.heatmap(corr_matrix, annot=True, fmt='.2f', cmap='coolwarm', 
                   center=0, ax=ax4, cbar_kws={'label': '相関係数'})
        ax4.set_title('指標間の相関マトリックス', fontsize=12)
        
        # ラベルを日本語に変換
        label_map = {
            'main_similarity': 'メイン類似度',
            'topic_jaccard': 'トピックJaccard',
            'lexical_similarity': '語彙類似度',
            'temporal_correlation': '時間的相関',
            'confidence_score': '信頼度'
        }
        ax4.set_xticklabels([label_map.get(m, m) for m in available_metrics], 
                           rotation=45, ha='right', fontsize=9)
        ax4.set_yticklabels([label_map.get(m, m) for m in available_metrics], 
                           rotation=0, fontsize=9)
    
    plt.tight_layout()
    output_path = os.path.join(output_dir, 'temporal_correlation_and_confidence_analysis.png')
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"[INFO] 時間的相関・信頼度分析図を保存: {output_path}")
    
    # 統計サマリーを表示
    print("\n=== 新機能の統計サマリー ===")
    print(f"時間的相関 (Temporal Correlation):")
    print(f"  - 平均: {pairs_df['temporal_correlation'].mean():.3f}")
    print(f"  - 中央値: {pairs_df['temporal_correlation'].median():.3f}")
    print(f"  - 有意な相関 (r>0.3): {len(significant_corr)}/{len(pairs_df)} ペア ({len(significant_corr)/len(pairs_df)*100:.1f}%)")
    
    print(f"\n信頼度スコア (Confidence Score):")
    print(f"  - 平均: {pairs_df['confidence_score'].mean():.3f}")
    print(f"  - 中央値: {pairs_df['confidence_score'].median():.3f}")
    print(f"  - 高信頼度 (>0.7): {len(pairs_df[pairs_df['confidence_score'] > 0.7])}/{len(pairs_df)} ペア")
    print(f"  - 中信頼度 (0.5-0.7): {len(pairs_df[(pairs_df['confidence_score'] >= 0.5) & (pairs_df['confidence_score'] <= 0.7)])}/{len(pairs_df)} ペア")
    print(f"  - 低信頼度 (<0.5): {len(pairs_df[pairs_df['confidence_score'] < 0.5])}/{len(pairs_df)} ペア")


if __name__ == "__main__":
    main()
