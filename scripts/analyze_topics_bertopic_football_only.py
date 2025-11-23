"""
BERTopic による多言語トピック抽出 (Football-Only版)
研究計画書 5節「BERTopicを用いて文脈ベクトルを取得」に対応

9配信 (Spain 2, Japan 2, UK 4, France 1) のコメントからトピックを抽出し、
国別のトピック分布と時系列パターンを可視化する。
"""

import pandas as pd
import numpy as np
import os
from collections import Counter, defaultdict
import matplotlib.pyplot as plt
import seaborn as sns
from sentence_transformers import SentenceTransformer
from bertopic import BERTopic
from bertopic.representation import MaximalMarginalRelevance
from sklearn.feature_extraction.text import CountVectorizer
from umap import UMAP
from hdbscan import HDBSCAN
import warnings
warnings.filterwarnings('ignore')

# 日本語フォント設定
plt.rcParams['font.sans-serif'] = ['MS Gothic', 'Yu Gothic', 'Meiryo']
plt.rcParams['axes.unicode_minus'] = False

# ==================== データ設定 ====================
FOOTBALL_STREAMS = {
    # El Clasico streams
    '⏱️ MINUTO A MINUTO _ Real Madrid vs Barcelona _ El Clásico_chat_log.csv': {
        'country': 'Spain', 'name': 'Spain_1'
    },
    '⚽️ REAL MADRID vs FC BARCELONA _ #LaLiga 25_26 - Jornada 10 _ \'EL CLÁSICO\' EN DIRECTO_chat_log.csv': {
        'country': 'Spain', 'name': 'Spain_2'
    },
    '【エルクラシコ】レアルマドリード×バルセロナ 0_15キックオフ リアルタイム戦術分析_chat_log.csv': {
        'country': 'Japan', 'name': 'Japan_1'
    },
    '【LIVE分析】レアルマドリードvsバルセロナ　▷ラ・リーガ｜第10節　エルクラシコ_chat_log.csv': {
        'country': 'Japan', 'name': 'Japan_2'
    },
    'Real Madrid vs Barcelona _EL CLASICO_ Laliga 2025 Live Reaction_chat_log.csv': {
        'country': 'UK', 'name': 'UK_1'
    },
    'Real Madrid vs Barcelona _ La Liga LIVE WATCHALONG_chat_log.csv': {
        'country': 'UK', 'name': 'UK_2'
    },
    'REAL MADRID VS BARCELONA _ EL CLASICO LIVE REACTION!_chat_log.csv': {
        'country': 'UK', 'name': 'UK_3'
    },
    'Real Madrid vs Barcelona El Clasico Watchalong LaLiga LIVE _ TFHD_chat_log.csv': {
        'country': 'UK', 'name': 'UK_4'
    },
    '🔴 REAL MADRID - BARCELONE LIVE _ 🚨LE CLASICO POUR LA 1ERE PLACE ! _ 🔥PLACE AU SPECTACLE ! _ LIGA_chat_log.csv': {
        'country': 'France', 'name': 'France'
    }
}

DATA_DIR = 'data/chat'
OUTPUT_DIR = 'output/bertopic_analysis'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ==================== データ読み込み ====================
def load_football_comments():
    """Football-Only 9配信のコメントを読み込む"""
    all_data = []
    
    for stream_file, meta in FOOTBALL_STREAMS.items():
        filepath = os.path.join(DATA_DIR, stream_file)
        if not os.path.exists(filepath):
            print(f"⚠️  Warning: {filepath} not found, skipping...")
            continue
        
        try:
            df = pd.read_csv(filepath, encoding='utf-8')
            
            # テキストカラムを探す
            text_col = None
            for col in ['message', 'text', 'comment', 'body']:
                if col in df.columns:
                    text_col = col
                    break
            
            if text_col is None:
                print(f"⚠️  Warning: No text column found in {stream_file}")
                continue
            
            # タイムスタンプカラムを探す
            time_col = None
            for col in ['timestamp', 'time', 'time_seconds', 'elapsed_time']:
                if col in df.columns:
                    time_col = col
                    break
            
            # データを追加
            df_filtered = df[[text_col]].copy()
            df_filtered['comment'] = df_filtered[text_col].astype(str)
            df_filtered['country'] = meta['country']
            df_filtered['stream'] = meta['name']
            
            if time_col is not None:
                # タイムスタンプをdatetimeに変換してから数値化
                try:
                    df_filtered['timestamp'] = pd.to_datetime(df[time_col], errors='coerce')
                    # 最初のタイムスタンプからの経過秒数に変換
                    first_time = df_filtered['timestamp'].min()
                    df_filtered['timestamp'] = (df_filtered['timestamp'] - first_time).dt.total_seconds()
                except:
                    # 変換失敗時は行番号を使用
                    df_filtered['timestamp'] = np.arange(len(df))
            else:
                df_filtered['timestamp'] = np.arange(len(df))  # 疑似タイムスタンプ
            
            # NaNを除外
            df_filtered = df_filtered[df_filtered['comment'].notna()]
            df_filtered = df_filtered[df_filtered['comment'].astype(str).str.strip() != '']
            
            all_data.append(df_filtered)
            print(f"✅ Loaded {len(df_filtered)} comments from {meta['name']} ({meta['country']})")
            
        except Exception as e:
            print(f"❌ Error loading {stream_file}: {e}")
    
    if not all_data:
        raise ValueError("No data loaded! Check DATA_DIR and file paths.")
    
    combined = pd.concat(all_data, ignore_index=True)
    print(f"\n📊 Total: {len(combined)} comments from {len(combined['stream'].unique())} streams")
    print(f"Countries: {combined['country'].value_counts().to_dict()}")
    
    return combined

