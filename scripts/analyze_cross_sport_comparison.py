#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
スポーツ種目間比較分析：サッカー vs 野球

仮説:
- H4: スポーツの特性（連続性 vs 区切り）がコメントパターンに影響
- H5: サッカーは流動的なバースト、野球は離散的なバースト
- H6: 野球ファンはより分析的なコメント（平均文字数が長い）

比較軸:
1. バースト分布パターン（連続 vs 離散）
2. コメント間隔の分散
3. 平均コメント長（感情的 vs 分析的）
4. トピック内容（戦術用語の出現率）
"""

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# 日本語フォント設定
plt.rcParams['font.sans-serif'] = ['Yu Gothic', 'Meiryo', 'MS Gothic']
plt.rcParams['axes.unicode_minus'] = False

# パス設定
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output" / "cross_sport_comparison"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 80)
print("スポーツ種目間比較分析 - Cross-Sport Comparison (Soccer vs Baseball)")
print("=" * 80)


def load_sport_data(sport_type):
    """スポーツ種別のデータを読み込む"""
    if sport_type == 'soccer':
        data_dir = DATA_DIR / "football"
    elif sport_type == 'baseball':
        data_dir = DATA_DIR / "baseball"
    else:
        return None
    
    if not data_dir.exists():
        print(f"⚠ {sport_type}フォルダが存在しません: {data_dir}")
        return None
    
    all_comments = []
    
    for match_folder in data_dir.iterdir():
        if not match_folder.is_dir():
            continue
        
        csv_files = list(match_folder.glob("*.csv"))
        
        for csv_file in csv_files:
            try:
                df = pd.read_csv(csv_file, encoding='utf-8-sig')
                
                # カラム名正規化
                if 'message' in df.columns and 'comment' not in df.columns:
                    df.rename(columns={'message': 'comment'}, inplace=True)
                
                if 'comment' in df.columns:
                    df['sport'] = sport_type
                    df['match_folder'] = match_folder.name
                    df['stream_name'] = csv_file.stem
                    all_comments.append(df)
            except Exception as e:
                print(f"  ⚠ エラー: {csv_file.name} - {e}")
    
    if all_comments:
        combined = pd.concat(all_comments, ignore_index=True)
        print(f"✓ {sport_type.upper()}: {len(csv_files)} 配信, {len(combined):,} コメント")
        return combined
    
    return None


def calculate_burst_patterns(df, sport_type):
    """バーストパターンを分析"""
    if 'timestamp' not in df.columns:
        return None
    
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df_sorted = df.dropna(subset=['timestamp']).sort_values('timestamp')
    
    if len(df_sorted) == 0:
        return None
    
    # 1分ごとのコメント数
    df_sorted['minute'] = df_sorted['timestamp'].dt.floor('1min')
    comments_per_minute = df_sorted.groupby('minute').size()
    
    # バースト検出
    mean_cpm = comments_per_minute.mean()
    std_cpm = comments_per_minute.std()
    threshold = mean_cpm + std_cpm
    
    burst_minutes = comments_per_minute[comments_per_minute > threshold]
    
    # バースト間隔の分析
    burst_intervals = []
    if len(burst_minutes) > 1:
        burst_times = burst_minutes.index
        for i in range(len(burst_times) - 1):
            interval = (burst_times[i+1] - burst_times[i]).total_seconds() / 60
            burst_intervals.append(interval)
    
    result = {
        'sport': sport_type,
        'total_minutes': len(comments_per_minute),
        'burst_count': len(burst_minutes),
        'burst_frequency': len(burst_minutes) / len(comments_per_minute) if len(comments_per_minute) > 0 else 0,
        'mean_cpm': mean_cpm,
        'std_cpm': std_cpm,
        'max_cpm': comments_per_minute.max(),
        'median_cpm': comments_per_minute.median(),
        'cv_cpm': std_cpm / mean_cpm if mean_cpm > 0 else 0,  # 変動係数
        'mean_burst_interval': np.mean(burst_intervals) if burst_intervals else np.nan,
        'std_burst_interval': np.std(burst_intervals) if burst_intervals else np.nan
    }
    
    return result, comments_per_minute


def analyze_comment_characteristics(df, sport_type):
    """コメントの特徴を分析"""
    result = {
        'sport': sport_type,
        'total_comments': len(df),
        'unique_users': df['author'].nunique() if 'author' in df.columns else np.nan
    }
    
    # コメント長
    df['comment_length'] = df['comment'].str.len()
    result['mean_length'] = df['comment_length'].mean()
    result['median_length'] = df['comment_length'].median()
    result['std_length'] = df['comment_length'].std()
    
    # 感情表現
    df['has_emoji'] = df['comment'].str.contains(
        r'[\U0001F000-\U0001F9FF]|[\u2600-\u27BF]|[\u2B50]|[\u26BD]|[\u26A1]',
        regex=True, na=False
    )
    result['emoji_rate'] = df['has_emoji'].mean() * 100
    
    df['has_exclamation'] = df['comment'].str.contains('!|！', regex=True, na=False)
    result['exclamation_rate'] = df['has_exclamation'].mean() * 100
    
    # 戦術用語の出現率（スポーツ別）
    if sport_type == 'soccer':
        tactical_terms = ['offside', 'corner', 'penalty', 'formation', 'tactics', 'press', 
                         'オフサイド', 'コーナー', 'ペナルティ', 'フォーメーション', '戦術']
    elif sport_type == 'baseball':
        tactical_terms = ['strike', 'ball', 'out', 'home run', 'pitch', 'batting',
                         'ストライク', 'ボール', 'アウト', 'ホームラン', '投球', '打撃']
    
    tactical_pattern = '|'.join(tactical_terms)
    df['has_tactical'] = df['comment'].str.contains(tactical_pattern, case=False, regex=True, na=False)
    result['tactical_term_rate'] = df['has_tactical'].mean() * 100
    
    return result


def compare_sports(soccer_df, baseball_df):
    """2つのスポーツを統計的に比較"""
    print("\n" + "=" * 80)
    print("スポーツ種目間の統計的比較...")
    print("=" * 80)
    
    results = []
    
    # バーストパターン比較
    print("\n📊 バーストパターン分析...")
    soccer_burst, soccer_cpm = calculate_burst_patterns(soccer_df, 'soccer')
    baseball_burst, baseball_cpm = calculate_burst_patterns(baseball_df, 'baseball')
    
    if soccer_burst and baseball_burst:
        print(f"\nサッカー:")
        print(f"  バースト頻度: {soccer_burst['burst_frequency']:.3f}")
        print(f"  平均バースト間隔: {soccer_burst['mean_burst_interval']:.1f}分")
        print(f"  CPM変動係数: {soccer_burst['cv_cpm']:.3f}")
        
        print(f"\n野球:")
        print(f"  バースト頻度: {baseball_burst['burst_frequency']:.3f}")
        print(f"  平均バースト間隔: {baseball_burst['mean_burst_interval']:.1f}分")
        print(f"  CPM変動係数: {baseball_burst['cv_cpm']:.3f}")
        
        # Mann-Whitney U検定
        u_stat, p_value = stats.mannwhitneyu(soccer_cpm, baseball_cpm, alternative='two-sided')
        print(f"\nCPM分布の差: U={u_stat:.0f}, p={p_value:.4f}")
        
        results.append({
            'comparison': 'Burst Frequency',
            'soccer_value': soccer_burst['burst_frequency'],
            'baseball_value': baseball_burst['burst_frequency'],
            'test': 'Descriptive',
            'p_value': np.nan
        })
    
    # コメント特徴比較
    print("\n📊 コメント特徴分析...")
    soccer_char = analyze_comment_characteristics(soccer_df, 'soccer')
    baseball_char = analyze_comment_characteristics(baseball_df, 'baseball')
    
    print(f"\nサッカー:")
    print(f"  平均コメント長: {soccer_char['mean_length']:.1f}文字")
    print(f"  絵文字率: {soccer_char['emoji_rate']:.2f}%")
    print(f"  戦術用語率: {soccer_char['tactical_term_rate']:.2f}%")
    
    print(f"\n野球:")
    print(f"  平均コメント長: {baseball_char['mean_length']:.1f}文字")
    print(f"  絵文字率: {baseball_char['emoji_rate']:.2f}%")
    print(f"  戦術用語率: {baseball_char['tactical_term_rate']:.2f}%")
    
    # コメント長の比較
    soccer_lengths = soccer_df['comment'].str.len().dropna()
    baseball_lengths = baseball_df['comment'].str.len().dropna()
    u_stat, p_value = stats.mannwhitneyu(soccer_lengths, baseball_lengths, alternative='two-sided')
    
    mean_diff = soccer_lengths.mean() - baseball_lengths.mean()
    pooled_std = np.sqrt((soccer_lengths.std()**2 + baseball_lengths.std()**2) / 2)
    cohens_d = mean_diff / pooled_std if pooled_std > 0 else np.nan
    
    print(f"\nコメント長の差: U={u_stat:.0f}, p={p_value:.4f}, Cohen's d={cohens_d:.3f}")
    
    results.append({
        'comparison': 'Comment Length',
        'soccer_value': soccer_char['mean_length'],
        'baseball_value': baseball_char['mean_length'],
        'test': 'Mann-Whitney U',
        'p_value': p_value,
        'cohens_d': cohens_d
    })
    
    # 結果をデータフレーム化
    results_df = pd.DataFrame(results)
    output_path = OUTPUT_DIR / "cross_sport_comparison_stats.csv"
    results_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"\n✓ 統計比較結果保存: {output_path}")
    
    return results_df, (soccer_burst, baseball_burst), (soccer_char, baseball_char)


def create_visualizations(soccer_df, baseball_df, soccer_cpm, baseball_cpm):
    """可視化を作成"""
    print("\n" + "=" * 80)
    print("可視化作成中...")
    print("=" * 80)
    
    # 図1: CPM分布の比較
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # ヒストグラム
    ax1 = axes[0]
    ax1.hist(soccer_cpm, bins=50, alpha=0.6, label='サッカー', color='green', density=True)
    ax1.hist(baseball_cpm, bins=50, alpha=0.6, label='野球', color='blue', density=True)
    ax1.set_xlabel('Comments per Minute', fontsize=11)
    ax1.set_ylabel('Density', fontsize=11)
    ax1.set_title('CPM分布の比較', fontsize=12, fontweight='bold')
    ax1.legend()
    ax1.grid(alpha=0.3)
    
    # ボックスプロット
    ax2 = axes[1]
    data_to_plot = [soccer_cpm, baseball_cpm]
    bp = ax2.boxplot(data_to_plot, labels=['サッカー', '野球'], patch_artist=True)
    bp['boxes'][0].set_facecolor('green')
    bp['boxes'][0].set_alpha(0.6)
    bp['boxes'][1].set_facecolor('blue')
    bp['boxes'][1].set_alpha(0.6)
    ax2.set_ylabel('Comments per Minute', fontsize=11)
    ax2.set_title('CPMのボックスプロット', fontsize=12, fontweight='bold')
    ax2.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    output_path = OUTPUT_DIR / "cpm_distribution_comparison.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  ✓ CPM分布保存: {output_path.name}")
    plt.close()
    
    # 図2: コメント長分布
    fig, ax = plt.subplots(figsize=(10, 6))
    
    soccer_lengths = soccer_df['comment'].str.len().dropna()
    baseball_lengths = baseball_df['comment'].str.len().dropna()
    
    ax.hist(soccer_lengths, bins=100, range=(0, 200), alpha=0.6, label='サッカー', color='green', density=True)
    ax.hist(baseball_lengths, bins=100, range=(0, 200), alpha=0.6, label='野球', color='blue', density=True)
    ax.set_xlabel('コメント長（文字数）', fontsize=11)
    ax.set_ylabel('Density', fontsize=11)
    ax.set_title('コメント長の分布比較', fontsize=12, fontweight='bold')
    ax.legend()
    ax.grid(alpha=0.3)
    
    plt.tight_layout()
    output_path = OUTPUT_DIR / "comment_length_comparison.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  ✓ コメント長分布保存: {output_path.name}")
    plt.close()
    
    print("\n✓ 全可視化完了")


def create_summary_report(stats_df, soccer_burst, baseball_burst, soccer_char, baseball_char):
    """サマリーレポート作成"""
    report = []
    report.append("# スポーツ種目間比較分析レポート\n\n")
    report.append(f"**分析日時**: {pd.Timestamp.now().strftime('%Y年%m月%d日 %H:%M')}\n")
    report.append(f"**比較対象**: サッカー vs 野球\n\n")
    report.append("---\n\n")
    
    # 仮説検証
    report.append("## 🎯 仮説検証\n\n")
    
    report.append("### H4: スポーツ特性とコメントパターン\n\n")
    if soccer_burst and baseball_burst:
        cv_diff = soccer_burst['cv_cpm'] - baseball_burst['cv_cpm']
        if cv_diff > 0:
            report.append(f"✅ **支持**: サッカーのCPM変動係数({soccer_burst['cv_cpm']:.3f})は野球({baseball_burst['cv_cpm']:.3f})より**{abs(cv_diff):.3f}高く**、より不規則なバーストパターンを示す。\n\n")
        else:
            report.append(f"❌ **非支持**: 野球のCPM変動係数が高く、仮説と逆の結果。\n\n")
    
    report.append("### H5: バースト分布パターン\n\n")
    if soccer_burst and baseball_burst:
        if soccer_burst['mean_burst_interval'] < baseball_burst['mean_burst_interval']:
            report.append(f"✅ **部分的支持**: サッカーの平均バースト間隔({soccer_burst['mean_burst_interval']:.1f}分)は野球({baseball_burst['mean_burst_interval']:.1f}分)より短く、より頻繁なバーストを示す。\n\n")
        else:
            report.append(f"❌ **非支持**: 野球の方がバースト間隔が短い。\n\n")
    
    report.append("### H6: コメントの分析性\n\n")
    if soccer_char and baseball_char:
        length_diff = baseball_char['mean_length'] - soccer_char['mean_length']
        if length_diff > 0:
            report.append(f"✅ **支持**: 野球の平均コメント長({baseball_char['mean_length']:.1f}文字)はサッカー({soccer_char['mean_length']:.1f}文字)より**{length_diff:.1f}文字長く**、より分析的なコメントが多い。\n\n")
        else:
            report.append(f"❌ **非支持**: サッカーの方がコメントが長い。\n\n")
    
    # 保存
    output_path = OUTPUT_DIR / "CROSS_SPORT_COMPARISON_SUMMARY.md"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(report)
    
    print(f"\n✓ サマリーレポート保存: {output_path}")
    print("\n" + "".join(report))


def main():
    """メイン実行関数"""
    print("\n🚀 スポーツ種目間比較分析開始\n")
    
    # 1. データ読み込み
    print("\n📂 データ読み込み中...")
    soccer_df = load_sport_data('soccer')
    baseball_df = load_sport_data('baseball')
    
    if soccer_df is None or baseball_df is None:
        print("⚠ データが不足しています")
        return
    
    # 2. 統計比較
    stats_df, (soccer_burst, baseball_burst), (soccer_char, baseball_char) = compare_sports(soccer_df, baseball_df)
    
    # 3. CPMデータの取得
    _, soccer_cpm = calculate_burst_patterns(soccer_df, 'soccer')
    _, baseball_cpm = calculate_burst_patterns(baseball_df, 'baseball')
    
    # 4. 可視化
    create_visualizations(soccer_df, baseball_df, soccer_cpm, baseball_cpm)
    
    # 5. サマリーレポート
    create_summary_report(stats_df, soccer_burst, baseball_burst, soccer_char, baseball_char)
    
    print("\n" + "=" * 80)
    print("✅ スポーツ種目間比較分析完了!")
    print("=" * 80)
    print(f"\n📁 出力ディレクトリ: {OUTPUT_DIR}")
    print("\n生成されたファイル:")
    for file in sorted(OUTPUT_DIR.glob("*")):
        print(f"  - {file.name}")
    print()


if __name__ == "__main__":
    main()
