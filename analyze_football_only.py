"""
スポーツ交絡の除去: フットボールのみの分析
Priority 2タスク - ベースボールとフットボールの混在による交絡を除去

目的:
1. フットボールのみ(9ストリーム)で全分析を再実行
2. ベースボール混在版との比較
3. より純粋な文化差を検出

データセット:
- El Clasico (9 streams): Spain(2), Japan(2), UK(4), France(1)
- 除外: Baseball streams (3 streams): Japan(1), USA(1), Dominican(1)
"""

import pandas as pd
import numpy as np
import emoji
import re
from collections import Counter
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import kruskal, mannwhitneyu
import os

# 日本語フォント設定
plt.rcParams['font.sans-serif'] = ['MS Gothic', 'Yu Gothic', 'Meiryo']
plt.rcParams['axes.unicode_minus'] = False

# フットボールのみのストリームリスト
FOOTBALL_STREAMS = {
    # El Clasico streams
    '⏱️ MINUTO A MINUTO _ Real Madrid vs Barcelona _ El Clásico_chat_log.csv': {
        'name': 'Spain_1',
        'country': 'Spain',
        'language': 'Spanish',
        'sport': 'Football'
    },
    '⚽️ REAL MADRID vs FC BARCELONA _ #LaLiga 25_26 - Jornada 10 _ \'EL CLÁSICO\' EN DIRECTO_chat_log.csv': {
        'name': 'Spain_2',
        'country': 'Spain',
        'language': 'Spanish',
        'sport': 'Football'
    },
    '【エルクラシコ】レアルマドリード×バルセロナ 0_15キックオフ リアルタイム戦術分析_chat_log.csv': {
        'name': 'Japan_1',
        'country': 'Japan',
        'language': 'Japanese',
        'sport': 'Football'
    },
    '【LIVE分析】レアルマドリードvsバルセロナ　▷ラ・リーガ｜第10節　エルクラシコ_chat_log.csv': {
        'name': 'Japan_2',
        'country': 'Japan',
        'language': 'Japanese',
        'sport': 'Football'
    },
    'Real Madrid vs Barcelona _EL CLASICO_ Laliga 2025 Live Reaction_chat_log.csv': {
        'name': 'UK_1',
        'country': 'UK',
        'language': 'English',
        'sport': 'Football'
    },
    'Real Madrid vs Barcelona _ La Liga LIVE WATCHALONG_chat_log.csv': {
        'name': 'UK_2',
        'country': 'UK',
        'language': 'English',
        'sport': 'Football'
    },
    'REAL MADRID VS BARCELONA _ EL CLASICO LIVE REACTION!_chat_log.csv': {
        'name': 'UK_3',
        'country': 'UK',
        'language': 'English',
        'sport': 'Football'
    },
    'Real Madrid vs Barcelona El Clasico Watchalong LaLiga LIVE _ TFHD_chat_log.csv': {
        'name': 'UK_4',
        'country': 'UK',
        'language': 'English',
        'sport': 'Football'
    },
    '🔴 REAL MADRID - BARCELONE LIVE _ 🚨LE CLASICO POUR LA 1ERE PLACE ! _ 🔥PLACE AU SPECTACLE ! _ LIGA_chat_log.csv': {
        'name': 'France',
        'country': 'France',
        'language': 'French',
        'sport': 'Football'
    }
}

def load_comments(stream_file):
    """コメントデータを読み込む"""
    file_path = f"data/chat/{stream_file}"
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
        if 'message' in df.columns:
            comments = df['message'].astype(str).tolist()
        elif 'text' in df.columns:
            comments = df['text'].astype(str).tolist()
        elif 'comment' in df.columns:
            comments = df['comment'].astype(str).tolist()
        else:
            text_cols = df.select_dtypes(include=['object']).columns
            if len(text_cols) > 0:
                comments = df[text_cols[0]].astype(str).tolist()
            else:
                return []
        
        comments = [c for c in comments if c != 'nan' and len(c) > 0]
        return comments
    except Exception as e:
        print(f"Error loading {stream_file}: {e}")
        return []

