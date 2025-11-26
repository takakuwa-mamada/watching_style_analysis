"""
全試合総合分析 - 6試合31配信の包括的な文化分析
All Matches Comprehensive Analysis

目的:
1. 6試合31配信で全分析を実行
2. 試合間・国別・言語別の文化差を検出
3. エンゲージメントパターンの統合分析

データセット:
- 6試合: レアルマドリードvsバルセロナ, ブラジルvs日本, ブライトンvsマンチェスターシティ,
         リーズユナイテッドvsスパーズ, レアルソシエダvsレアルマドリード, パリサンジェルマンvsインテルマイアミ
- 31配信
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
from pathlib import Path
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

# データ設定
DATA_BASE_DIR = Path('data/football')
OUTPUT_DIR = 'output/all_matches_comprehensive'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 6試合のフォルダマッピング
MATCH_FOLDERS = {
    'レアルマドリードvsバルセロナ': {'importance': 'Tier1', 'league': 'LaLiga'},
    'ブラジルvs日本': {'importance': 'Tier2', 'league': 'International'},
    'ブライトンvsマンチェスターシティ': {'importance': 'Tier3', 'league': 'Premier'},
    'リーズユナイテッドvsスパーズ': {'importance': 'Tier3', 'league': 'Premier'},
    'レアルソシエダvsレアルマドリード': {'importance': 'Tier3', 'league': 'LaLiga'},
    'パリサンジェルマンvsインテルマイアミ': {'importance': 'Tier4', 'league': 'Friendly'}
}

def load_all_streams():
    """全31配信のデータを読み込む"""
    all_data = []
    stream_count = 0
    
    print("\n" + "="*80)
    print("📂 Loading all 31 streams from 6 matches...")
    print("="*80)
    
    for match_folder, match_info in MATCH_FOLDERS.items():
        match_path = DATA_BASE_DIR / match_folder
        
        if not match_path.exists():
            print(f"⚠️  Warning: {match_folder} not found, skipping...")
            continue
        
        print(f"\n📁 {match_folder} ({match_info['importance']})")
        
        csv_files = list(match_path.glob('*_chat_log.csv'))
        
        for csv_file in csv_files:
            try:
                df = pd.read_csv(csv_file, encoding='utf-8')
                
                # テキストカラムを探す
                text_col = None
                for col in ['message', 'text', 'comment', 'body']:
                    if col in df.columns:
                        text_col = col
                        break
                
                if text_col is None:
                    print(f"  ⚠️  No text column in {csv_file.name}")
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
                df_stream['match'] = match_folder
                df_stream['stream_name'] = csv_file.stem.replace('_chat_log', '')
                df_stream['importance'] = match_info['importance']
                df_stream['league'] = match_info['league']
                
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
                
                all_data.append(df_stream)
                stream_count += 1
                print(f"  ✅ {csv_file.name}: {len(df_stream):,} comments")
                
            except Exception as e:
                print(f"  ❌ Error loading {csv_file.name}: {e}")
    
    if not all_data:
        raise ValueError("No data loaded!")
    
    combined = pd.concat(all_data, ignore_index=True)
    print(f"\n📊 Total: {len(combined):,} comments from {stream_count} streams")
    print(f"Matches: {combined['match'].nunique()}")
    print(f"Importance tiers: {combined['importance'].unique()}")
    
    return combined

def analyze_emoji_usage(text):
    """絵文字使用率を分析"""
    if pd.isna(text):
        return 0
    emoji_count = len([c for c in str(text) if c in emoji.EMOJI_DATA])
    return emoji_count

def analyze_laugh_expression(text):
    """笑いの表現を分析"""
    if pd.isna(text):
        return 0
    text = str(text).lower()
    laugh_patterns = ['w', 'lol', 'haha', 'jaja', 'kkkk', '笑', 'wwww']
    laugh_count = sum([1 for pattern in laugh_patterns if pattern in text])
    return min(laugh_count, 1)  # 0 or 1

def analyze_exclamation(text):
    """感嘆符の使用を分析"""
    if pd.isna(text):
        return 0
    return str(text).count('!')

def calculate_stream_metrics(df_stream):
    """配信単位のメトリクスを計算"""
    comments = df_stream['comment'].tolist()
    
    # 基本統計
    total_comments = len(comments)
    
    # 絵文字率
    emoji_counts = df_stream['comment'].apply(analyze_emoji_usage)
    emoji_rate = (emoji_counts > 0).sum() / total_comments * 100 if total_comments > 0 else 0
    
    # 笑い率
    laugh_counts = df_stream['comment'].apply(analyze_laugh_expression)
    laugh_rate = laugh_counts.sum() / total_comments * 100 if total_comments > 0 else 0
    
    # 感嘆符率
    exclamation_counts = df_stream['comment'].apply(analyze_exclamation)
    exclamation_rate = (exclamation_counts > 0).sum() / total_comments * 100 if total_comments > 0 else 0
    
    # コメント長
    comment_lengths = df_stream['comment'].str.len()
    mean_length = comment_lengths.mean()
    
    # CPM計算
    if 'time_seconds' in df_stream.columns:
        time_span = df_stream['time_seconds'].max() - df_stream['time_seconds'].min()
        cpm = (total_comments / time_span) * 60 if time_span > 0 else 0
    else:
        cpm = 0
    
    return {
        'total_comments': total_comments,
        'emoji_rate': emoji_rate,
        'laugh_rate': laugh_rate,
        'exclamation_rate': exclamation_rate,
        'mean_comment_length': mean_length,
        'cpm': cpm
    }

def main():
    print("="*80)
    print("🌍 All Matches Comprehensive Analysis - 6 Matches, 31 Streams")
    print("="*80)
    
    # 1. データ読み込み
    df_all = load_all_streams()
    
    # 2. 配信単位の分析
    print("\n" + "="*80)
    print("📊 Analyzing stream-level metrics...")
    print("="*80)
    
    stream_results = []
    
    for (match, stream_name), df_stream in df_all.groupby(['match', 'stream_name']):
        metrics = calculate_stream_metrics(df_stream)
        metrics['match'] = match
        metrics['stream_name'] = stream_name
        metrics['importance'] = df_stream['importance'].iloc[0]
        metrics['league'] = df_stream['league'].iloc[0]
        stream_results.append(metrics)
        
        print(f"  ✅ {stream_name[:50]}: {metrics['total_comments']:,} comments, "
              f"emoji={metrics['emoji_rate']:.1f}%, CPM={metrics['cpm']:.1f}")
    
    df_results = pd.DataFrame(stream_results)
    
    # 3. CSV保存
    output_file = os.path.join(OUTPUT_DIR, 'all_matches_stream_metrics.csv')
    df_results.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n✅ Saved: {output_file}")
    
    # 4. 統計サマリー
    print("\n" + "="*80)
    print("📈 Statistical Summary by Importance Tier")
    print("="*80)
    
    for tier in sorted(df_results['importance'].unique()):
        tier_data = df_results[df_results['importance'] == tier]
        print(f"\n{tier}:")
        print(f"  Streams: {len(tier_data)}")
        print(f"  Avg emoji rate: {tier_data['emoji_rate'].mean():.2f}%")
        print(f"  Avg CPM: {tier_data['cpm'].mean():.2f}")
        print(f"  Avg comment length: {tier_data['mean_comment_length'].mean():.2f}")
    
    # 5. 可視化
    print("\n" + "="*80)
    print("📊 Creating visualizations...")
    print("="*80)
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # Emoji rate by importance
    sns.boxplot(data=df_results, x='importance', y='emoji_rate', ax=axes[0, 0])
    axes[0, 0].set_title('Emoji Rate by Importance Tier', fontweight='bold')
    axes[0, 0].set_ylabel('Emoji Rate (%)')
    
    # CPM by importance
    sns.boxplot(data=df_results, x='importance', y='cpm', ax=axes[0, 1])
    axes[0, 1].set_title('CPM by Importance Tier', fontweight='bold')
    axes[0, 1].set_ylabel('Comments Per Minute')
    
    # Comment length by league
    sns.boxplot(data=df_results, x='league', y='mean_comment_length', ax=axes[1, 0])
    axes[1, 0].set_title('Comment Length by League', fontweight='bold')
    axes[1, 0].set_ylabel('Mean Comment Length')
    axes[1, 0].tick_params(axis='x', rotation=45)
    
    # Laugh rate by importance
    sns.boxplot(data=df_results, x='importance', y='laugh_rate', ax=axes[1, 1])
    axes[1, 1].set_title('Laugh Expression Rate by Importance', fontweight='bold')
    axes[1, 1].set_ylabel('Laugh Rate (%)')
    
    plt.tight_layout()
    viz_file = os.path.join(OUTPUT_DIR, 'all_matches_comparison.png')
    plt.savefig(viz_file, dpi=300, bbox_inches='tight')
    print(f"✅ Saved: {viz_file}")
    plt.close()
    
    # 6. サマリーレポート作成
    print("\n" + "="*80)
    print("📝 Creating summary report...")
    print("="*80)
    
    report = f"""# 全試合総合分析レポート