# ==================== BERTopic モデル構築 ====================
def build_bertopic_model():
    """多言語対応 BERTopic モデルを構築"""
    print("\n🔧 Building BERTopic model...")
    
    # 多言語埋め込みモデル
    embedding_model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
    
    # CountVectorizer (多言語対応)
    vectorizer_model = CountVectorizer(
        token_pattern=r"(?u)\b\w+\b",
        max_features=3000,
        min_df=3,
        ngram_range=(1, 2)
    )
    
    # UMAP (次元削減)
    umap_model = UMAP(
        n_components=5,
        n_neighbors=15,
        min_dist=0.0,
        metric='cosine',
        random_state=42
    )
    
    # HDBSCAN (クラスタリング)
    hdbscan_model = HDBSCAN(
        min_cluster_size=30,  # 小さいクラスタも検出
        min_samples=10,
        metric='euclidean',
        cluster_selection_method='eom',
        prediction_data=True
    )
    
    # MMR (トピック表現の多様性向上)
    representation_model = MaximalMarginalRelevance(diversity=0.5)
    
    # BERTopic
    topic_model = BERTopic(
        embedding_model=embedding_model,
        vectorizer_model=vectorizer_model,
        umap_model=umap_model,
        hdbscan_model=hdbscan_model,
        representation_model=representation_model,
        top_n_words=10,
        min_topic_size=20,
        nr_topics='auto',  # 自動最適化
        calculate_probabilities=True,
        verbose=True
    )
    
    return topic_model

# ==================== トピック抽出 ====================
def extract_topics(df, topic_model):
    """コメントからトピックを抽出"""
    print("\n🔍 Extracting topics...")
    
    documents = df['comment'].tolist()
    
    # トピックモデル学習
    topics, probs = topic_model.fit_transform(documents)
    
    # 結果を追加
    df['topic'] = topics
    df['topic_prob'] = [p.max() if len(p) > 0 else 0 for p in probs]
    
    # トピック情報取得
    topic_info = topic_model.get_topic_info()
    print(f"\n📊 Detected {len(topic_info) - 1} topics (excluding outliers)")
    print(topic_info.head(10))
    
    return df, topic_model, topic_info

# ==================== 国別トピック分布 ====================
def analyze_country_topics(df, topic_model, topic_info):
    """国別のトピック分布を分析"""
    print("\n📊 Analyzing country-specific topics...")
    
    # Outlier (-1) を除外
    df_valid = df[df['topic'] != -1].copy()
    
    # 国別トピック分布
    country_topic_dist = pd.crosstab(
        df_valid['country'],
        df_valid['topic'],
        normalize='index'
    ) * 100  # パーセンテージ
    
    # 可視化
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # 上位10トピックのみ表示
    top_topics = topic_info[topic_info['Topic'] != -1].head(10)['Topic'].tolist()
    country_topic_dist_top = country_topic_dist[top_topics]
    
    country_topic_dist_top.plot(kind='bar', stacked=False, ax=ax, width=0.8)
    
    ax.set_xlabel('Country', fontsize=14, fontweight='bold')
    ax.set_ylabel('Topic Distribution (%)', fontsize=14, fontweight='bold')
    ax.set_title('Country-Specific Topic Distribution (Top 10 Topics)', 
                 fontsize=16, fontweight='bold', pad=20)
    ax.legend(title='Topic ID', bbox_to_anchor=(1.05, 1), loc='upper left')
    ax.grid(axis='y', alpha=0.3)
    plt.xticks(rotation=0)
    plt.tight_layout()
    
    plt.savefig(os.path.join(OUTPUT_DIR, 'country_topic_distribution.png'), 
                dpi=300, bbox_inches='tight')
    print(f"✅ Saved: country_topic_distribution.png")
    plt.close()
    
    # CSV保存
    country_topic_dist.to_csv(os.path.join(OUTPUT_DIR, 'country_topic_distribution.csv'))
    print(f"✅ Saved: country_topic_distribution.csv")
    
    return country_topic_dist

