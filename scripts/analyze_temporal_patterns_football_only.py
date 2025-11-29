"""
詳細な時系列分析 (Football-Only版)
研究計画書 4節「盛り上がりのタイミングに注目」に対応

試合進行に沿った時系列パターンを可視化:
1. コメント密度の時系列変化
2. 国別の時間的パターン
3. バースト詳細分析
4. 感情表現の時系列推移
"""

import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from scipy.signal import find_peaks
import warnings
warnings.filterwarnings('ignore')

# UTF-8エンコーディング設定（文字化け防止）
import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 日本語フォント設定（優先順位を変更）
import matplotlib
matplotlib.rcParams['font.family'] = 'sans-serif'
matplotlib.rcParams['font.sans-serif'] = ['Yu Gothic', 'Meiryo', 'MS Gothic', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Yu Gothic', 'Meiryo', 'MS Gothic', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ==================== データ設定 ====================
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
OUTPUT_DIR = 'output/temporal_analysis_el_clasico'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ==================== データ読み込み ====================
def load_football_data():
    """Football-Only 9配信のコメントを読み込む"""
    all_data = []
    
    for stream_file, meta in FOOTBALL_STREAMS.items():
        filepath = os.path.join(DATA_DIR, stream_file)
        if not os.path.exists(filepath):
            print(f"⚠️  Warning: {filepath} not found, skipping...")
            continue
        
        try:
            df = pd.read_csv(filepath, encoding='utf-8')
            
            # テキストカラム
            text_col = None
            for col in ['message', 'text', 'comment', 'body']:
                if col in df.columns:
                    text_col = col
                    break
            
            if text_col is None:
                print(f"⚠️  Warning: No text column in {stream_file}")
                continue
            
            # タイムスタンプカラム
            time_col = None
            for col in ['timestamp', 'time', 'time_seconds', 'elapsed_time']:
                if col in df.columns:
                    time_col = col
                    break
            
            # データ整形
            df_clean = df[[text_col]].copy()
            df_clean['comment'] = df_clean[text_col].astype(str)
            df_clean['country'] = meta['country']
            df_clean['stream'] = meta['name']
            
            if time_col:
                # タイムスタンプをdatetimeに変換してから数値化
                try:
                    df_clean['timestamp'] = pd.to_datetime(df[time_col], errors='coerce')
                    # 最初のタイムスタンプからの経過秒数に変換
                    first_time = df_clean['timestamp'].min()
                    df_clean['timestamp'] = (df_clean['timestamp'] - first_time).dt.total_seconds()
                except:
                    # 変換失敗時は行番号を使用
                    df_clean['timestamp'] = np.arange(len(df))
            else:
                # 疑似タイムスタンプ (行番号ベース)
                df_clean['timestamp'] = np.arange(len(df))
            
            # NaN除外
            df_clean = df_clean[df_clean['comment'].notna()]
            df_clean = df_clean[df_clean['comment'].astype(str).str.strip() != '']
            df_clean = df_clean.dropna(subset=['timestamp'])
            
            all_data.append(df_clean)
            print(f"✅ Loaded {len(df_clean)} comments from {meta['name']} ({meta['country']})")
            
        except Exception as e:
            print(f"❌ Error loading {stream_file}: {e}")
    
    if not all_data:
        raise ValueError("No data loaded!")
    
    combined = pd.concat(all_data, ignore_index=True)
    print(f"\n📊 Total: {len(combined)} comments from {len(combined['stream'].unique())} streams")
    
    return combined

# ==================== 感情表現の抽出 ====================
def extract_emotional_features(text):
    """感情表現を抽出"""
    text = str(text).lower()
    
    # Emoji count (簡易版)
    emoji_count = len([c for c in text if ord(c) > 0x1F300])
    
    # Exclamation
    exclamation_count = text.count('!')
    
    # Laugh (w, lol, haha, jaja)
    laugh_patterns = ['w', 'lol', 'haha', 'jaja', 'kkkk']
    laugh_count = sum([text.count(p) for p in laugh_patterns])
    
    return {
        'emoji_count': emoji_count,
        'exclamation_count': exclamation_count,
        'laugh_count': laugh_count
    }

# ==================== 時系列密度分析 ====================
def analyze_comment_density(df):
    """コメント密度の時系列分析"""
    print("\n📈 Analyzing comment density over time...")
    
    # 時間を正規化 (0-100%)
    df['time_normalized'] = (df['timestamp'] - df['timestamp'].min()) / \
                            (df['timestamp'].max() - df['timestamp'].min()) * 100
    
    # 時間ビン (1%刻み)
    df['time_bin'] = pd.cut(df['time_normalized'], bins=100, labels=False)
    
    # 全体密度
    overall_density = df.groupby('time_bin').size()
    
    # 国別密度
    country_density = df.groupby(['time_bin', 'country']).size().unstack(fill_value=0)
    
    # 可視化: 全体
    fig, ax = plt.subplots(figsize=(16, 5))
    ax.plot(overall_density.index, overall_density.values, 
            linewidth=2, color='#2E86AB', alpha=0.8)
    ax.fill_between(overall_density.index, overall_density.values, 
                     alpha=0.3, color='#2E86AB')
    ax.set_xlabel('Match Progress (%)', fontsize=14, fontweight='bold')
    ax.set_ylabel('Comment Count per 1% Time Bin', fontsize=14, fontweight='bold')
    ax.set_title('Comment Density Timeline - All Streams', 
                 fontsize=16, fontweight='bold', pad=20)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'comment_density_overall.png'), 
                dpi=300, bbox_inches='tight')
    print(f"✅ Saved: comment_density_overall.png")
    plt.close()
    
    # 可視化: 国別
    fig, ax = plt.subplots(figsize=(16, 6))
    for country in country_density.columns:
        ax.plot(country_density.index, country_density[country], 
                linewidth=2.5, label=country, marker='', alpha=0.8)
    ax.set_xlabel('Match Progress (%)', fontsize=14, fontweight='bold')
    ax.set_ylabel('Comment Count per 1% Time Bin', fontsize=14, fontweight='bold')
    ax.set_title('Comment Density Timeline - Country Comparison', 
                 fontsize=16, fontweight='bold', pad=20)
    ax.legend(fontsize=12, loc='upper left')
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'comment_density_by_country.png'), 
                dpi=300, bbox_inches='tight')
    print(f"✅ Saved: comment_density_by_country.png")
    plt.close()
    
    # CSV保存
    overall_density.to_csv(os.path.join(OUTPUT_DIR, 'comment_density_overall.csv'))
    country_density.to_csv(os.path.join(OUTPUT_DIR, 'comment_density_by_country.csv'))
    
    return overall_density, country_density

