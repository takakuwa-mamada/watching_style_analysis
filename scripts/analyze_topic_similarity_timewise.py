"""
時間帯別トピック類似度分析 - El Clasico 10配信
Time-wise Topic Similarity Analysis

目的:
1. 同じ試合の同じ時間帯で、各配信のコメントから抽出されるトピックを比較
2. 配信間のトピック類似度をコサイン類似度で計算
3. ヒートマップで可視化して文化的差異を定量化

手法:
- BERTopicで各配信・各時間帯のトピック抽出
- トピック埋め込みベクトルのコサイン類似度計算
- 階層的クラスタリングでグルーピング
"""

import pandas as pd
import numpy as np
import os
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics.pairwise import cosine_similarity
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import squareform
from sentence_transformers import SentenceTransformer
from bertopic import BERTopic
from bertopic.representation import MaximalMarginalRelevance
from sklearn.feature_extraction.text import CountVectorizer
from umap import UMAP
from hdbscan import HDBSCAN
import warnings
warnings.filterwarnings('ignore')

# UTF-8エンコーディング設定（文字化け防止）
import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 日本語フォント設定
import matplotlib
matplotlib.rcParams['font.family'] = 'sans-serif'
matplotlib.rcParams['font.sans-serif'] = ['Yu Gothic', 'Meiryo', 'MS Gothic', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Yu Gothic', 'Meiryo', 'MS Gothic', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# データ設定
FOOTBALL_STREAMS = {
    # El Clasico streams (10配信)
    '⏱️ MINUTO A MINUTO _ Real Madrid vs Barcelona _ El Clásico_chat_log.csv': {
        'country': 'Spain', 'name': 'Spain_1'
    },
    '⚽️ REAL MADRID vs FC BARCELONA _ #LaLiga 25_26 - Jornada 10 _ \'EL CLÁSICO\' EN DIRECTO_chat_log.csv': {
        'country': 'Spain', 'name': 'Spain_2'
    },
    'REAL MADRID VS FC BARCELONA EN DIRECTO _ EL CLÁSICO _ LALIGA _ Tiempo de Juego COPE _ EN VIVO_chat_log.csv': {
        'country': 'Spain', 'name': 'Spain_3'
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

DATA_DIR = 'data/football/レアルマドリードvsバルセロナ'
OUTPUT_DIR = 'output/topic_similarity_timewise'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# パラメータ設定
TIME_BINS = 10  # 試合を10分割
MIN_COMMENTS_PER_BIN = 50  # 各時間帯の最小コメント数

def load_stream_data():
    """全配信データを読み込み、時間帯で分割"""
    print("\n" + "="*80)
    print("📂 Loading El Clasico streams with timestamps...")
    print("="*80)
    
    stream_data = {}
    
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
                print(f"⚠️  Warning: No text column in {stream_file}")
                continue
            
            # タイムスタンプカラムを探す
            time_col = None
            for col in ['timestamp', 'time', 'time_seconds', 'elapsed_time']:
                if col in df.columns:
                    time_col = col
                    break
            
            # データを整形
            df_stream = pd.DataFrame()
            df_stream['comment'] = df[text_col].astype(str)
            df_stream['stream'] = meta['name']
            df_stream['country'] = meta['country']
            
            if time_col is not None:
                try:
                    df_stream['timestamp'] = pd.to_datetime(df[time_col], errors='coerce')
                    first_time = df_stream['timestamp'].min()
                    df_stream['time_seconds'] = (df_stream['timestamp'] - first_time).dt.total_seconds()
                except:
                    df_stream['time_seconds'] = np.arange(len(df))
            else:
                df_stream['time_seconds'] = np.arange(len(df))
            
            # NaNを除外
            df_stream = df_stream[df_stream['comment'].notna()]
            df_stream = df_stream[df_stream['comment'].str.strip() != '']
            
            # 時間帯で分割（パーセンタイルベース）
            df_stream['time_bin'] = pd.qcut(df_stream['time_seconds'], 
                                             q=TIME_BINS, 
                                             labels=False, 
                                             duplicates='drop')
            
            stream_data[meta['name']] = df_stream
            
            print(f"✅ {meta['name']} ({meta['country']}): {len(df_stream):,} comments, "
                  f"{df_stream['time_bin'].nunique()} time bins")
            
        except Exception as e:
            print(f"❌ Error loading {stream_file}: {e}")
    
    return stream_data

def extract_topics_per_stream_time(stream_data):
    """各配信・各時間帯でトピックを抽出"""
    print("\n" + "="*80)
    print("🔍 Extracting topics for each stream and time bin...")
    print("="*80)
    
    # 埋め込みモデル（共通）
    embedding_model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
    
    topic_data = []
    
    for stream_name, df_stream in stream_data.items():
        print(f"\n📊 Processing {stream_name}...")
        
        for time_bin in sorted(df_stream['time_bin'].dropna().unique()):
            df_bin = df_stream[df_stream['time_bin'] == time_bin]
            
            if len(df_bin) < MIN_COMMENTS_PER_BIN:
                print(f"  ⚠️  Time bin {int(time_bin)} skipped (only {len(df_bin)} comments)")
                continue
            
            comments = df_bin['comment'].tolist()
            
            # トピックキーワード抽出（簡易版：頻出単語Top 10）
            from collections import Counter
            import re
            
            # 単語抽出（英数字、日本語、スペイン語など）
            words = []
            for comment in comments:
                # 単語分割（簡易版）
                tokens = re.findall(r'\w+', comment.lower())
                words.extend([w for w in tokens if len(w) > 2])
            
            # 頻出単語Top 10
            word_freq = Counter(words)
            top_words = [word for word, count in word_freq.most_common(10)]
            
            # 埋め込みベクトル計算（トップ単語の平均）
            if top_words:
                embeddings = embedding_model.encode(top_words)
                topic_embedding = np.mean(embeddings, axis=0)
            else:
                topic_embedding = np.zeros(384)  # モデルの次元数
            
            topic_data.append({
                'stream': stream_name,
                'country': df_stream['country'].iloc[0],
                'time_bin': int(time_bin),
                'num_comments': len(df_bin),
                'top_words': ', '.join(top_words[:5]),
                'embedding': topic_embedding
            })
            
            print(f"  ✅ Time bin {int(time_bin)}: {len(df_bin)} comments, "
                  f"top words: {', '.join(top_words[:3])}")
    
    return pd.DataFrame(topic_data)

def calculate_similarity_matrix(topic_df):
    """時間帯ごとに配信間のトピック類似度を計算"""
    print("\n" + "="*80)
    print("📐 Calculating topic similarity between streams...")
    print("="*80)
    
    similarity_matrices = {}
    
    for time_bin in sorted(topic_df['time_bin'].unique()):
        df_bin = topic_df[topic_df['time_bin'] == time_bin]
        
        if len(df_bin) < 2:
            continue
        
        # 埋め込みベクトルを行列に変換
        streams = df_bin['stream'].tolist()
        embeddings = np.vstack(df_bin['embedding'].values)
        
        # コサイン類似度計算
        similarity = cosine_similarity(embeddings)
        
        similarity_matrices[time_bin] = {
            'streams': streams,
            'similarity': similarity,
            'countries': df_bin['country'].tolist(),
            'top_words': df_bin['top_words'].tolist()
        }
        
        print(f"✅ Time bin {time_bin}: {len(streams)} streams, "
              f"avg similarity: {similarity[np.triu_indices_from(similarity, k=1)].mean():.3f}")
    
    return similarity_matrices

def visualize_similarity_heatmaps(similarity_matrices):
    """時間帯ごとのヒートマップを作成"""
    print("\n" + "="*80)
    print("📊 Creating similarity heatmaps...")
    print("="*80)
    
    n_bins = len(similarity_matrices)
    n_cols = 3
    n_rows = (n_bins + n_cols - 1) // n_cols
    
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(20, 6*n_rows))
    axes = axes.flatten() if n_bins > 1 else [axes]
    
    for idx, (time_bin, data) in enumerate(sorted(similarity_matrices.items())):
        streams = data['streams']
        similarity = data['similarity']
        countries = data['countries']
        
        # ストリーム名を短縮（国名_番号）
        stream_labels = [f"{country}_{stream.split('_')[-1]}" 
                        for stream, country in zip(streams, countries)]
        
        ax = axes[idx]
        
        # ヒートマップ
        im = ax.imshow(similarity, cmap='YlOrRd', vmin=0, vmax=1)
        
        # 軸設定
        ax.set_xticks(np.arange(len(streams)))
        ax.set_yticks(np.arange(len(streams)))
        ax.set_xticklabels(stream_labels, rotation=45, ha='right')
        ax.set_yticklabels(stream_labels)
        
        # 値を表示
        for i in range(len(streams)):
            for j in range(len(streams)):
                text = ax.text(j, i, f'{similarity[i, j]:.2f}',
                             ha="center", va="center", color="black", fontsize=8)
        
        ax.set_title(f'Time Bin {time_bin} ({int(time_bin*10)}%-{int((time_bin+1)*10)}%)',
                    fontweight='bold', fontsize=12)
        
        # カラーバー
        plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    
    # 余ったサブプロットを非表示
    for idx in range(len(similarity_matrices), len(axes)):
        axes[idx].set_visible(False)
    
    plt.tight_layout()
    output_file = os.path.join(OUTPUT_DIR, 'topic_similarity_heatmaps_timewise.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✅ Saved: {output_file}")
    plt.close()

def visualize_average_similarity_heatmap(similarity_matrices):
    """全時間帯の平均類似度ヒートマップ"""
    print("\n" + "="*80)
    print("📊 Creating average similarity heatmap...")
    print("="*80)
    
    # 全配信名を取得
    all_streams = set()
    for data in similarity_matrices.values():
        all_streams.update(data['streams'])
    all_streams = sorted(list(all_streams))
    
    # 配信名から国名を取得
    stream_to_country = {}
    for data in similarity_matrices.values():
        for stream, country in zip(data['streams'], data['countries']):
            stream_to_country[stream] = country
    
    # 平均類似度行列を初期化
    n_streams = len(all_streams)
    avg_similarity = np.zeros((n_streams, n_streams))
    count_matrix = np.zeros((n_streams, n_streams))
    
    # 各時間帯の類似度を累積
    for data in similarity_matrices.values():
        streams = data['streams']
        similarity = data['similarity']
        
        for i, stream_i in enumerate(streams):
            for j, stream_j in enumerate(streams):
                idx_i = all_streams.index(stream_i)
                idx_j = all_streams.index(stream_j)
                avg_similarity[idx_i, idx_j] += similarity[i, j]
                count_matrix[idx_i, idx_j] += 1
    
    # 平均を計算
    avg_similarity = np.divide(avg_similarity, count_matrix, 
                               where=count_matrix!=0, 
                               out=np.zeros_like(avg_similarity))
    
    # 可視化
    fig, ax = plt.subplots(figsize=(14, 12))
    
    # ストリーム名を短縮
    stream_labels = [f"{stream_to_country.get(s, 'Unknown')}_{s.split('_')[-1]}" 
                    for s in all_streams]
    
    # ヒートマップ
    im = ax.imshow(avg_similarity, cmap='YlOrRd', vmin=0, vmax=1)
    
    # 軸設定
    ax.set_xticks(np.arange(n_streams))
    ax.set_yticks(np.arange(n_streams))
    ax.set_xticklabels(stream_labels, rotation=45, ha='right', fontsize=10)
    ax.set_yticklabels(stream_labels, fontsize=10)
    
    # 値を表示
    for i in range(n_streams):
        for j in range(n_streams):
            if count_matrix[i, j] > 0:
                text = ax.text(j, i, f'{avg_similarity[i, j]:.2f}',
                             ha="center", va="center", 
                             color="white" if avg_similarity[i, j] > 0.5 else "black",
                             fontsize=9, fontweight='bold')
    
    ax.set_title('Average Topic Similarity Across All Time Bins\n'
                 '(El Clasico 10 Streams)',
                 fontweight='bold', fontsize=14, pad=20)
    
    # カラーバー
    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label('Cosine Similarity', rotation=270, labelpad=20, fontsize=12)
    
    plt.tight_layout()
    output_file = os.path.join(OUTPUT_DIR, 'topic_similarity_average_heatmap.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✅ Saved: {output_file}")
    plt.close()
    
    return avg_similarity, all_streams

def visualize_country_similarity(similarity_matrices):
    """国別の平均類似度"""
    print("\n" + "="*80)
    print("📊 Creating country-level similarity heatmap...")
    print("="*80)
    
    countries = ['Spain', 'Japan', 'UK', 'France']
    country_similarity = np.zeros((len(countries), len(countries)))
    count_matrix = np.zeros((len(countries), len(countries)))
    
    for data in similarity_matrices.values():
        streams = data['streams']
        similarity = data['similarity']
        stream_countries = data['countries']
        
        for i, (stream_i, country_i) in enumerate(zip(streams, stream_countries)):
            for j, (stream_j, country_j) in enumerate(zip(streams, stream_countries)):
                if country_i in countries and country_j in countries:
                    idx_i = countries.index(country_i)
                    idx_j = countries.index(country_j)
                    country_similarity[idx_i, idx_j] += similarity[i, j]
                    count_matrix[idx_i, idx_j] += 1
    
    # 平均を計算
    country_similarity = np.divide(country_similarity, count_matrix,
                                   where=count_matrix!=0,
                                   out=np.zeros_like(country_similarity))
    
    # 可視化
    fig, ax = plt.subplots(figsize=(8, 7))
    
    im = ax.imshow(country_similarity, cmap='YlOrRd', vmin=0, vmax=1)
    
    ax.set_xticks(np.arange(len(countries)))
    ax.set_yticks(np.arange(len(countries)))
    ax.set_xticklabels(countries, fontsize=12)
    ax.set_yticklabels(countries, fontsize=12)
    
    # 値を表示
    for i in range(len(countries)):
        for j in range(len(countries)):
            if count_matrix[i, j] > 0:
                text = ax.text(j, i, f'{country_similarity[i, j]:.3f}',
                             ha="center", va="center",
                             color="white" if country_similarity[i, j] > 0.5 else "black",
                             fontsize=14, fontweight='bold')
    
    ax.set_title('Country-Level Topic Similarity\n(Average Across All Time Bins)',
                 fontweight='bold', fontsize=14, pad=20)
    
    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label('Average Cosine Similarity', rotation=270, labelpad=20, fontsize=12)
    
    plt.tight_layout()
    output_file = os.path.join(OUTPUT_DIR, 'topic_similarity_by_country.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✅ Saved: {output_file}")
    plt.close()
    
    return country_similarity, countries

def save_similarity_stats(similarity_matrices, avg_similarity, all_streams):
    """類似度統計をCSVに保存"""
    print("\n" + "="*80)
    print("💾 Saving similarity statistics...")
    print("="*80)
    
    # 時間帯別統計
    time_stats = []
    for time_bin, data in sorted(similarity_matrices.items()):
        similarity = data['similarity']
        upper_tri = similarity[np.triu_indices_from(similarity, k=1)]
        
        time_stats.append({
            'time_bin': time_bin,
            'time_range': f'{int(time_bin*10)}-{int((time_bin+1)*10)}%',
            'num_streams': len(data['streams']),
            'avg_similarity': upper_tri.mean(),
            'std_similarity': upper_tri.std(),
            'min_similarity': upper_tri.min(),
            'max_similarity': upper_tri.max()
        })
    
    df_time_stats = pd.DataFrame(time_stats)
    output_file = os.path.join(OUTPUT_DIR, 'similarity_stats_by_time.csv')
    df_time_stats.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"✅ Saved: {output_file}")
    
    # 配信ペア別平均類似度
    pair_stats = []
    for i, stream_i in enumerate(all_streams):
        for j, stream_j in enumerate(all_streams):
            if i < j:  # 上三角のみ
                pair_stats.append({
                    'stream_1': stream_i,
                    'stream_2': stream_j,
                    'avg_similarity': avg_similarity[i, j]
                })
    
    df_pair_stats = pd.DataFrame(pair_stats).sort_values('avg_similarity', ascending=False)
    output_file = os.path.join(OUTPUT_DIR, 'stream_pair_similarities.csv')
    df_pair_stats.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"✅ Saved: {output_file}")

def main():
    print("="*80)
    print("🎯 Time-wise Topic Similarity Analysis - El Clasico")
    print("="*80)
    
    # 1. データ読み込みと時間帯分割
    stream_data = load_stream_data()
    
    # 2. 各配信・各時間帯でトピック抽出
    topic_df = extract_topics_per_stream_time(stream_data)
    
    # 3. 時間帯ごとの類似度行列計算
    similarity_matrices = calculate_similarity_matrix(topic_df)
    
    # 4. 可視化
    visualize_similarity_heatmaps(similarity_matrices)
    avg_similarity, all_streams = visualize_average_similarity_heatmap(similarity_matrices)
    country_similarity, countries = visualize_country_similarity(similarity_matrices)
    
    # 5. 統計保存
    save_similarity_stats(similarity_matrices, avg_similarity, all_streams)
    
    # サマリー
    print("\n" + "="*80)
    print("📊 ANALYSIS SUMMARY")
    print("="*80)
    print(f"Total streams analyzed: {len(stream_data)}")
    print(f"Time bins: {len(similarity_matrices)}")
    print(f"Total topic comparisons: {sum(len(d['streams']) for d in similarity_matrices.values())}")
    
    print("\n🌍 Country-level similarity:")
    for i, country_i in enumerate(countries):
        for j, country_j in enumerate(countries):
            if i < j:
                print(f"  {country_i} - {country_j}: {country_similarity[i, j]:.3f}")
    
    print("\n" + "="*80)
    print("✅ Time-wise Topic Similarity Analysis Complete!")
    print(f"📁 Output directory: {OUTPUT_DIR}/")
    print("="*80)

if __name__ == '__main__':
    main()
