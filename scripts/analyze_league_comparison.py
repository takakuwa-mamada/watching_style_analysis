#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
リーグ比較分析：プレミアリーグ vs ラ・リーガ

仮説:
- H7: リーグ文化がファン行動に影響
- H8: プレミアリーグ（英語圏）はより分析的、ラ・リーガ（スペイン語圏）はより感情的

比較対象:
- プレミアリーグ: ブライトン vs マンC、リーズ vs スパーズ（英語配信のみ）
- ラ・リーガ: エル・クラシコ、ソシエダ vs マドリード（スペイン語配信のみ）
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
OUTPUT_DIR = BASE_DIR / "output" / "league_comparison"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 80)
print("リーグ比較分析 - League Comparison (Premier League vs La Liga)")
print("=" * 80)


# リーグ定義
LEAGUE_MATCHES = {
    'Premier League': [
        'ブライトンvsマンチェスターシティ',
        'リーズユナイテッドvsスパーズ'
    ],
    'La Liga': [
        'レアルマドリードvsバルセロナ',
        'レアルソシエダvsレアルマドリード'
    ]
}


def detect_stream_language(stream_name):
    """配信名から言語を検出"""
    # 英語
    if any(word in stream_name.lower() for word in ['watch', 'live', 'premier', 'league']):
        if not any(char in stream_name for char in ['【', '】']):
            return 'English'
    
    # スペイン語
    if any(word in stream_name.lower() for word in ['directo', 'vivo', 'minuto', 'clásico']):
        return 'Spanish'
    
    # 日本語
    if any(char in stream_name for char in ['【', '】', '配信', '同時視聴']):
        return 'Japanese'
    
    return 'Unknown'


def load_league_data(league_name):
    """リーグ別のデータを読み込む"""
    match_folders = LEAGUE_MATCHES[league_name]
    all_comments = []
    stream_count = 0
    
    for match_folder in match_folders:
        folder_path = DATA_DIR / "football" / match_folder
        
        if not folder_path.exists():
            print(f"  ⚠ フォルダが存在しません: {match_folder}")
            continue
        
        csv_files = list(folder_path.glob("*.csv"))
        
        for csv_file in csv_files:
            try:
                df = pd.read_csv(csv_file, encoding='utf-8-sig')
                
                # カラム名正規化
                if 'message' in df.columns and 'comment' not in df.columns:
                    df.rename(columns={'message': 'comment'}, inplace=True)
                
                if 'comment' in df.columns:
                    df['league'] = league_name
                    df['match_folder'] = match_folder
                    df['stream_name'] = csv_file.stem
                    df['detected_language'] = detect_stream_language(csv_file.stem)
                    
                    # リーグに対応する言語のみを抽出
                    if league_name == 'Premier League' and df['detected_language'].iloc[0] == 'English':
                        all_comments.append(df)
                        stream_count += 1
                    elif league_name == 'La Liga' and df['detected_language'].iloc[0] == 'Spanish':
                        all_comments.append(df)
                        stream_count += 1
                        
            except Exception as e:
                print(f"  ⚠ エラー: {csv_file.name} - {e}")
    
    if all_comments:
        combined = pd.concat(all_comments, ignore_index=True)
        print(f"✓ {league_name}: {stream_count} 配信, {len(combined):,} コメント")
        return combined
    
    print(f"⚠ {league_name}: データなし")
    return None


def analyze_league_characteristics(df, league_name):
    """リーグの特徴を分析"""
    result = {
        'league': league_name,
        'total_comments': len(df),
        'unique_streams': df['stream_name'].nunique() if 'stream_name' in df.columns else 0
    }
    
    # コメント長
    df['comment_length'] = df['comment'].str.len()
    result['mean_length'] = df['comment_length'].mean()
    result['median_length'] = df['comment_length'].median()
    
    # 感情表現
    df['has_emoji'] = df['comment'].str.contains(
        r'[\U0001F000-\U0001F9FF]|[\u2600-\u27BF]|[\u2B50]|[\u26BD]',
        regex=True, na=False
    )
    result['emoji_rate'] = df['has_emoji'].mean() * 100
    
    df['has_exclamation'] = df['comment'].str.contains('!|！', regex=True, na=False)
    result['exclamation_rate'] = df['has_exclamation'].mean() * 100
    
    # 戦術用語（リーグ別）
    if league_name == 'Premier League':
        tactical_terms = ['offside', 'corner', 'penalty', 'formation', 'tactics', 'press', 'counter']
    elif league_name == 'La Liga':
        tactical_terms = ['fuera de juego', 'córner', 'penalti', 'táctica', 'formación', 'gol']
    
    tactical_pattern = '|'.join(tactical_terms)
    df['has_tactical'] = df['comment'].str.contains(tactical_pattern, case=False, regex=True, na=False)
    result['tactical_term_rate'] = df['has_tactical'].mean() * 100
    
    # チャント文化（ラ・リーガ特有）
    if league_name == 'La Liga':
        chant_terms = ['olé', 'vamos', 'arriba', 'hala']
        chant_pattern = '|'.join(chant_terms)
        df['has_chant'] = df['comment'].str.contains(chant_pattern, case=False, regex=True, na=False)
        result['chant_rate'] = df['has_chant'].mean() * 100
    else:
        result['chant_rate'] = np.nan
    
    return result