# ==================== トピック時系列分析 ====================
def analyze_topic_timeline(df, topic_model, topic_info):
    """トピックの時系列パターンを分析"""
    print("\n📈 Analyzing topic timeline...")
    
    # Outlier (-1) を除外
    df_valid = df[df['topic'] != -1].copy()
    
    # タイムスタンプの有効性チェック
    if df_valid['timestamp'].isna().all():
        print("⚠️  Warning: All timestamps are NaN, using row numbers instead")
        df_valid['timestamp'] = np.arange(len(df_valid))
    
    # ユニークな値が少ない場合の対処
    unique_timestamps = df_valid['timestamp'].nunique()
    if unique_timestamps < 10:
        print(f"⚠️  Warning: Only {unique_timestamps} unique timestamps, adjusting bins")
        bins = max(2, unique_timestamps)
    else:
        bins = 10
    
    # 時間を等分
    try:
        df_valid['time_bin'] = pd.cut(df_valid['timestamp'], bins=bins, labels=False, duplicates='drop')
    except Exception as e:
        print(f"⚠️  Warning: Could not create time bins ({e}), using quantile-based bins")
        df_valid['time_bin'] = pd.qcut(df_valid['timestamp'], q=min(10, unique_timestamps), labels=False, duplicates='drop')
    
    # 上位5トピックに絞る
    top_topics = topic_info[topic_info['Topic'] != -1].head(5)['Topic'].tolist()
    df_top = df_valid[df_valid['topic'].isin(top_topics)]
    
    # 時間ビンごとのトピック出現数
    timeline = pd.crosstab(df_top['time_bin'], df_top['topic'])
    
    # 可視化
    fig, ax = plt.subplots(figsize=(14, 6))
    
    for topic_id in top_topics:
        if topic_id in timeline.columns:
            # トピックラベル取得
            topic_words = topic_model.get_topic(topic_id)
            if topic_words:
                label = f"Topic {topic_id}: {', '.join([w[0] for w in topic_words[:3]])}"
            else:
                label = f"Topic {topic_id}"
            
            ax.plot(timeline.index, timeline[topic_id], marker='o', 
                   linewidth=2, label=label)
    
    ax.set_xlabel('Time Bin (Match Progress)', fontsize=14, fontweight='bold')
    ax.set_ylabel('Comment Count', fontsize=14, fontweight='bold')
    ax.set_title('Topic Timeline During Match', fontsize=16, fontweight='bold', pad=20)
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    
    plt.savefig(os.path.join(OUTPUT_DIR, 'topic_timeline.png'), 
                dpi=300, bbox_inches='tight')
    print(f"✅ Saved: topic_timeline.png")
    plt.close()
    
    # CSV保存
    timeline.to_csv(os.path.join(OUTPUT_DIR, 'topic_timeline.csv'))
    print(f"✅ Saved: topic_timeline.csv")
    
    return timeline

# ==================== トピック詳細情報 ====================
def save_topic_details(topic_model, topic_info):
    """トピックの詳細情報を保存"""
    print("\n💾 Saving topic details...")
    
    # トピック単語リスト
    topic_details = []
    
    for topic_id in topic_info[topic_info['Topic'] != -1]['Topic'].tolist():
        topic_words = topic_model.get_topic(topic_id)
        if topic_words:
            words = ', '.join([f"{w[0]}({w[1]:.3f})" for w in topic_words[:10]])
            topic_details.append({
                'Topic_ID': topic_id,
                'Count': topic_info[topic_info['Topic'] == topic_id]['Count'].values[0],
                'Top_Words': words
            })
    
    topic_df = pd.DataFrame(topic_details)
    topic_df.to_csv(os.path.join(OUTPUT_DIR, 'topic_details.csv'), index=False)
    print(f"✅ Saved: topic_details.csv")
    
    return topic_df

# ==================== メイン実行 ====================
def main():
    print("="*80)
    print("🏆 BERTopic Analysis - Football-Only (9 Streams, 4 Countries)")
    print("="*80)
    
    # 1. データ読み込み
    df = load_football_comments()
    
    # 2. BERTopicモデル構築
    topic_model = build_bertopic_model()
    
    # 3. トピック抽出
    df, topic_model, topic_info = extract_topics(df, topic_model)
    
    # 4. 国別トピック分布
    country_topic_dist = analyze_country_topics(df, topic_model, topic_info)
    
    # 5. トピック時系列
    timeline = analyze_topic_timeline(df, topic_model, topic_info)
    
    # 6. トピック詳細保存
    topic_details = save_topic_details(topic_model, topic_info)
    
    # 7. サマリー統計
    print("\n" + "="*80)
    print("📊 ANALYSIS SUMMARY")
    print("="*80)
    print(f"Total comments analyzed: {len(df)}")
    print(f"Valid topics detected: {len(topic_info) - 1}")
    print(f"Outlier comments: {len(df[df['topic'] == -1])}")
    print(f"\nCountry breakdown:")
    print(df['country'].value_counts())
    print(f"\nTop 5 topics:")
    print(topic_info[topic_info['Topic'] != -1].head(5)[['Topic', 'Count', 'Name']])
    
    print("\n" + "="*80)
    print("✅ BERTopic Analysis Complete!")
    print(f"📁 Output saved to: {OUTPUT_DIR}/")
    print("="*80)

if __name__ == '__main__':
    main()
