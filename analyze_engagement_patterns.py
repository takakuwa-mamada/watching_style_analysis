"""
軸1: エンゲージメントパターンの定量化
Comment密度、Burst特性、反応タイミングの分析
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import kruskal, mannwhitneyu
from scipy.signal import find_peaks
from datetime import datetime, timedelta
import os

# 日本語フォント設定
plt.rcParams['font.sans-serif'] = ['MS Gothic', 'Yu Gothic', 'Meiryo']
plt.rcParams['axes.unicode_minus'] = False

def load_comments_with_timestamps(stream_file):
    """タイムスタンプ付きコメントを読み込む"""
    file_path = f"data/chat/{stream_file}"
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
        
        # タイムスタンプカラムを探す
        time_col = None
        for col in ['time_in_seconds', 'timestamp', 'time', 'seconds']:
            if col in df.columns:
                time_col = col
                break
        
        if time_col is None:
            print(f"Warning: No timestamp column found in {stream_file}")
            return None
        
        # メッセージカラムを探す
        message_col = None
        for col in ['message', 'text', 'comment']:
            if col in df.columns:
                message_col = col
                break
        
        if message_col is None:
            print(f"Warning: No message column found in {stream_file}")
            return None
        
        # 有効なデータのみ抽出
        df_clean = df[[time_col, message_col]].copy()
        df_clean.columns = ['timestamp', 'message']
        df_clean = df_clean.dropna()
        
        # タイムスタンプを日時型に変換して秒数に
        try:
            df_clean['timestamp'] = pd.to_datetime(df_clean['timestamp'])
            # 最初のタイムスタンプを0として相対秒数に変換
            start_time = df_clean['timestamp'].min()
            df_clean['timestamp'] = (df_clean['timestamp'] - start_time).dt.total_seconds()
        except:
            # 既に数値の場合
            df_clean['timestamp'] = pd.to_numeric(df_clean['timestamp'], errors='coerce')
        
        df_clean = df_clean.dropna()
        df_clean = df_clean.sort_values('timestamp')
        
        return df_clean
        
    except Exception as e:
        print(f"Error loading {stream_file}: {e}")
        return None

def calculate_cpm(timestamps, window_seconds=60):
    """Comments Per Minute (CPM) を計算"""
    if len(timestamps) == 0:
        return np.array([])
    
    start_time = timestamps.min()
    end_time = timestamps.max()
    duration = end_time - start_time
    
    # 1分ごとのビンを作成
    bins = np.arange(start_time, end_time + window_seconds, window_seconds)
    
    # 各ビンのコメント数をカウント
    counts, _ = np.histogram(timestamps, bins=bins)
    
    # CPMに変換（コメント数 / 分）
    cpm = counts / (window_seconds / 60)
    
    return cpm

def detect_bursts(cpm, threshold_std=2.0):
    """Burst（盛り上がり）を検出"""
    if len(cpm) == 0:
        return []
    
    mean_cpm = np.mean(cpm)
    std_cpm = np.std(cpm)
    threshold = mean_cpm + threshold_std * std_cpm
    
    # ピークを検出
    peaks, properties = find_peaks(cpm, height=threshold, distance=3)
    
    bursts = []
    for peak_idx in peaks:
        # Burst開始・終了を検出
        start_idx = peak_idx
        end_idx = peak_idx
        
        # 後方にスキャン（閾値を下回るまで）
        while start_idx > 0 and cpm[start_idx - 1] > mean_cpm:
            start_idx -= 1
        
        # 前方にスキャン
        while end_idx < len(cpm) - 1 and cpm[end_idx + 1] > mean_cpm:
            end_idx += 1
        
        burst = {
            'peak_index': peak_idx,
            'start_index': start_idx,
            'end_index': end_idx,
            'peak_cpm': cpm[peak_idx],
            'duration': (end_idx - start_idx + 1),  # in minutes
            'intensity': cpm[peak_idx] / mean_cpm if mean_cpm > 0 else 0
        }
        bursts.append(burst)
    
    return bursts

def analyze_engagement(df_comments):
    """エンゲージメント指標を計算"""
    if df_comments is None or len(df_comments) == 0:
        return None
    
    timestamps = df_comments['timestamp'].values
    
    # CPM計算
    cpm = calculate_cpm(timestamps, window_seconds=60)
    
    if len(cpm) == 0:
        return None
    
    # Burst検出
    bursts = detect_bursts(cpm, threshold_std=2.0)
    
    # 統計量計算
    mean_cpm = np.mean(cpm)
    peak_cpm = np.max(cpm)
    cv_cpm = np.std(cpm) / mean_cpm if mean_cpm > 0 else 0
    
    # Burst統計
    if bursts:
        burst_freq = len(bursts) / (len(cpm) / 60)  # bursts per hour
        burst_durations = [b['duration'] for b in bursts]
        burst_intensities = [b['intensity'] for b in bursts]
        mean_burst_duration = np.mean(burst_durations)
        mean_burst_intensity = np.mean(burst_intensities)
    else:
        burst_freq = 0
        mean_burst_duration = 0
        mean_burst_intensity = 0
    
    # 全体統計
    total_duration = (timestamps.max() - timestamps.min()) / 60  # minutes
    
    return {
        'total_comments': len(df_comments),
        'duration_minutes': total_duration,
        'mean_cpm': mean_cpm,
        'peak_cpm': peak_cpm,
        'cv_cpm': cv_cpm,
        'burst_count': len(bursts),
        'burst_freq_per_hour': burst_freq,
        'mean_burst_duration': mean_burst_duration,
        'mean_burst_intensity': mean_burst_intensity,
        'cpm_series': cpm,
        'bursts': bursts
    }

def get_broadcaster_mapping():
    """ファイル名からbroadcaster情報へのマッピング"""
    return {
        # El Clasico streams
        '⏱️ MINUTO A MINUTO _ Real Madrid vs Barcelona _ El Clásico_chat_log.csv': {
            'name': 'Spain_1',
            'country': 'Spain',
            'language': 'Spanish',
            'region': 'Europe'
        },
        '⚽️ REAL MADRID vs FC BARCELONA _ #LaLiga 25_26 - Jornada 10 _ \'EL CLÁSICO\' EN DIRECTO_chat_log.csv': {
            'name': 'Spain_2',
            'country': 'Spain',
            'language': 'Spanish',
            'region': 'Europe'
        },
        'REAL MADRID VS FC BARCELONA EN DIRECTO _ EL CLASICO _ LALIGA _ Tiempo de Juego COPE _ EN VIVO_chat_log.csv': {
            'name': 'Spain_3',
            'country': 'Spain',
            'language': 'Spanish',
            'region': 'Europe'
        },
        '【エルクラシコ】レアルマドリード×バルセロナ 0_15キックオフ リアルタイム戦術分析_chat_log.csv': {
            'name': 'Japan_1',
            'country': 'Japan',
            'language': 'Japanese',
            'region': 'Asia'
        },
        '【LIVE分析】レアルマドリードvsバルセロナ　▷ラ・リーガ｜第10節　エルクラシコ_chat_log.csv': {
            'name': 'Japan_2',
            'country': 'Japan',
            'language': 'Japanese',
            'region': 'Asia'
        },
        'Real Madrid vs Barcelona _EL CLASICO_ Laliga 2025 Live Reaction_chat_log.csv': {
            'name': 'UK_1',
            'country': 'UK',
            'language': 'English',
            'region': 'Europe'
        },
        'Real Madrid vs Barcelona _ La Liga LIVE WATCHALONG_chat_log.csv': {
            'name': 'UK_2',
            'country': 'UK',
            'language': 'English',
            'region': 'Europe'
        },
        'REAL MADRID VS BARCELONA _ EL CLASICO LIVE REACTION!_chat_log.csv': {
            'name': 'UK_3',
            'country': 'UK',
            'language': 'English',
            'region': 'Europe'
        },
        'Real Madrid vs Barcelona El Clasico Watchalong LaLiga LIVE _ TFHD_chat_log.csv': {
            'name': 'UK_4',
            'country': 'UK',
            'language': 'English',
            'region': 'Europe'
        },
        '🔴 REAL MADRID - BARCELONE LIVE _ 🚨LE CLASICO POUR LA 1ERE PLACE ! _ 🔥PLACE AU SPECTACLE ! _ LIGA_chat_log.csv': {
            'name': 'France',
            'country': 'France',
            'language': 'French',
            'region': 'Europe'
        },
        # Baseball streams
        'Dodgers_WhiteSox_Japan.csv': {
            'name': 'Japan_Baseball',
            'country': 'Japan',
            'language': 'Japanese',
            'region': 'Asia'
        },
        'Dodgers_WhiteSox_US.csv': {
            'name': 'US_Baseball',
            'country': 'USA',
            'language': 'English',
            'region': 'North America'
        },
        'Dodgers_WhiteSox_Dominican.csv': {
            'name': 'Dominican_Baseball',
            'country': 'Dominican',
            'language': 'Spanish',
            'region': 'Latin America'
        }
    }

def main():
    print("="*80)
    print("軸1: エンゲージメントパターンの定量化")
    print("="*80)
    
    file_mapping = get_broadcaster_mapping()
    
    all_results = []
    
    print("\n📊 各配信の分析開始...\n")
    
    for filename, info in file_mapping.items():
        print(f"Processing: {info['name']} ({info['country']})...")
        
        # コメント読み込み
        df_comments = load_comments_with_timestamps(filename)
        
        if df_comments is None:
            print(f"  ⚠️ データ読み込み失敗")
            continue
        
        print(f"  Total comments: {len(df_comments)}")
        
        # エンゲージメント分析
        engagement = analyze_engagement(df_comments)
        
        if engagement is None:
            print(f"  ⚠️ 分析失敗")
            continue
        
        # 結果統合
        result = {
            'broadcaster': info['name'],
            'country': info['country'],
            'language': info['language'],
            'region': info['region'],
            **{k: v for k, v in engagement.items() if k not in ['cpm_series', 'bursts']}
        }
        
        # CPMとBurstデータを別途保存
        result['_cpm_series'] = engagement['cpm_series']
        result['_bursts'] = engagement['bursts']
        
        all_results.append(result)
        
        print(f"  ✅ Mean CPM: {engagement['mean_cpm']:.1f}")
        print(f"  ✅ Peak CPM: {engagement['peak_cpm']:.1f}")
        print(f"  ✅ Bursts detected: {engagement['burst_count']}")
        print()
    
    # DataFrameに変換（CPM seriesとburstsを除く）
    df_results = pd.DataFrame([{k: v for k, v in r.items() if not k.startswith('_')} 
                                for r in all_results])
    
    # 結果を保存
    output_dir = 'output/engagement_analysis'
    os.makedirs(output_dir, exist_ok=True)
    
    df_results.to_csv(f'{output_dir}/engagement_results.csv', index=False, encoding='utf-8-sig')
    print(f"✅ Results saved to {output_dir}/engagement_results.csv")
    
    # 国別に集計
    print("\n" + "="*80)
    print("📊 国別集計結果")
    print("="*80)
    
    country_summary = df_results.groupby('country').agg({
        'mean_cpm': ['mean', 'std'],
        'peak_cpm': ['mean', 'std'],
        'cv_cpm': ['mean', 'std'],
        'burst_freq_per_hour': ['mean', 'std'],
        'mean_burst_duration': ['mean', 'std'],
        'mean_burst_intensity': ['mean', 'std']
    }).round(2)
    
    print(country_summary)
    
    # 統計的検定
    print("\n" + "="*80)
    print("📈 統計的検定")
    print("="*80)
    
    countries = df_results['country'].unique()
    
    if len(countries) >= 3:
        for metric in ['mean_cpm', 'burst_freq_per_hour', 'mean_burst_duration', 'mean_burst_intensity']:
            groups = [df_results[df_results['country'] == c][metric].values for c in countries]
            groups = [g for g in groups if len(g) > 0]
            
            if len(groups) >= 2:
                h_stat, p_value = kruskal(*groups)
                print(f"\n{metric}:")
                print(f"  Kruskal-Wallis H = {h_stat:.3f}, p = {p_value:.4f}")
                
                if p_value < 0.05:
                    print(f"  ✅ Significant difference detected!")
                else:
                    print(f"  ❌ No significant difference")
    
    # 可視化
    print("\n" + "="*80)
    print("🎨 可視化作成中...")
    print("="*80)
    
    create_visualizations(df_results, all_results, output_dir)
    
    print("\n✅ 分析完了！")
    print(f"📁 結果は {output_dir}/ に保存されました")

def create_visualizations(df, all_results, output_dir):
    """可視化を作成"""
    
    # Figure 1: エンゲージメント指標の比較
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    metrics = [
        ('mean_cpm', 'Mean CPM (comments/minute)', axes[0, 0]),
        ('burst_freq_per_hour', 'Burst Frequency (bursts/hour)', axes[0, 1]),
        ('mean_burst_duration', 'Mean Burst Duration (minutes)', axes[1, 0]),
        ('mean_burst_intensity', 'Mean Burst Intensity (×baseline)', axes[1, 1])
    ]
    
    for metric, title, ax in metrics:
        sns.barplot(data=df, x='country', y=metric, ax=ax, hue='country', palette='Set2', errorbar='sd', legend=False)
        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.set_xlabel('Country', fontsize=10)
        ax.set_ylabel(title.split('(')[0].strip(), fontsize=10)
        ax.tick_params(axis='x', rotation=45)
        
        # データポイントを追加
        for i, country in enumerate(df['country'].unique()):
            values = df[df['country'] == country][metric].values
            x_positions = np.random.normal(i, 0.04, size=len(values))
            ax.scatter(x_positions, values, alpha=0.5, color='black', s=20)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/engagement_patterns_comparison.png', dpi=300, bbox_inches='tight')
    print(f"✅ Saved: engagement_patterns_comparison.png")
    plt.close()
    
    # Figure 2: CPM時系列（国別のサンプル）
    fig, axes = plt.subplots(3, 2, figsize=(15, 12))
    axes = axes.flatten()
    
    for idx, result in enumerate(all_results[:6]):  # 最初の6つ
        if idx >= len(axes):
            break
        
        ax = axes[idx]
        cpm_series = result['_cpm_series']
        bursts = result['_bursts']
        
        # CPM時系列をプロット
        time_axis = np.arange(len(cpm_series))
        ax.plot(time_axis, cpm_series, linewidth=1.5, color='steelblue')
        
        # 平均線
        mean_cpm = np.mean(cpm_series)
        ax.axhline(y=mean_cpm, color='green', linestyle='--', label=f'Mean: {mean_cpm:.1f}', alpha=0.7)
        
        # Burstを強調
        if bursts:
            for burst in bursts:
                ax.axvspan(burst['start_index'], burst['end_index'], 
                          alpha=0.3, color='red', label='Burst' if burst == bursts[0] else '')
        
        ax.set_title(f"{result['broadcaster']} ({result['country']})", 
                    fontsize=10, fontweight='bold')
        ax.set_xlabel('Time (minutes)', fontsize=9)
        ax.set_ylabel('CPM', fontsize=9)
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)
    
    # 未使用のサブプロットを非表示
    for idx in range(len(all_results[:6]), len(axes)):
        axes[idx].axis('off')
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/cpm_timeseries_samples.png', dpi=300, bbox_inches='tight')
    print(f"✅ Saved: cpm_timeseries_samples.png")
    plt.close()
    
    # Figure 3: CPM vs Burst Frequency scatter
    fig, ax = plt.subplots(figsize=(10, 6))
    
    for country in df['country'].unique():
        country_data = df[df['country'] == country]
        ax.scatter(country_data['mean_cpm'], 
                  country_data['burst_freq_per_hour'],
                  label=country, s=100, alpha=0.7)
    
    ax.set_xlabel('Mean CPM (comments/minute)', fontsize=12)
    ax.set_ylabel('Burst Frequency (bursts/hour)', fontsize=12)
    ax.set_title('Engagement: CPM vs Burst Frequency', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/cpm_vs_burst_frequency.png', dpi=300, bbox_inches='tight')
    print(f"✅ Saved: cpm_vs_burst_frequency.png")
    plt.close()
    
    # Figure 4: Heatmap（国別の特徴）
    fig, ax = plt.subplots(figsize=(10, 6))
    
    country_means = df.groupby('country').agg({
        'mean_cpm': 'mean',
        'peak_cpm': 'mean',
        'burst_freq_per_hour': 'mean',
        'mean_burst_duration': 'mean',
        'mean_burst_intensity': 'mean'
    }).reset_index()
    
    # 正規化（0-1スケール）
    metrics_for_heatmap = ['mean_cpm', 'peak_cpm', 'burst_freq_per_hour', 
                           'mean_burst_duration', 'mean_burst_intensity']
    heatmap_data = country_means[metrics_for_heatmap]
    heatmap_data_normalized = (heatmap_data - heatmap_data.min()) / (heatmap_data.max() - heatmap_data.min())
    heatmap_data_normalized.index = country_means['country']
    
    # ラベルを短縮
    labels = ['Mean CPM', 'Peak CPM', 'Burst Freq', 'Burst Duration', 'Burst Intensity']
    heatmap_data_normalized.columns = labels
    
    sns.heatmap(heatmap_data_normalized.T, annot=True, fmt='.2f', cmap='YlOrRd', 
                cbar_kws={'label': 'Normalized Score (0-1)'}, ax=ax)
    ax.set_title('Engagement Profile by Country (Normalized)', fontsize=14, fontweight='bold')
    ax.set_xlabel('Country', fontsize=12)
    ax.set_ylabel('Metric', fontsize=12)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/engagement_profile_heatmap.png', dpi=300, bbox_inches='tight')
    print(f"✅ Saved: engagement_profile_heatmap.png")
    plt.close()

if __name__ == "__main__":
    main()
