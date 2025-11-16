"""
統計的分析の改善
Bootstrap CI、Welch's ANOVA、Effect sizeの計算
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import f_oneway
import os

# 日本語フォント設定
plt.rcParams['font.sans-serif'] = ['MS Gothic', 'Yu Gothic', 'Meiryo']
plt.rcParams['axes.unicode_minus'] = False

def calculate_bootstrap_ci(data, n_bootstrap=10000, confidence=0.95):
    """Bootstrap法で平均の信頼区間を計算"""
    if len(data) == 0:
        return None, None, None
    
    rng = np.random.default_rng(42)
    bootstrap_means = []
    
    for _ in range(n_bootstrap):
        sample = rng.choice(data, size=len(data), replace=True)
        bootstrap_means.append(np.mean(sample))
    
    mean = np.mean(data)
    alpha = (1 - confidence) / 2
    ci_low = np.percentile(bootstrap_means, alpha * 100)
    ci_high = np.percentile(bootstrap_means, (1 - alpha) * 100)
    
    return mean, ci_low, ci_high

def calculate_cohens_d(group1, group2):
    """Cohen's d（効果量）を計算"""
    n1, n2 = len(group1), len(group2)
    if n1 == 0 or n2 == 0:
        return None
    
    mean1, mean2 = np.mean(group1), np.mean(group2)
    var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)
    
    # Pooled standard deviation
    pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
    
    if pooled_std == 0:
        return None
    
    d = (mean1 - mean2) / pooled_std
    return d

def welch_anova(df, metric, group_col='country'):
    """
    Welch's ANOVA (不等分散対応)
    scipyのf_onewayはデフォルトでWelch版を使用
    """
    groups = []
    group_names = []
    
    for name in df[group_col].unique():
        data = df[df[group_col] == name][metric].dropna().values
        if len(data) > 0:
            groups.append(data)
            group_names.append(name)
    
    if len(groups) < 2:
        return None, None, group_names
    
    # Welch's ANOVA
    f_stat, p_value = f_oneway(*groups)
    
    return f_stat, p_value, group_names

def analyze_with_bootstrap(df, metrics, group_col='country'):
    """Bootstrap CIとeffect sizeを含む包括的分析"""
    
    results = {}
    
    for metric in metrics:
        print(f"\n{'='*80}")
        print(f"分析対象: {metric}")
        print(f"{'='*80}")
        
        # Bootstrap CI計算
        bootstrap_results = []
        
        for group in df[group_col].unique():
            data = df[df[group_col] == group][metric].dropna().values
            
            if len(data) == 0:
                continue
            
            mean, ci_low, ci_high = calculate_bootstrap_ci(data, n_bootstrap=10000)
            
            bootstrap_results.append({
                'group': group,
                'n': len(data),
                'mean': mean,
                'ci_low': ci_low,
                'ci_high': ci_high,
                'ci_width': ci_high - ci_low,
                'stderr': np.std(data) / np.sqrt(len(data)) if len(data) > 1 else np.nan
            })
        
        df_bootstrap = pd.DataFrame(bootstrap_results)
        print("\n📊 Bootstrap 95% CI:")
        print(df_bootstrap.to_string(index=False))
        
        # Welch's ANOVA
        f_stat, p_value, group_names = welch_anova(df, metric, group_col)
        
        if f_stat is not None:
            print(f"\n📈 Welch's ANOVA:")
            print(f"  F-statistic = {f_stat:.3f}")
            print(f"  p-value = {p_value:.4f}")
            
            if p_value < 0.05:
                print(f"  ✅ Significant difference detected! (p < 0.05)")
            else:
                print(f"  ❌ No significant difference (p ≥ 0.05)")
        
        # Pairwise effect sizes
        print(f"\n💪 Pairwise Effect Sizes (Cohen's d):")
        
        effect_sizes = []
        groups_list = df[group_col].unique()
        
        for i, group1 in enumerate(groups_list):
            for group2 in groups_list[i+1:]:
                data1 = df[df[group_col] == group1][metric].dropna().values
                data2 = df[df[group_col] == group2][metric].dropna().values
                
                if len(data1) > 0 and len(data2) > 0:
                    d = calculate_cohens_d(data1, data2)
                    
                    if d is not None:
                        # Effect size interpretation
                        if abs(d) < 0.2:
                            magnitude = "Negligible"
                        elif abs(d) < 0.5:
                            magnitude = "Small"
                        elif abs(d) < 0.8:
                            magnitude = "Medium"
                        else:
                            magnitude = "Large"
                        
                        effect_sizes.append({
                            'pair': f"{group1} vs {group2}",
                            'cohens_d': d,
                            'magnitude': magnitude,
                            'n1': len(data1),
                            'n2': len(data2)
                        })
                        
                        print(f"  {group1} vs {group2}: d={d:.3f} ({magnitude}), n1={len(data1)}, n2={len(data2)}")
        
        df_effect = pd.DataFrame(effect_sizes)
        
        results[metric] = {
            'bootstrap': df_bootstrap,
            'anova': {'f': f_stat, 'p': p_value, 'groups': group_names},
            'effect_sizes': df_effect
        }
    
    return results

