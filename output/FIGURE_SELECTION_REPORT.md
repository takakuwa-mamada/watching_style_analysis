================================================================================
論文用図の選定レポート
================================================================================

📊 MAIN PAPER FIGURES (推奨: 6-8枚)
--------------------------------------------------------------------------------

**Figure 1**: exclamation_rate_bootstrap_ci.png
  Path: output/football_only_statistical_analysis/
  Score: 95/100
  Section: Results 4.2 - Emotional Expression
  Reason: 統計的有意性あり (p=0.0272)、文化差を明確に示す
  Caption: Exclamation rate across countries with 95% Bootstrap CI. Japan shows significantly lower exclamation usage (Welch's ANOVA: F=7.443, p=0.0272).

**Figure 2**: emoji_rate_bootstrap_ci.png
  Path: output/football_only_statistical_analysis/
  Score: 90/100
  Section: Results 4.2 - Emotional Expression
  Reason: 最大の効果量 (d=8.765)、スペインと日本の対比
  Caption: Emoji rate comparison showing Spain's expressive style vs Japan's restrained approach (Cohen's d=8.765, Large effect).

**Figure 3**: multi_metric_comparison_football_only.png
  Path: output/football_only_analysis/
  Score: 88/100
  Section: Results 4.1 - Overview
  Reason: 5軸すべてを1枚で比較、論文のFigure 1候補
  Caption: Comprehensive five-axis comparison of watching styles across four countries (Football-only dataset). Shows emotional expression, engagement, and textual patterns.

**Figure 4**: mean_cpm_bootstrap_ci.png
  Path: output/football_only_statistical_analysis/
  Score: 85/100
  Section: Results 4.3 - Engagement Patterns
  Reason: エンゲージメントの基本指標、スポーツ交絡除去後
  Caption: Comments Per Minute (CPM) across countries after removing sport confounding. Shows consistent engagement in football-only analysis.

**Figure 5**: cultural_profiles_heatmap_football_only.png
  Path: output/football_only_analysis/
  Score: 82/100
  Section: Results 4.4 - Cultural Distance
  Reason: 文化プロファイルの可視化、クラスタリング
  Caption: Cultural profile heatmap showing hierarchical clustering. Spain and UK form a cluster, distinct from Japan.

**Figure 6**: exclamation_rate_effect_sizes_heatmap.png
  Path: output/football_only_statistical_analysis/
  Score: 80/100
  Section: Results 4.4 - Cultural Distance
  Reason: 全ペアの効果量を一覧、日本-UK間でLarge効果
  Caption: Pairwise effect sizes (Cohen's d) for exclamation rate. Japan-UK pair shows large effect (d=-4.183).

**Figure 7**: laugh_rate_bootstrap_ci.png
  Path: output/football_only_statistical_analysis/
  Score: 75/100
  Section: Results 4.2 - Emotional Expression
  Reason: 笑い表現の文化差、日本の「w」文化
  Caption: Laugh expression rate (w, lol, haha) showing Japan's unique "w" culture with high usage.

================================================================================
📎 SUPPLEMENTARY FIGURES
--------------------------------------------------------------------------------

**Supp. Figure 1**: sport_confounding_cpm_comparison.png
  Path: output/sport_confounding_comparison/
  Score: 90/100
  Reason: スポーツ交絡の明確な証拠、Methods説明に必須

**Supp. Figure 2**: sport_confounding_summary_table.png
  Path: output/sport_confounding_comparison/
  Score: 85/100
  Reason: 交絡の包括的サマリー、透明性の証明

**Supp. Figure 3**: mean_length_bootstrap_ci.png
  Path: output/football_only_statistical_analysis/
  Score: 70/100
  Reason: コメント長の違い、UK/Spain vs Japan

**Supp. Figure 4**: mean_burst_intensity_bootstrap_ci.png
  Path: output/football_only_statistical_analysis/
  Score: 65/100
  Reason: バースト強度、エンゲージメントの質

================================================================================
💡 推奨構成
--------------------------------------------------------------------------------

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
    
================================================================================
✅ 選定完了!
================================================================================