def compare_leagues(premier_df, laliga_df):
    """2つのリーグを統計的に比較"""
    print("\n" + "=" * 80)
    print("リーグ間の統計的比較...")
    print("=" * 80)
    
    results = []
    
    # 特徴分析
    premier_char = analyze_league_characteristics(premier_df, 'Premier League')
    laliga_char = analyze_league_characteristics(laliga_df, 'La Liga')
    
    print(f"\nプレミアリーグ:")
    print(f"  配信数: {premier_char['unique_streams']}")
    print(f"  平均コメント長: {premier_char['mean_length']:.1f}文字")
    print(f"  絵文字率: {premier_char['emoji_rate']:.2f}%")
    print(f"  感嘆符率: {premier_char['exclamation_rate']:.2f}%")
    print(f"  戦術用語率: {premier_char['tactical_term_rate']:.2f}%")
    
    print(f"\nラ・リーガ:")
    print(f"  配信数: {laliga_char['unique_streams']}")
    print(f"  平均コメント長: {laliga_char['mean_length']:.1f}文字")
    print(f"  絵文字率: {laliga_char['emoji_rate']:.2f}%")
    print(f"  感嘆符率: {laliga_char['exclamation_rate']:.2f}%")
    print(f"  戦術用語率: {laliga_char['tactical_term_rate']:.2f}%")
    print(f"  チャント率: {laliga_char['chant_rate']:.2f}%")
    
    # 統計検定
    print("\n📊 統計検定:")
    
    # コメント長
    premier_lengths = premier_df['comment'].str.len().dropna()
    laliga_lengths = laliga_df['comment'].str.len().dropna()
    u_stat, p_value = stats.mannwhitneyu(premier_lengths, laliga_lengths, alternative='two-sided')
    
    mean_diff = premier_lengths.mean() - laliga_lengths.mean()
    pooled_std = np.sqrt((premier_lengths.std()**2 + laliga_lengths.std()**2) / 2)
    cohens_d = mean_diff / pooled_std if pooled_std > 0 else np.nan
    
    print(f"  コメント長: U={u_stat:.0f}, p={p_value:.4f}, d={cohens_d:.3f}")
    
    results.append({
        'metric': 'Comment Length',
        'premier_value': premier_char['mean_length'],
        'laliga_value': laliga_char['mean_length'],
        'mann_whitney_u': u_stat,
        'p_value': p_value,
        'cohens_d': cohens_d
    })
    
    # 絵文字率（サンプルベース）
    premier_emoji = premier_df['comment'].str.contains(
        r'[\U0001F000-\U0001F9FF]|[\u2600-\u27BF]', regex=True, na=False
    ).astype(int)
    laliga_emoji = laliga_df['comment'].str.contains(
        r'[\U0001F000-\U0001F9FF]|[\u2600-\u27BF]', regex=True, na=False
    ).astype(int)
    
    # サンプリング（大きすぎる場合）
    if len(premier_emoji) > 10000:
        premier_emoji = premier_emoji.sample(10000, random_state=42)
    if len(laliga_emoji) > 10000:
        laliga_emoji = laliga_emoji.sample(10000, random_state=42)
    
    u_stat, p_value = stats.mannwhitneyu(premier_emoji, laliga_emoji, alternative='two-sided')
    print(f"  絵文字使用: U={u_stat:.0f}, p={p_value:.4f}")
    
    results.append({
        'metric': 'Emoji Rate',
        'premier_value': premier_char['emoji_rate'],
        'laliga_value': laliga_char['emoji_rate'],
        'mann_whitney_u': u_stat,
        'p_value': p_value,
        'cohens_d': np.nan
    })
    
    # 結果保存
    results_df = pd.DataFrame(results)
    output_path = OUTPUT_DIR / "league_comparison_stats.csv"
    results_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"\n✓ 統計比較結果保存: {output_path}")
    
    return results_df, premier_char, laliga_char