def analyze_emoji_usage(comments):
    """Emoji使用率と多様性を分析"""
    emoji_counts = []
    all_emojis = []
    
    for comment in comments:
        emoji_list = emoji.emoji_list(comment)
        emoji_counts.append(len(emoji_list))
        all_emojis.extend([e['emoji'] for e in emoji_list])
    
    emoji_rate = sum(emoji_counts) / len(comments) if comments else 0
    emoji_diversity = len(set(all_emojis))
    top_emojis = Counter(all_emojis).most_common(5) if all_emojis else []
    
    return {
        'emoji_rate': emoji_rate,
        'emoji_diversity': emoji_diversity,
        'top_emojis': top_emojis,
        'total_emojis': sum(emoji_counts)
    }

def analyze_laughter(comments, region):
    """笑いの表現を分析"""
    laugh_patterns = {
        'Spain': r'jaja+|jeje+|jiji+',
        'Japan': r'w{3,}|草+|笑+|ワロ',
        'UK': r'lol|haha+|lmao|rofl|lmfao',
        'France': r'mdr|ptdr|lol'
    }
    
    pattern = laugh_patterns.get(region, r'lol|haha+')
    
    laugh_matches = []
    for comment in comments:
        matches = re.findall(pattern, comment.lower())
        if matches:
            laugh_matches.extend(matches)
    
    laugh_rate = len([c for c in comments if re.search(pattern, c.lower())]) / len(comments) if comments else 0
    laugh_lengths = [len(match) for match in laugh_matches]
    avg_laugh_length = np.mean(laugh_lengths) if laugh_lengths else 0
    
    return {
        'laugh_rate': laugh_rate,
        'laugh_mean_length': avg_laugh_length,
        'laugh_total_count': len(laugh_matches)
    }

def analyze_exclamation(comments):
    """Exclamation（!）の使用を分析"""
    exclamation_counts = [comment.count('!') for comment in comments]
    exclamation_rate = sum(exclamation_counts) / len(comments) if comments else 0
    
    return {
        'exclamation_rate': exclamation_rate,
        'exclamation_total': sum(exclamation_counts)
    }

def analyze_comment_length(comments):
    """コメントの長さを分析"""
    lengths = [len(comment) for comment in comments]
    
    return {
        'mean_length': np.mean(lengths) if lengths else 0,
        'median_length': np.median(lengths) if lengths else 0,
        'std_length': np.std(lengths) if lengths else 0
    }

def calculate_cpm(timestamps, window=60):
    """Comments Per Minute (CPM) を計算"""
    if len(timestamps) == 0:
        return []
    
    timestamps_sec = pd.to_datetime(timestamps).astype(np.int64) // 10**9
    min_time = timestamps_sec.min()
    max_time = timestamps_sec.max()
    
    bins = np.arange(min_time, max_time + window, window)
    hist, _ = np.histogram(timestamps_sec, bins=bins)
    
    cpm = hist * (60 / window)
    return cpm

def detect_bursts(cpm_values, threshold_factor=2):
    """コメントバーストを検出"""
    if len(cpm_values) == 0:
        return []
    
    mean_cpm = np.mean(cpm_values)
    std_cpm = np.std(cpm_values)
    threshold = mean_cpm + threshold_factor * std_cpm
    
    from scipy.signal import find_peaks
    peaks, properties = find_peaks(cpm_values, height=threshold)
    
    return peaks

