"""
論文用図の選定: 47枚から最適な6-8枚を選ぶ

基準:
1. 統計的有意性 (p < 0.05)
2. 効果量の大きさ (Cohen's d > 0.8)
3. 視覚的明瞭性
4. 論文のストーリーとの適合性
"""

import os
import pandas as pd
import json

def score_figures():
    """全図にスコアを付けて優先順位を決定"""
    
    figures = []
    
    # Football Only Statistical Analysis (推奨メイン)
    figures.extend([
        {
            'name': 'exclamation_rate_bootstrap_ci.png',
            'path': 'output/football_only_statistical_analysis/',
            'type': 'Main Figure',
            'priority': 1,
            'score': 95,
            'reason': '統計的有意性あり (p=0.0272)、文化差を明確に示す',
            'section': 'Results 4.2 - Emotional Expression',
            'caption': 'Exclamation rate across countries with 95% Bootstrap CI. Japan shows significantly lower exclamation usage (Welch\'s ANOVA: F=7.443, p=0.0272).'
        },
        {
            'name': 'emoji_rate_bootstrap_ci.png',
            'path': 'output/football_only_statistical_analysis/',
            'type': 'Main Figure',
            'priority': 2,
            'score': 90,
            'reason': '最大の効果量 (d=8.765)、スペインと日本の対比',
            'section': 'Results 4.2 - Emotional Expression',
            'caption': 'Emoji rate comparison showing Spain\'s expressive style vs Japan\'s restrained approach (Cohen\'s d=8.765, Large effect).'
        },
        {
            'name': 'mean_cpm_bootstrap_ci.png',
            'path': 'output/football_only_statistical_analysis/',
            'type': 'Main Figure',
            'priority': 3,
            'score': 85,
            'reason': 'エンゲージメントの基本指標、スポーツ交絡除去後',
            'section': 'Results 4.3 - Engagement Patterns',
            'caption': 'Comments Per Minute (CPM) across countries after removing sport confounding. Shows consistent engagement in football-only analysis.'
        },
        {
            'name': 'exclamation_rate_effect_sizes_heatmap.png',
            'path': 'output/football_only_statistical_analysis/',
            'type': 'Main Figure',
            'priority': 4,
            'score': 80,
            'reason': '全ペアの効果量を一覧、日本-UK間でLarge効果',
            'section': 'Results 4.4 - Cultural Distance',
            'caption': 'Pairwise effect sizes (Cohen\'s d) for exclamation rate. Japan-UK pair shows large effect (d=-4.183).'
        },
        {
            'name': 'laugh_rate_bootstrap_ci.png',
            'path': 'output/football_only_statistical_analysis/',
            'type': 'Main Figure',
            'priority': 5,
            'score': 75,
            'reason': '笑い表現の文化差、日本の「w」文化',
            'section': 'Results 4.2 - Emotional Expression',
            'caption': 'Laugh expression rate (w, lol, haha) showing Japan\'s unique "w" culture with high usage.'
        },
        {
            'name': 'mean_length_bootstrap_ci.png',
            'path': 'output/football_only_statistical_analysis/',
            'type': 'Supplementary',
            'priority': 6,
            'score': 70,
            'reason': 'コメント長の違い、UK/Spain vs Japan',
            'section': 'Supplementary Materials',
            'caption': 'Mean comment length showing Western countries\' longer comments vs Japan\'s brevity.'
        },
    ])
    
    # Football Only Analysis (Overview figures)
    figures.extend([
        {
            'name': 'multi_metric_comparison_football_only.png',
            'path': 'output/football_only_analysis/',
            'type': 'Main Figure',
            'priority': 7,
            'score': 88,
            'reason': '5軸すべてを1枚で比較、論文のFigure 1候補',
            'section': 'Results 4.1 - Overview',
            'caption': 'Comprehensive five-axis comparison of watching styles across four countries (Football-only dataset). Shows emotional expression, engagement, and textual patterns.'
        },
        {
            'name': 'cultural_profiles_heatmap_football_only.png',
            'path': 'output/football_only_analysis/',
            'type': 'Main Figure',
            'priority': 8,
            'score': 82,
            'reason': '文化プロファイルの可視化、クラスタリング',
            'section': 'Results 4.4 - Cultural Distance',
            'caption': 'Cultural profile heatmap showing hierarchical clustering. Spain and UK form a cluster, distinct from Japan.'
        },
    ])
    
    # Sport Confounding Comparison (Methods/Supplementary)
    figures.extend([
        {
            'name': 'sport_confounding_cpm_comparison.png',
            'path': 'output/sport_confounding_comparison/',
            'type': 'Supplementary',
            'priority': 9,
            'score': 90,
            'reason': 'スポーツ交絡の明確な証拠、Methods説明に必須',
            'section': 'Methods & Supplementary',
            'caption': 'Sport confounding effect on CPM. Baseball streams show 2× higher engagement than football, necessitating football-only analysis.'
        },
        {
            'name': 'sport_confounding_summary_table.png',
            'path': 'output/sport_confounding_comparison/',
            'type': 'Supplementary',
            'priority': 10,
            'score': 85,
            'reason': '交絡の包括的サマリー、透明性の証明',
            'section': 'Supplementary Materials',
            'caption': 'Comprehensive summary of sport confounding effects. Cultural metrics remain stable while engagement metrics vary by sport type.'
        },
    ])
    
    # Burst Analysis
    figures.extend([
        {
            'name': 'mean_burst_intensity_bootstrap_ci.png',
            'path': 'output/football_only_statistical_analysis/',
            'type': 'Supplementary',
            'priority': 11,
            'score': 65,
            'reason': 'バースト強度、エンゲージメントの質',
            'section': 'Supplementary Materials',
            'caption': 'Burst intensity showing peak engagement moments. Spain shows highest intensity during critical match events.'
        },
    ])
    
    # Sort by score
    figures_sorted = sorted(figures, key=lambda x: x['score'], reverse=True)
    
    return figures_sorted