def create_visualizations(premier_df, laliga_df):
    """可視化を作成"""
    print("\n" + "=" * 80)
    print("可視化作成中...")
    print("=" * 80)
    
    # 図1: コメント長分布
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    premier_lengths = premier_df['comment'].str.len().dropna()
    laliga_lengths = laliga_df['comment'].str.len().dropna()
    
    # ヒストグラム
    ax1 = axes[0]
    ax1.hist(premier_lengths, bins=100, range=(0, 200), alpha=0.6, 
            label='Premier League', color='purple', density=True)
    ax1.hist(laliga_lengths, bins=100, range=(0, 200), alpha=0.6, 
            label='La Liga', color='red', density=True)
    ax1.set_xlabel('コメント長（文字数）', fontsize=11)
    ax1.set_ylabel('Density', fontsize=11)
    ax1.set_title('コメント長の分布比較', fontsize=12, fontweight='bold')
    ax1.legend()
    ax1.grid(alpha=0.3)
    
    # ボックスプロット
    ax2 = axes[1]
    data_to_plot = [premier_lengths, laliga_lengths]
    bp = ax2.boxplot(data_to_plot, labels=['Premier League', 'La Liga'], patch_artist=True)
    bp['boxes'][0].set_facecolor('purple')
    bp['boxes'][0].set_alpha(0.6)
    bp['boxes'][1].set_facecolor('red')
    bp['boxes'][1].set_alpha(0.6)
    ax2.set_ylabel('コメント長（文字数）', fontsize=11)
    ax2.set_title('コメント長のボックスプロット', fontsize=12, fontweight='bold')
    ax2.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    output_path = OUTPUT_DIR / "comment_length_league_comparison.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  ✓ コメント長比較保存: {output_path.name}")
    plt.close()
    
    print("\n✓ 全可視化完了")


def create_summary_report(stats_df, premier_char, laliga_char):
    """サマリーレポート作成"""
    report = []
    report.append("# リーグ比較分析レポート\n\n")
    report.append(f"**分析日時**: {pd.Timestamp.now().strftime('%Y年%m月%d日 %H:%M')}\n")
    report.append(f"**比較対象**: プレミアリーグ（英語配信） vs ラ・リーガ（スペイン語配信）\n\n")
    report.append("---\n\n")
    
    # 仮説検証
    report.append("## 🎯 仮説検証\n\n")
    
    report.append("### H7: リーグ文化の影響\n\n")
    if premier_char['tactical_term_rate'] > laliga_char['tactical_term_rate']:
        report.append(f"✅ **部分的支持**: プレミアリーグの戦術用語率({premier_char['tactical_term_rate']:.2f}%)はラ・リーガ({laliga_char['tactical_term_rate']:.2f}%)より高い。\n\n")
    else:
        report.append(f"❌ **非支持**: ラ・リーガの方が戦術用語率が高い。\n\n")
    
    report.append("### H8: 分析的 vs 感情的\n\n")
    if (premier_char['mean_length'] > laliga_char['mean_length'] and 
        premier_char['emoji_rate'] < laliga_char['emoji_rate']):
        report.append(f"✅ **支持**: プレミアリーグは平均コメント長が長く({premier_char['mean_length']:.1f}文字 vs {laliga_char['mean_length']:.1f}文字)、絵文字率が低い({premier_char['emoji_rate']:.2f}% vs {laliga_char['emoji_rate']:.2f}%)。より分析的な傾向。\n\n")
    else:
        report.append(f"△ **部分的支持**: 一部指標で予想と異なる結果。\n\n")
    
    # 保存
    output_path = OUTPUT_DIR / "LEAGUE_COMPARISON_SUMMARY.md"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(report)
    
    print(f"\n✓ サマリーレポート保存: {output_path}")
    print("\n" + "".join(report))


def main():
    """メイン実行関数"""
    print("\n🚀 リーグ比較分析開始\n")
    
    # 1. データ読み込み
    print("\n📂 データ読み込み中...")
    premier_df = load_league_data('Premier League')
    laliga_df = load_league_data('La Liga')
    
    if premier_df is None or laliga_df is None:
        print("⚠ データが不足しています")
        return
    
    # 2. 統計比較
    stats_df, premier_char, laliga_char = compare_leagues(premier_df, laliga_df)
    
    # 3. 可視化
    create_visualizations(premier_df, laliga_df)
    
    # 4. サマリーレポート
    create_summary_report(stats_df, premier_char, laliga_char)
    
    print("\n" + "=" * 80)
    print("✅ リーグ比較分析完了!")
    print("=" * 80)
    print(f"\n📁 出力ディレクトリ: {OUTPUT_DIR}")
    print("\n生成されたファイル:")
    for file in sorted(OUTPUT_DIR.glob("*")):
        print(f"  - {file.name}")
    print()


if __name__ == "__main__":
    main()