def analyze_engagement(stream_file):
    """エンゲージメントパターンを分析"""
    file_path = f"data/chat/{stream_file}"
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
        
        # Timestamp列の検出
        timestamp_col = None
        for col in ['timestamp', 'time', 'created_at', 'date']:
            if col in df.columns:
                timestamp_col = col
                break
        
        if timestamp_col is None:
            return None
        
        timestamps = pd.to_datetime(df[timestamp_col], errors='coerce')
        timestamps = timestamps.dropna()
        
        if len(timestamps) < 10:
            return None
        
        # CPM計算
        cpm_values = calculate_cpm(timestamps, window=60)
        mean_cpm = np.mean(cpm_values) if len(cpm_values) > 0 else 0
        
        # バースト検出
        burst_indices = detect_bursts(cpm_values)
        
        # バースト統計
        burst_freq_per_hour = len(burst_indices) / (len(timestamps) / 3600) if len(timestamps) > 0 else 0
        
        # バースト継続時間と強度
        burst_durations = []
        burst_intensities = []
        
        for peak in burst_indices:
            start = max(0, peak - 5)
            end = min(len(cpm_values), peak + 5)
            burst_durations.append(end - start)
            if len(cpm_values) > 0:
                burst_intensities.append(cpm_values[peak] / mean_cpm if mean_cpm > 0 else 0)
        
        return {
            'mean_cpm': mean_cpm,
            'burst_freq_per_hour': burst_freq_per_hour,
            'mean_burst_duration': np.mean(burst_durations) if burst_durations else 0,
            'mean_burst_intensity': np.mean(burst_intensities) if burst_intensities else 0,
            'num_bursts': len(burst_indices)
        }
    except Exception as e:
        print(f"Error analyzing engagement for {stream_file}: {e}")
        return None

def main():
    print("="*80)
    print("フットボールのみの文化分析 (スポーツ交絡除去)")
    print("="*80)
    print(f"\n分析対象: {len(FOOTBALL_STREAMS)} streams (Football only)")
    print("除外: Baseball streams (Japan Baseball, USA, Dominican)")
    print()
    
    # 結果格納
    results = []
    
    # 各ストリームを分析
    for stream_file, metadata in FOOTBALL_STREAMS.items():
        print(f"Processing: {metadata['name']} ({metadata['country']})...")
        
        comments = load_comments(stream_file)
        
        if len(comments) == 0:
            print(f"  ⚠️ No comments found, skipping...")
            continue
        
        # 感情表現分析
        emoji_stats = analyze_emoji_usage(comments)
        laugh_stats = analyze_laughter(comments, metadata['country'])
        exclamation_stats = analyze_exclamation(comments)
        length_stats = analyze_comment_length(comments)
        
        # エンゲージメント分析
        engagement_stats = analyze_engagement(stream_file)
        
        # 結果統合
        result = {
            'stream': metadata['name'],
            'country': metadata['country'],
            'language': metadata['language'],
            'sport': metadata['sport'],
            'num_comments': len(comments),
            **emoji_stats,
            **laugh_stats,
            **exclamation_stats,
            **length_stats
        }
        
        if engagement_stats:
            result.update(engagement_stats)
        
        results.append(result)
        print(f"  ✅ Processed {len(comments):,} comments")
    
    # DataFrameに変換
    df = pd.DataFrame(results)
    
    # 出力ディレクトリ作成
    output_dir = 'output/football_only_analysis'
    os.makedirs(output_dir, exist_ok=True)
    
    # CSV保存
    df.to_csv(f'{output_dir}/football_only_results.csv', index=False, encoding='utf-8-sig')
    print(f"\n✅ Results saved: {output_dir}/football_only_results.csv")
    
    # 国別集計
    print("\n" + "="*80)
    print("国別統計 (Football only)")
    print("="*80)
    
    country_stats = df.groupby('country').agg({
        'num_comments': ['count', 'sum', 'mean'],
        'emoji_rate': ['mean', 'std'],
        'laugh_rate': ['mean', 'std'],
        'exclamation_rate': ['mean', 'std'],
        'mean_length': ['mean', 'std'],
        'mean_cpm': ['mean', 'std']
    }).round(3)
    
    print(country_stats)
    
    # 比較可視化
    create_comparison_visualizations(df, output_dir)
    
    print("\n" + "="*80)
    print("フットボールのみの分析完了!")
    print("="*80)
    print(f"📁 結果: {output_dir}/")
    print("📊 次のステップ: Baseball混在版との比較レポート作成")
    
    return df