def create_figure_selection_report(figures):
    """図選定レポートを作成"""
    
    output_dir = 'output'
    os.makedirs(output_dir, exist_ok=True)
    
    # Main paper figures (Top 6-8)
    main_figures = [f for f in figures if f['type'] == 'Main Figure'][:8]
    supplementary_figures = [f for f in figures if f['type'] == 'Supplementary']
    
    report = []
    report.append("=" * 80)
    report.append("論文用図の選定レポート")
    report.append("=" * 80)
    report.append("")
    
    # Main Figures
    report.append("📊 MAIN PAPER FIGURES (推奨: 6-8枚)")
    report.append("-" * 80)
    for i, fig in enumerate(main_figures, 1):
        report.append(f"\n**Figure {i}**: {fig['name']}")
        report.append(f"  Path: {fig['path']}")
        report.append(f"  Score: {fig['score']}/100")
        report.append(f"  Section: {fig['section']}")
        report.append(f"  Reason: {fig['reason']}")
        report.append(f"  Caption: {fig['caption']}")
    
    report.append("\n" + "=" * 80)
    report.append("📎 SUPPLEMENTARY FIGURES")
    report.append("-" * 80)
    for i, fig in enumerate(supplementary_figures, 1):
        report.append(f"\n**Supp. Figure {i}**: {fig['name']}")
        report.append(f"  Path: {fig['path']}")
        report.append(f"  Score: {fig['score']}/100")
        report.append(f"  Reason: {fig['reason']}")
    
    report.append("\n" + "=" * 80)
    report.append("💡 推奨構成")
    report.append("-" * 80)
    report.append("""
**Main Paper (6 Figures)**:
1. Multi-metric comparison (Overview) - 5軸の全体像
2. Exclamation rate with CI (Significant) - 統計的有意性
3. Emoji rate with CI (Largest effect) - 最大効果量
4. CPM with CI (Engagement) - 基本指標
5. Effect size heatmap (Cultural distance) - ペア比較
6. Cultural profile heatmap (Clustering) - 文化グルーピング

**Supplementary (4+ Figures)**:
S1. Sport confounding CPM comparison - 交絡の証拠
S2. Sport confounding summary table - 包括的サマリー
S3. Laugh rate with CI - 追加の文化差
S4. Comment length with CI - テキスト特性
S5. Burst intensity - エンゲージメントの質

**論文のストーリーフロー**:
Results 4.1 → Figure 1 (Overview)
Results 4.2 → Figures 2-3, S3 (Emotional Expression)
Results 4.3 → Figure 4, S5 (Engagement Patterns)
Results 4.4 → Figures 5-6 (Cultural Distance)
Methods → S1-S2 (Sport Confounding)
    """)
    
    report.append("=" * 80)
    report.append("✅ 選定完了!")
    report.append("=" * 80)
    
    # Save report
    report_text = "\n".join(report)
    
    with open(f'{output_dir}/FIGURE_SELECTION_REPORT.md', 'w', encoding='utf-8') as f:
        f.write(report_text)
    
    print(report_text)
    
    # Save as JSON for programmatic use
    with open(f'{output_dir}/figure_selection.json', 'w', encoding='utf-8') as f:
        json.dump({
            'main_figures': main_figures,
            'supplementary_figures': supplementary_figures
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n📁 Saved: {output_dir}/FIGURE_SELECTION_REPORT.md")
    print(f"📁 Saved: {output_dir}/figure_selection.json")

def main():
    print("="*80)
    print("論文用図の選定")
    print("="*80)
    print()
    
    # Score all figures
    figures = score_figures()
    
    # Create report
    create_figure_selection_report(figures)

if __name__ == '__main__':
    main()