# ==================== バースト検出 ====================
def detect_bursts(df):
    """コメントバーストを詳細に検出"""
    print("\n💥 Detecting comment bursts...")
    
    # 時間ビン (30秒間隔または100ビン)
    df['time_bin_fine'] = pd.cut(df['timestamp'], bins=100, labels=False)
    
    # 時間ビンごとのコメント数
    bin_counts = df.groupby('time_bin_fine').size()
    
    # ピーク検出 (高さ: 平均の1.5倍以上)
    threshold = bin_counts.mean() + 1.5 * bin_counts.std()
    peaks, properties = find_peaks(bin_counts.values, height=threshold, distance=3)
    
    # バースト情報
    burst_info = []
    for i, peak_idx in enumerate(peaks):
        peak_time = bin_counts.index[peak_idx]
        peak_height = bin_counts.iloc[peak_idx]
        
        # そのバーストのコメント取得
        burst_comments = df[df['time_bin_fine'] == peak_time]['comment'].tolist()
        
        burst_info.append({
            'Burst_ID': i + 1,
            'Time_Bin': peak_time,
            'Time_Percent': (peak_time / 100) * 100,
            'Peak_Height': peak_height,
            'Sample_Comments': ' | '.join(burst_comments[:3])
        })
    
    burst_df = pd.DataFrame(burst_info)
    print(f"✅ Detected {len(burst_df)} bursts")
    
    # 可視化
    fig, ax = plt.subplots(figsize=(16, 6))
    ax.plot(bin_counts.index, bin_counts.values, linewidth=2, 
            color='#2E86AB', alpha=0.7, label='Comment Count')
    ax.scatter(peaks, bin_counts.iloc[peaks], color='red', s=100, 
               zorder=5, label=f'Bursts (n={len(peaks)})')
    ax.axhline(threshold, color='orange', linestyle='--', linewidth=2, 
               label='Threshold', alpha=0.7)
    ax.set_xlabel('Time Bin', fontsize=14, fontweight='bold')
    ax.set_ylabel('Comment Count', fontsize=14, fontweight='bold')
    ax.set_title('Comment Burst Detection', fontsize=16, fontweight='bold', pad=20)
    ax.legend(fontsize=12)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'burst_detection.png'), 
                dpi=300, bbox_inches='tight')
    print(f"✅ Saved: burst_detection.png")
    plt.close()
    
    # CSV保存
    burst_df.to_csv(os.path.join(OUTPUT_DIR, 'burst_details.csv'), index=False)
    print(f"✅ Saved: burst_details.csv")
    
    return burst_df