**分析日時**: {pd.Timestamp.now().strftime('%Y年%m月%d日 %H:%M')}
**データ規模**: 6試合、{len(df_results)}配信、{len(df_all):,}コメント

---

## 📊 試合別サマリー

"""
    
    for match in MATCH_FOLDERS.keys():
        match_data = df_results[df_results['match'] == match]
        if len(match_data) > 0:
            report += f"""
### {match}
- **配信数**: {len(match_data)}
- **重要度**: {match_data['importance'].iloc[0]}
- **リーグ**: {match_data['league'].iloc[0]}
- **総コメント数**: {match_data['total_comments'].sum():,}
- **平均絵文字率**: {match_data['emoji_rate'].mean():.2f}%
- **平均CPM**: {match_data['cpm'].mean():.2f}

"""
    
    report += """
---

## 📈 重要度別統計

"""
    
    for tier in sorted(df_results['importance'].unique()):
        tier_data = df_results[df_results['importance'] == tier]
        report += f"""
### {tier}
- **配信数**: {len(tier_data)}
- **平均絵文字率**: {tier_data['emoji_rate'].mean():.2f}%
- **平均笑い率**: {tier_data['laugh_rate'].mean():.2f}%
- **平均感嘆符率**: {tier_data['exclamation_rate'].mean():.2f}%
- **平均コメント長**: {tier_data['mean_comment_length'].mean():.2f}文字
- **平均CPM**: {tier_data['cpm'].mean():.2f}

"""
    
    report_file = os.path.join(OUTPUT_DIR, 'ALL_MATCHES_SUMMARY.md')
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"✅ Saved: {report_file}")
    
    print("\n" + "="*80)
    print("✅ All Matches Comprehensive Analysis Complete!")
    print(f"📁 Output directory: {OUTPUT_DIR}/")
    print("="*80)

if __name__ == '__main__':
    main()