def create_comparison_visualizations(df, output_dir):
    """比較可視化を作成"""
    
    # Figure 1: Emoji rate comparison (Football only)
    fig, ax = plt.subplots(figsize=(12, 6))
    
    countries = df.groupby('country')['emoji_rate'].mean().sort_values(ascending=False)
    colors = plt.cm.Set3(np.linspace(0, 1, len(countries)))
    
    ax.bar(countries.index, countries.values, color=colors, edgecolor='black', linewidth=1.5)
    ax.set_ylabel('Emoji Rate (emojis/comment)', fontsize=12, fontweight='bold')
    ax.set_xlabel('Country', fontsize=12, fontweight='bold')
    ax.set_title('Emoji Usage Rate by Country (Football Only - No Baseball Confounding)', 
                fontsize=14, fontweight='bold')
    ax.grid(alpha=0.3, axis='y')
    
    # 各国のストリーム数を表示
    for i, country in enumerate(countries.index):
        n = len(df[df['country'] == country])
        ax.text(i, countries.values[i] + 0.05, f'n={n}', 
               ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/emoji_rate_football_only.png', dpi=300, bbox_inches='tight')
    print(f"✅ Saved: emoji_rate_football_only.png")
    plt.close()
    
    # Figure 2: Multi-metric comparison
    metrics = ['emoji_rate', 'laugh_rate', 'exclamation_rate', 'mean_length']
    metric_labels = ['Emoji Rate', 'Laugh Rate', 'Exclamation Rate', 'Mean Length']
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()
    
    for idx, (metric, label) in enumerate(zip(metrics, metric_labels)):
        ax = axes[idx]
        
        data_by_country = df.groupby('country')[metric].mean().sort_values(ascending=False)
        
        ax.bar(data_by_country.index, data_by_country.values, 
              color=colors[:len(data_by_country)], edgecolor='black', linewidth=1.5)
        ax.set_ylabel(label, fontsize=11, fontweight='bold')
        ax.set_xlabel('Country', fontsize=11, fontweight='bold')
        ax.set_title(f'{label} (Football Only)', fontsize=12, fontweight='bold')
        ax.grid(alpha=0.3, axis='y')
        
        # Sample sizes
        for i, country in enumerate(data_by_country.index):
            n = len(df[df['country'] == country])
            ax.text(i, data_by_country.values[i] * 0.05, f'n={n}', 
                   ha='center', va='bottom', fontsize=9)
    
    plt.suptitle('Cultural Differences in Watching Style (Football Only - Confounding Removed)', 
                fontsize=14, fontweight='bold', y=0.995)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/multi_metric_comparison_football_only.png', dpi=300, bbox_inches='tight')
    print(f"✅ Saved: multi_metric_comparison_football_only.png")
    plt.close()
    
    # Figure 3: Heatmap
    metrics_for_heatmap = ['emoji_rate', 'laugh_rate', 'exclamation_rate', 
                          'mean_length', 'mean_cpm']
    
    country_profiles = df.groupby('country')[metrics_for_heatmap].mean()
    
    # 正規化 (0-1)
    from sklearn.preprocessing import MinMaxScaler
    scaler = MinMaxScaler()
    normalized_profiles = pd.DataFrame(
        scaler.fit_transform(country_profiles),
        columns=country_profiles.columns,
        index=country_profiles.index
    )
    
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.heatmap(normalized_profiles.T, annot=True, fmt='.2f', cmap='YlOrRd', 
               cbar_kws={'label': 'Normalized Value (0-1)'}, linewidths=0.5)
    ax.set_xlabel('Country', fontsize=12, fontweight='bold')
    ax.set_ylabel('Metric', fontsize=12, fontweight='bold')
    ax.set_title('Cultural Profiles (Football Only - Normalized)', 
                fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/cultural_profiles_heatmap_football_only.png', dpi=300, bbox_inches='tight')
    print(f"✅ Saved: cultural_profiles_heatmap_football_only.png")
    plt.close()

if __name__ == '__main__':
    df_football = main()