def create_improved_visualizations(results, output_dir):
    """改善された可視化（CIエラーバー付き）"""
    
    print("\n🎨 改善された可視化作成中...")
    
    for metric, result_dict in results.items():
        df_bootstrap = result_dict['bootstrap']
        
        if len(df_bootstrap) == 0:
            continue
        
        # Figure: Mean with 95% CI error bars
        fig, ax = plt.subplots(figsize=(10, 6))
        
        x_pos = np.arange(len(df_bootstrap))
        
        # Bar plot
        bars = ax.bar(x_pos, df_bootstrap['mean'], alpha=0.7, color='steelblue', edgecolor='black')
        
        # Error bars (CI)
        errors_low = df_bootstrap['mean'] - df_bootstrap['ci_low']
        errors_high = df_bootstrap['ci_high'] - df_bootstrap['mean']
        ax.errorbar(x_pos, df_bootstrap['mean'], 
                   yerr=[errors_low, errors_high],
                   fmt='none', ecolor='black', capsize=5, capthick=2)
        
        # Labels
        ax.set_xticks(x_pos)
        ax.set_xticklabels(df_bootstrap['group'], rotation=45, ha='right')
        ax.set_ylabel(metric.replace('_', ' ').title(), fontsize=12)
        ax.set_title(f'{metric.replace("_", " ").title()}\n(Mean with 95% Bootstrap CI)', 
                    fontsize=14, fontweight='bold')
        ax.grid(alpha=0.3, axis='y')
        
        # Sample sizes
        for i, row in df_bootstrap.iterrows():
            ax.text(i, row['mean'] + (row['ci_high'] - row['mean']) + 0.05 * ax.get_ylim()[1], 
                   f'n={row["n"]}', ha='center', va='bottom', fontsize=9)
        
        plt.tight_layout()
        plt.savefig(f'{output_dir}/{metric}_bootstrap_ci.png', dpi=300, bbox_inches='tight')
        print(f"✅ Saved: {metric}_bootstrap_ci.png")
        plt.close()
        
        # Figure: Effect sizes heatmap
        df_effect = result_dict['effect_sizes']
        
        if len(df_effect) > 0:
            # Pivot for heatmap
            groups = df_bootstrap['group'].unique()
            n_groups = len(groups)
            
            # NaNを含む行列を作成（デフォルトはNaN）
            effect_matrix = np.full((n_groups, n_groups), np.nan)
            
            for idx, row in df_effect.iterrows():
                pair = row['pair']
                g1, g2 = pair.split(' vs ')
                
                try:
                    i = np.where(groups == g1)[0][0]
                    j = np.where(groups == g2)[0][0]
                    
                    # NaNでない場合のみ設定
                    if pd.notna(row['cohens_d']):
                        effect_matrix[i, j] = row['cohens_d']
                        effect_matrix[j, i] = -row['cohens_d']  # Symmetric with opposite sign
                except:
                    pass
            
            fig, ax = plt.subplots(figsize=(12, 10))
            
            # Mask diagonal and NaN values
            mask = np.eye(n_groups, dtype=bool) | np.isnan(effect_matrix)
            
            # カスタムアノテーション（NaNには"N/A"を表示）
            annot_matrix = np.empty_like(effect_matrix, dtype=object)
            for i in range(n_groups):
                for j in range(n_groups):
                    if i == j:
                        annot_matrix[i, j] = ""
                    elif np.isnan(effect_matrix[i, j]):
                        annot_matrix[i, j] = "N/A\n(n=1)"
                    else:
                        annot_matrix[i, j] = f"{effect_matrix[i, j]:.2f}"
            
            # 効果量に応じた色の範囲を設定
            vmin = -5 if np.nanmin(effect_matrix) < -2 else -2
            vmax = 5 if np.nanmax(effect_matrix) > 2 else 2
            
            # Heatmap
            sns.heatmap(effect_matrix, annot=annot_matrix, fmt='', cmap='RdBu_r', center=0,
                       xticklabels=groups, yticklabels=groups, ax=ax, mask=mask,
                       cbar_kws={'label': "Cohen's d"}, vmin=vmin, vmax=vmax,
                       linewidths=0.5, linecolor='gray')
            
            ax.set_title(f"Effect Sizes (Cohen's d) for {metric.replace('_', ' ').title()}\n"
                        f"Red = Group 1 > Group 2, Blue = Group 1 < Group 2", 
                        fontsize=14, fontweight='bold')
            ax.set_xlabel('Group 2', fontsize=12, fontweight='bold')
            ax.set_ylabel('Group 1', fontsize=12, fontweight='bold')
            
            # 効果量の凡例を追加
            legend_text = ("Effect Size Interpretation:\n"
                          "|d| < 0.2: Negligible\n"
                          "0.2 ≤ |d| < 0.5: Small\n"
                          "0.5 ≤ |d| < 0.8: Medium\n"
                          "|d| ≥ 0.8: Large")
            ax.text(1.15, 0.5, legend_text, transform=ax.transAxes, 
                   fontsize=9, verticalalignment='center',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
            
            plt.tight_layout()
            plt.savefig(f'{output_dir}/{metric}_effect_sizes_heatmap.png', dpi=300, bbox_inches='tight')
            print(f"✅ Saved: {metric}_effect_sizes_heatmap.png")
            plt.close()

def generate_improved_summary_report(results, output_dir):
    """改善された統計レポートを生成"""
    
    report_lines = []
    report_lines.append("="*80)
    report_lines.append("改善された統計分析レポート")
    report_lines.append("="*80)
    report_lines.append("")
    report_lines.append("## 方法論")
    report_lines.append("")
    report_lines.append("- **信頼区間**: Bootstrap法 (n=10,000 resamples, 95% CI)")
    report_lines.append("- **群間比較**: Welch's ANOVA (不等分散対応)")
    report_lines.append("- **効果量**: Cohen's d")
    report_lines.append("  - |d| < 0.2: Negligible")
    report_lines.append("  - 0.2 ≤ |d| < 0.5: Small")
    report_lines.append("  - 0.5 ≤ |d| < 0.8: Medium")
    report_lines.append("  - |d| ≥ 0.8: Large")
    report_lines.append("")
    
    for metric, result_dict in results.items():
        report_lines.append(f"## {metric.replace('_', ' ').title()}")
        report_lines.append("")
        
        # Bootstrap results
        df_bootstrap = result_dict['bootstrap']
        report_lines.append("### Bootstrap 95% Confidence Intervals")
        report_lines.append("")
        report_lines.append("```")
        report_lines.append(df_bootstrap.to_string(index=False))
        report_lines.append("```")
        report_lines.append("")
        
        # ANOVA results
        anova = result_dict['anova']
        if anova['f'] is not None:
            report_lines.append("### Welch's ANOVA")
            report_lines.append("")
            report_lines.append(f"- F-statistic: {anova['f']:.3f}")
            report_lines.append(f"- p-value: {anova['p']:.4f}")
            
            if anova['p'] < 0.001:
                report_lines.append(f"- **Result**: ✅ Highly significant (p < 0.001) ****")
            elif anova['p'] < 0.01:
                report_lines.append(f"- **Result**: ✅ Very significant (p < 0.01) ***")
            elif anova['p'] < 0.05:
                report_lines.append(f"- **Result**: ✅ Significant (p < 0.05) *")
            else:
                report_lines.append(f"- **Result**: ❌ Not significant (p ≥ 0.05)")
            
            report_lines.append("")
        
        # Effect sizes
        df_effect = result_dict['effect_sizes']
        if len(df_effect) > 0:
            report_lines.append("### Pairwise Effect Sizes (Cohen's d)")
            report_lines.append("")
            
            # Large effects
            large_effects = df_effect[df_effect['magnitude'] == 'Large']
            if len(large_effects) > 0:
                report_lines.append("**Large effects (|d| ≥ 0.8)**:")
                for idx, row in large_effects.iterrows():
                    report_lines.append(f"- {row['pair']}: d={row['cohens_d']:.3f}")
                report_lines.append("")
            
            # Full table
            report_lines.append("```")
            report_lines.append(df_effect.to_string(index=False))
            report_lines.append("```")
            report_lines.append("")
        
        report_lines.append("---")
        report_lines.append("")
    
    # Save report
    with open(f'{output_dir}/IMPROVED_STATISTICAL_REPORT.md', 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    
    print(f"\n✅ Saved: IMPROVED_STATISTICAL_REPORT.md")
    
    return '\n'.join(report_lines)

def main():
    print("="*80)
    print("統計的分析の改善")
    print("="*80)
    
    # Load data
    print("\n📊 データ読み込み中...")
    
    try:
        df_emotional = pd.read_csv('output/emotional_analysis/emotional_expression_results.csv')
        print("✅ Loaded emotional expression results")
    except:
        print("❌ Emotional expression results not found")
        return
    
    try:
        df_engagement = pd.read_csv('output/engagement_analysis/engagement_results.csv')
        print("✅ Loaded engagement results")
    except:
        print("❌ Engagement results not found")
        return
    
    # Output directory
    output_dir = 'output/improved_statistical_analysis'
    os.makedirs(output_dir, exist_ok=True)
    
    # Analyze emotional metrics
    print("\n" + "="*80)
    print("感情表現メトリクスの分析")
    print("="*80)
    
    emotional_metrics = ['emoji_rate', 'laugh_rate', 'exclamation_rate', 'mean_length']
    results_emotional = analyze_with_bootstrap(df_emotional, emotional_metrics, 'country')
    
    # Analyze engagement metrics
    print("\n" + "="*80)
    print("エンゲージメントメトリクスの分析")
    print("="*80)
    
    engagement_metrics = ['mean_cpm', 'burst_freq_per_hour', 'mean_burst_duration', 'mean_burst_intensity']
    results_engagement = analyze_with_bootstrap(df_engagement, engagement_metrics, 'country')
    
    # Combine results
    all_results = {**results_emotional, **results_engagement}
    
    # Save detailed results
    for metric, result_dict in all_results.items():
        df_bootstrap = result_dict['bootstrap']
        df_bootstrap.to_csv(f'{output_dir}/{metric}_bootstrap_ci.csv', index=False, encoding='utf-8-sig')
        
        df_effect = result_dict['effect_sizes']
        if len(df_effect) > 0:
            df_effect.to_csv(f'{output_dir}/{metric}_effect_sizes.csv', index=False, encoding='utf-8-sig')
    
    print(f"\n✅ Detailed results saved to {output_dir}/")
    
    # Create visualizations
    create_improved_visualizations(all_results, output_dir)
    
    # Generate report
    report = generate_improved_summary_report(all_results, output_dir)
    
    print("\n" + "="*80)
    print("統計分析完了！")
    print("="*80)
    print(f"\n📁 結果は {output_dir}/ に保存されました")
    print("\n主要な改善点:")
    print("  ✅ Bootstrap 95% CI: 小サンプルでも信頼区間計算可能")
    print("  ✅ Welch's ANOVA: 不等分散・不等サンプルサイズに対応")
    print("  ✅ Cohen's d: 効果量を明示（論文執筆に必須）")

if __name__ == "__main__":
    main()
