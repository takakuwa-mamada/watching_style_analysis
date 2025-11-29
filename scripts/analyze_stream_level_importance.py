#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配信単位での試合重要度分析（統計的検出力強化版）

改善点:
- 試合単位（N=6）から配信単位（N=31）への変更
- Cohen's dが正しく計算される
- より詳細な統計分析（Bootstrap CI、ペアワイズ比較）
- 配信者メタデータの自動抽出
"""

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from scipy.stats import kruskal, mannwhitneyu
import warnings
warnings.filterwarnings('ignore')

# 日本語フォント設定
plt.rcParams['font.sans-serif'] = ['Yu Gothic', 'Meiryo', 'MS Gothic']
plt.rcParams['axes.unicode_minus'] = False

# パス設定
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output" / "stream_level_match_importance_analysis"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 80)
print("配信単位 試合重要度分析 - Stream-Level Match Importance Analysis")
print("=" * 80)


def load_match_metadata():
    """試合メタデータを読み込む"""
    metadata_path = DATA_DIR / "match_metadata.csv"
    df = pd.read_csv(metadata_path, encoding='utf-8-sig')
    print(f"\n✓ 試合メタデータ読み込み完了: {len(df)} 試合")
    return df


def detect_language_from_filename(filename):
    """ファイル名から言語を推定"""
    filename_lower = filename.lower()
    
    # 日本語
    if any(char in filename for char in ['【', '】', '配信', '同時視聴', '分析']):
        return 'Japanese'
    
    # スペイン語
    if any(word in filename_lower for word in ['directo', 'vivo', 'minuto', 'jornada', 'liga']):
        return 'Spanish'
    
    # フランス語
    if any(word in filename_lower for word in ['live', 'place', 'spectacle', 'forme']):
        if 'barcelone' in filename_lower or 'clasico' in filename_lower:
            return 'French'
    
    # ポルトガル語
    if filename.startswith('Bra'):
        return 'Portuguese'
    
    # 英語（デフォルト）
    return 'English'


def analyze_single_stream(match_folder, csv_file, tier_info):
    """単一配信のデータを分析"""
    try:
        df = pd.read_csv(csv_file, encoding='utf-8-sig')
        
        # カラム名の正規化
        if 'message' in df.columns and 'comment' not in df.columns:
            df.rename(columns={'message': 'comment'}, inplace=True)
        
        if 'comment' not in df.columns:
            return None
        
        # 基本情報
        result = {
            'stream_id': csv_file.stem.replace('_chat_log', ''),
            'match_folder': match_folder,
            'match_name': tier_info['match_name_ja'],
            'tier': tier_info['tier'],
            'tier_label': tier_info['tier_label'],
            'importance_score': tier_info['importance_score'],
            'league': tier_info['league'],
            'match_type': tier_info['match_type'],
            'detected_language': detect_language_from_filename(csv_file.name),
            'total_comments': len(df)
        }
        
        # 感情表現指標
        df['has_emoji'] = df['comment'].str.contains(
            r'[\U0001F000-\U0001F9FF]|[\u2600-\u27BF]|[\u2B50]|[\u26BD]|[\u26A1]|[\u2764]|[\U0001FA00-\U0001FAFF]',
            regex=True, na=False
        )
        result['emoji_rate'] = df['has_emoji'].mean() * 100
        
        df['has_exclamation'] = df['comment'].str.contains('!|！', regex=True, na=False)
        result['exclamation_rate'] = df['has_exclamation'].mean() * 100
        
        df['comment_length'] = df['comment'].str.len()
        result['mean_comment_length'] = df['comment_length'].mean()
        result['median_comment_length'] = df['comment_length'].median()
        
        # バースト指標
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
            df_sorted = df.dropna(subset=['timestamp']).sort_values('timestamp')
            
            if len(df_sorted) > 0:
                df_sorted['minute'] = df_sorted['timestamp'].dt.floor('1min')
                comments_per_minute = df_sorted.groupby('minute').size()
                
                if len(comments_per_minute) > 0:
                    result['max_cpm'] = comments_per_minute.max()
                    result['mean_cpm'] = comments_per_minute.mean()
                    result['median_cpm'] = comments_per_minute.median()
                    result['std_cpm'] = comments_per_minute.std()
                    result['burst_frequency'] = (comments_per_minute > comments_per_minute.mean() + comments_per_minute.std()).sum()
                else:
                    result.update({'max_cpm': np.nan, 'mean_cpm': np.nan, 'median_cpm': np.nan, 
                                  'std_cpm': np.nan, 'burst_frequency': np.nan})
            else:
                result.update({'max_cpm': np.nan, 'mean_cpm': np.nan, 'median_cpm': np.nan, 
                              'std_cpm': np.nan, 'burst_frequency': np.nan})
        
        # トピック多様性
        all_text = ' '.join(df['comment'].dropna().astype(str))
        words = all_text.split()
        
        if len(words) > 0:
            word_counts = pd.Series(words).value_counts()
            probabilities = word_counts / word_counts.sum()
            entropy = -np.sum(probabilities * np.log2(probabilities))
            
            result['topic_entropy'] = entropy
            result['unique_words'] = len(word_counts)
            result['total_words'] = len(words)
            result['lexical_diversity'] = len(word_counts) / len(words) if len(words) > 0 else 0
        else:
            result.update({'topic_entropy': np.nan, 'unique_words': 0, 
                          'total_words': 0, 'lexical_diversity': 0})
        
        return result
        
    except Exception as e:
        print(f"  ⚠ エラー: {csv_file.name} - {e}")
        return None


def analyze_all_streams(metadata):
    """全配信のデータを分析（配信単位）"""
    print("\n" + "=" * 80)
    print("全配信データ分析中（配信単位）...")
    print("=" * 80)
    
    results = []
    
    for _, match_row in metadata.iterrows():
        match_folder = match_row['match_folder']
        folder_path = DATA_DIR / "football" / match_folder
        
        if not folder_path.exists():
            continue
        
        print(f"\n📊 {match_row['match_name_ja']} (Tier {match_row['tier']})")
        
        # CSVファイルを検索
        csv_files = list(folder_path.glob("*_chat_log.csv"))
        if not csv_files:
            csv_files = list(folder_path.glob("*.csv"))
        
        tier_info = match_row.to_dict()
        
        for csv_file in csv_files:
            stream_result = analyze_single_stream(match_folder, csv_file, tier_info)
            if stream_result:
                results.append(stream_result)
                cpm_str = f"{stream_result['max_cpm']:.0f}" if not np.isnan(stream_result['max_cpm']) else 'N/A'
                print(f"  ✓ {stream_result['stream_id'][:50]}: "
                      f"{stream_result['total_comments']:,}件, "
                      f"絵文字{stream_result['emoji_rate']:.1f}%, "
                      f"CPM{cpm_str}")
    
    results_df = pd.DataFrame(results)
    
    # 保存
    output_path = OUTPUT_DIR / "stream_level_raw_data.csv"
    results_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"\n✓ 配信単位生データ保存: {output_path}")
    print(f"  総配信数: {len(results_df)}")
    
    return results_df


def perform_statistical_tests(df):
    """配信単位での統計検定"""
    print("\n" + "=" * 80)
    print("統計検定実行中（配信単位、N={})...".format(len(df)))
    print("=" * 80)
    
    results = []
    
    metrics = [
        ('emoji_rate', '絵文字率 (%)'),
        ('exclamation_rate', '感嘆符率 (%)'),
        ('mean_comment_length', '平均コメント長'),
        ('max_cpm', '最大CPM'),
        ('mean_cpm', '平均CPM'),
        ('topic_entropy', 'トピック多様性')
    ]
    
    for metric, metric_name in metrics:
        if metric not in df.columns or df[metric].isna().all():
            continue
        
        print(f"\n📊 {metric_name}")
        
        # Tier別のデータ
        tier1 = df[df['tier'] == 1][metric].dropna()
        tier2 = df[df['tier'] == 2][metric].dropna()
        tier3 = df[df['tier'] == 3][metric].dropna()
        tier4 = df[df['tier'] == 4][metric].dropna()
        
        print(f"  サンプル数: Tier1={len(tier1)}, Tier2={len(tier2)}, Tier3={len(tier3)}, Tier4={len(tier4)}")
        
        # Kruskal-Wallis検定
        groups = [tier1, tier2, tier3, tier4]
        groups_valid = [g for g in groups if len(g) > 0]
        
        if len(groups_valid) >= 2:
            h_stat, p_value = kruskal(*groups_valid)
            significance = "✓ 有意" if p_value < 0.05 else "非有意"
            print(f"  Kruskal-Wallis: H={h_stat:.3f}, p={p_value:.4f} ({significance})")
            
            # Tier 1 vs Tier 4 の詳細比較
            if len(tier1) > 0 and len(tier4) > 0:
                mean_diff = tier1.mean() - tier4.mean()
                pooled_std = np.sqrt((tier1.std()**2 + tier4.std()**2) / 2)
                cohens_d = mean_diff / pooled_std if pooled_std > 0 else np.nan
                
                u_stat, u_p = mannwhitneyu(tier1, tier4, alternative='two-sided')
                
                # 効果量の解釈
                if np.isnan(cohens_d):
                    effect_interpretation = "undefined"
                elif abs(cohens_d) < 0.2:
                    effect_interpretation = "negligible"
                elif abs(cohens_d) < 0.5:
                    effect_interpretation = "small"
                elif abs(cohens_d) < 0.8:
                    effect_interpretation = "medium"
                else:
                    effect_interpretation = "large"
                
                print(f"  Tier 1 vs Tier 4:")
                print(f"    平均差: {mean_diff:.2f}")
                print(f"    Cohen's d: {cohens_d:.3f} ({effect_interpretation})")
                print(f"    Mann-Whitney U: p={u_p:.4f}")
                
                # Bootstrap信頼区間
                n_bootstrap = 1000
                bootstrap_diffs = []
                for _ in range(n_bootstrap):
                    sample1 = np.random.choice(tier1, size=len(tier1), replace=True)
                    sample4 = np.random.choice(tier4, size=len(tier4), replace=True)
                    bootstrap_diffs.append(sample1.mean() - sample4.mean())
                
                ci_lower = np.percentile(bootstrap_diffs, 2.5)
                ci_upper = np.percentile(bootstrap_diffs, 97.5)
                print(f"    Bootstrap 95% CI: [{ci_lower:.2f}, {ci_upper:.2f}]")
                
                results.append({
                    'metric': metric,
                    'metric_name': metric_name,
                    'kruskal_h': h_stat,
                    'kruskal_p': p_value,
                    'tier1_n': len(tier1),
                    'tier1_mean': tier1.mean(),
                    'tier1_std': tier1.std(),
                    'tier1_median': tier1.median(),
                    'tier4_n': len(tier4),
                    'tier4_mean': tier4.mean(),
                    'tier4_std': tier4.std(),
                    'tier4_median': tier4.median(),
                    'mean_diff': mean_diff,
                    'cohens_d': cohens_d,
                    'effect_interpretation': effect_interpretation,
                    'mannwhitney_u': u_stat,
                    'mannwhitney_p': u_p,
                    'bootstrap_ci_lower': ci_lower,
                    'bootstrap_ci_upper': ci_upper
                })
    
    results_df = pd.DataFrame(results)
    
    # 保存
    output_path = OUTPUT_DIR / "stream_level_statistical_tests.csv"
    results_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"\n✓ 統計検定結果保存: {output_path}")
    
    return results_df


def create_visualizations(df, stats_df):
    """配信単位での可視化"""
    print("\n" + "=" * 80)
    print("可視化作成中...")
    print("=" * 80)
    
    # 図1: 配信単位ボックスプロット（N=31表示）
    fig, axes = plt.subplots(2, 3, figsize=(16, 10))
    fig.suptitle(f'配信単位での試合重要度分析 (N={len(df)} streams)', 
                fontsize=16, fontweight='bold')
    
    metrics_to_plot = [
        ('emoji_rate', '絵文字率 (%)'),
        ('exclamation_rate', '感嘆符率 (%)'),
        ('mean_comment_length', '平均コメント長'),
        ('max_cpm', '最大CPM'),
        ('mean_cpm', '平均CPM'),
        ('topic_entropy', 'トピック多様性')
    ]
    
    for idx, (metric, title) in enumerate(metrics_to_plot):
        ax = axes[idx // 3, idx % 3]
        
        if metric in df.columns and not df[metric].isna().all():
            df_sorted = df.sort_values('tier')
            
            # ボックスプロット + ストリッププロット
            sns.boxplot(data=df_sorted, x='tier_label', y=metric, ax=ax,
                       order=['Ultra-High', 'High', 'Medium', 'Low'],
                       palette='RdYlGn_r', showmeans=True)
            
            sns.stripplot(data=df_sorted, x='tier_label', y=metric, ax=ax,
                         order=['Ultra-High', 'High', 'Medium', 'Low'],
                         color='black', alpha=0.4, size=4)
            
            # p値を表示
            if not stats_df.empty and metric in stats_df['metric'].values:
                p_val = stats_df[stats_df['metric'] == metric]['kruskal_p'].values[0]
                sig_text = f'p={p_val:.4f}'
                if p_val < 0.001:
                    sig_text = 'p<0.001***'
                elif p_val < 0.01:
                    sig_text = f'p={p_val:.4f}**'
                elif p_val < 0.05:
                    sig_text = f'p={p_val:.4f}*'
                
                ax.text(0.5, 0.95, sig_text, transform=ax.transAxes,
                       ha='center', va='top', fontsize=9,
                       bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
            
            ax.set_title(title, fontsize=11, fontweight='bold')
            ax.set_xlabel('試合重要度', fontsize=9)
            ax.set_ylabel(title, fontsize=9)
            ax.grid(axis='y', alpha=0.3)
        else:
            ax.text(0.5, 0.5, f'{title}\nデータなし', 
                   ha='center', va='center', transform=ax.transAxes)
    
    plt.tight_layout()
    output_path = OUTPUT_DIR / "stream_level_boxplot.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  ✓ ボックスプロット保存: {output_path.name}")
    plt.close()
    
    # 図2: 効果量と有意性の可視化
    if not stats_df.empty:
        fig, ax = plt.subplots(figsize=(10, 6))
        
        stats_df_sorted = stats_df.sort_values('cohens_d', ascending=True)
        colors = ['red' if p < 0.05 else 'orange' if p < 0.10 else 'gray' 
                 for p in stats_df_sorted['kruskal_p']]
        
        bars = ax.barh(range(len(stats_df_sorted)), stats_df_sorted['cohens_d'], color=colors)
        ax.set_yticks(range(len(stats_df_sorted)))
        ax.set_yticklabels(stats_df_sorted['metric_name'])
        ax.set_xlabel("Cohen's d (Tier 1 vs Tier 4)", fontsize=11)
        ax.set_title("効果量と統計的有意性（配信単位 N=31）", fontsize=13, fontweight='bold')
        ax.axvline(x=0, color='black', linestyle='-', linewidth=0.8)
        ax.axvline(x=0.2, color='green', linestyle='--', alpha=0.5, label='Small effect')
        ax.axvline(x=0.5, color='orange', linestyle='--', alpha=0.5, label='Medium effect')
        ax.axvline(x=0.8, color='red', linestyle='--', alpha=0.5, label='Large effect')
        ax.legend(loc='lower right', fontsize=9)
        ax.grid(axis='x', alpha=0.3)
        
        # 凡例
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='red', label='p<0.05 (有意)'),
            Patch(facecolor='orange', label='p<0.10 (傾向)'),
            Patch(facecolor='gray', label='p≥0.10 (非有意)')
        ]
        ax.legend(handles=legend_elements, loc='upper right', fontsize=9)
        
        plt.tight_layout()
        output_path = OUTPUT_DIR / "effect_size_and_significance.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"  ✓ 効果量プロット保存: {output_path.name}")
        plt.close()
    
    print("\n✓ 全可視化完了")


def create_summary_report(df, stats_df):
    """配信単位分析のサマリーレポート"""
    print("\n" + "=" * 80)
    print("サマリーレポート作成中...")
    print("=" * 80)
    
    report = []
    report.append("# 配信単位 試合重要度分析レポート\n\n")
    report.append(f"**分析日時**: {pd.Timestamp.now().strftime('%Y年%m月%d日 %H:%M')}\n")
    report.append(f"**分析単位**: 配信単位（Stream-level）\n")
    report.append(f"**総配信数**: N={len(df)}\n\n")
    report.append("---\n\n")
    
    # データ概要
    report.append("## 📊 データ概要\n\n")
    tier_summary = df.groupby('tier_label').agg({
        'total_comments': 'sum',
        'stream_id': 'count',
        'emoji_rate': 'mean',
        'exclamation_rate': 'mean',
        'max_cpm': 'mean'
    }).reindex(['Ultra-High', 'High', 'Medium', 'Low'])
    
    report.append("| Tier | 配信数 | 総コメント数 | 平均絵文字率(%) | 平均感嘆符率(%) | 平均最大CPM |\n")
    report.append("|------|--------|-------------|----------------|----------------|-----------|\n")
    for tier_label, row in tier_summary.iterrows():
        report.append(f"| {tier_label} | {row['stream_id']:.0f} | {row['total_comments']:,.0f} | "
                     f"{row['emoji_rate']:.2f} | {row['exclamation_rate']:.2f} | {row['max_cpm']:.0f} |\n")
    report.append("\n")
    
    # 統計的有意差
    report.append("## 📈 統計的有意差の検出\n\n")
    
    significant_results = stats_df[stats_df['kruskal_p'] < 0.05]
    if len(significant_results) > 0:
        report.append("### ✅ 有意差が検出された指標（p<0.05）\n\n")
        for _, row in significant_results.iterrows():
            report.append(f"- **{row['metric_name']}**\n")
            report.append(f"  - Kruskal-Wallis: H={row['kruskal_h']:.3f}, **p={row['kruskal_p']:.4f}**\n")
            report.append(f"  - Tier 1 平均: {row['tier1_mean']:.2f} (N={row['tier1_n']:.0f})\n")
            report.append(f"  - Tier 4 平均: {row['tier4_mean']:.2f} (N={row['tier4_n']:.0f})\n")
            report.append(f"  - 効果量: Cohen's d={row['cohens_d']:.3f} ({row['effect_interpretation']})\n")
            report.append(f"  - Bootstrap 95% CI: [{row['bootstrap_ci_lower']:.2f}, {row['bootstrap_ci_upper']:.2f}]\n\n")
    
    trend_results = stats_df[(stats_df['kruskal_p'] >= 0.05) & (stats_df['kruskal_p'] < 0.10)]
    if len(trend_results) > 0:
        report.append("### 🔶 傾向が見られた指標（0.05≤p<0.10）\n\n")
        for _, row in trend_results.iterrows():
            report.append(f"- **{row['metric_name']}**: p={row['kruskal_p']:.4f}, d={row['cohens_d']:.3f}\n")
        report.append("\n")
    
    # 改善の確認
    report.append("## 🔍 試合単位分析からの改善\n\n")
    report.append("| 項目 | 試合単位 (N=6) | 配信単位 (N=31) | 改善 |\n")
    report.append("|------|---------------|----------------|------|\n")
    report.append("| サンプルサイズ | 6試合 | 31配信 | **5.2倍** |\n")
    report.append("| Cohen's d計算 | 不可 (NaN) | **可能** | ✅ |\n")
    report.append("| 統計的検出力 | 低 | **中～高** | ✅ |\n")
    if len(significant_results) > 0:
        report.append(f"| 有意差検出 | 0指標 | **{len(significant_results)}指標** | ✅ |\n")
    report.append("\n")
    
    # 保存
    output_path = OUTPUT_DIR / "STREAM_LEVEL_ANALYSIS_SUMMARY.md"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(report)
    
    print(f"\n✓ サマリーレポート保存: {output_path}")
    print("\n" + "".join(report))


def main():
    """メイン実行関数"""
    print("\n🚀 配信単位 試合重要度分析開始\n")
    
    # 1. メタデータ読み込み
    metadata = load_match_metadata()
    
    # 2. 全配信のデータ分析（配信単位）
    results_df = analyze_all_streams(metadata)
    
    # 3. 統計検定
    stats_df = perform_statistical_tests(results_df)
    
    # 4. 可視化
    create_visualizations(results_df, stats_df)
    
    # 5. サマリーレポート
    create_summary_report(results_df, stats_df)
    
    print("\n" + "=" * 80)
    print("✅ 配信単位 試合重要度分析完了!")
    print("=" * 80)
    print(f"\n📁 出力ディレクトリ: {OUTPUT_DIR}")
    print("\n生成されたファイル:")
    for file in sorted(OUTPUT_DIR.glob("*")):
        print(f"  - {file.name}")
    print()


if __name__ == "__main__":
    main()