# ==================== 感情表現の時系列 ====================
def analyze_emotion_timeline(df):
    """感情表現の時系列推移"""
    print("\n😊 Analyzing emotion timeline...")
    
    # 感情表現を抽出
    emotion_features = df['comment'].apply(extract_emotional_features)
    df['emoji_count'] = emotion_features.apply(lambda x: x['emoji_count'])
    df['exclamation_count'] = emotion_features.apply(lambda x: x['exclamation_count'])
    df['laugh_count'] = emotion_features.apply(lambda x: x['laugh_count'])
    
    # 時間を正規化
    df['time_normalized'] = (df['timestamp'] - df['timestamp'].min()) / \
                            (df['timestamp'].max() - df['timestamp'].min()) * 100
    df['time_bin'] = pd.cut(df['time_normalized'], bins=20, labels=False)
    
    # 時間ビンごとの感情表現率
    emotion_timeline = df.groupby('time_bin').agg({
        'emoji_count': 'sum',
        'exclamation_count': 'sum',
        'laugh_count': 'sum',
        'comment': 'count'
    })
    
    emotion_timeline['emoji_rate'] = emotion_timeline['emoji_count'] / emotion_timeline['comment']
    emotion_timeline['exclamation_rate'] = emotion_timeline['exclamation_count'] / emotion_timeline['comment']
    emotion_timeline['laugh_rate'] = emotion_timeline['laugh_count'] / emotion_timeline['comment']
    
    # 可視化
    fig, ax = plt.subplots(figsize=(14, 6))
    
    ax.plot(emotion_timeline.index, emotion_timeline['emoji_rate'], 
            marker='o', linewidth=2.5, label='Emoji Rate', color='#FF6B6B')
    ax.plot(emotion_timeline.index, emotion_timeline['exclamation_rate'], 
            marker='s', linewidth=2.5, label='Exclamation Rate', color='#4ECDC4')
    ax.plot(emotion_timeline.index, emotion_timeline['laugh_rate'], 
            marker='^', linewidth=2.5, label='Laugh Rate', color='#FFE66D')
    
    ax.set_xlabel('Match Progress (20 Time Bins)', fontsize=14, fontweight='bold')
    ax.set_ylabel('Emotion Expression Rate', fontsize=14, fontweight='bold')
    ax.set_title('Emotion Expression Timeline', fontsize=16, fontweight='bold', pad=20)
    ax.legend(fontsize=12, loc='upper right')
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'emotion_timeline.png'), 
                dpi=300, bbox_inches='tight')
    print(f"✅ Saved: emotion_timeline.png")
    plt.close()
    
    # CSV保存
    emotion_timeline.to_csv(os.path.join(OUTPUT_DIR, 'emotion_timeline.csv'))
    print(f"✅ Saved: emotion_timeline.csv")
    
    return emotion_timeline

# ==================== 国別時間パターン比較 ====================
def compare_country_temporal_patterns(df):
    """国別の時間的パターンを比較"""
    print("\n🌍 Comparing country temporal patterns...")
    
    # 時間を正規化
    df['time_normalized'] = (df['timestamp'] - df['timestamp'].min()) / \
                            (df['timestamp'].max() - df['timestamp'].min()) * 100
    df['time_bin'] = pd.cut(df['time_normalized'], bins=20, labels=False)
    
    # 国別・時間ビン別のコメント数
    country_time = df.groupby(['country', 'time_bin']).size().unstack(fill_value=0)
    
    # 正規化 (各国を0-1にスケール)
    country_time_norm = country_time.div(country_time.sum(axis=1), axis=0)
    
    # ヒートマップ
    fig, ax = plt.subplots(figsize=(16, 6))
    sns.heatmap(country_time_norm, cmap='YlOrRd', annot=False, 
                fmt='.2f', cbar_kws={'label': 'Normalized Comment Density'},
                ax=ax, linewidths=0.5)
    ax.set_xlabel('Time Bin (Match Progress)', fontsize=14, fontweight='bold')
    ax.set_ylabel('Country', fontsize=14, fontweight='bold')
    ax.set_title('Country Temporal Pattern Heatmap', fontsize=16, fontweight='bold', pad=20)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'country_temporal_heatmap.png'), 
                dpi=300, bbox_inches='tight')
    print(f"✅ Saved: country_temporal_heatmap.png")
    plt.close()
    
    # CSV保存
    country_time_norm.to_csv(os.path.join(OUTPUT_DIR, 'country_temporal_patterns.csv'))
    print(f"✅ Saved: country_temporal_patterns.csv")
    
    return country_time_norm

# ==================== メイン実行 ====================
def main():
    print("="*80)
    print("⏱️  Temporal Analysis - Football-Only (9 Streams, 4 Countries)")
    print("="*80)
    
    # 1. データ読み込み
    df = load_football_data()
    
    # 2. コメント密度分析
    overall_density, country_density = analyze_comment_density(df)
    
    # 3. バースト検出
    burst_df = detect_bursts(df)
    
    # 4. 感情表現の時系列
    emotion_timeline = analyze_emotion_timeline(df)
    
    # 5. 国別時間パターン
    country_patterns = compare_country_temporal_patterns(df)
    
    # サマリー
    print("\n" + "="*80)
    print("📊 TEMPORAL ANALYSIS SUMMARY")
    print("="*80)
    print(f"Total comments: {len(df)}")
    print(f"Time range: {df['timestamp'].min():.1f} - {df['timestamp'].max():.1f}")
    print(f"Bursts detected: {len(burst_df)}")
    print(f"\nTop 3 bursts:")
    print(burst_df.nlargest(3, 'Peak_Height')[['Burst_ID', 'Time_Percent', 'Peak_Height']])
    
    print("\n" + "="*80)
    print("✅ Temporal Analysis Complete!")
    print(f"📁 Output saved to: {OUTPUT_DIR}/")
    print("="*80)

if __name__ == '__main__':
    main()
