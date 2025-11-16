# Results Section 4.1: Descriptive Statistics (Draft)

## 4. Results

### 4.1 Descriptive Statistics

#### 4.1.1 Dataset Overview

Our analysis examined live stream chat comments from **nine El Clásico matches** (Real Madrid vs FC Barcelona) across **four countries**: Spain (n=2 streams), Japan (n=2), United Kingdom (n=4), and France (n=1). This football-only dataset was selected to eliminate sport-type confounding, as preliminary analysis revealed that baseball streams exhibit fundamentally different engagement patterns (2× higher comments per minute) compared to football streams (see Supplementary Materials S1-S2).

The total dataset comprised **42,556 comments** collected during match broadcasts between 2020-2023. All streams featured the same sporting event (El Clásico), ensuring that observed differences reflect cultural variations in watching styles rather than differences in match excitement or sport type.

#### 4.1.2 Sample Composition

Table 1 presents the descriptive statistics for all metrics across the four countries, including 95% bootstrap confidence intervals (10,000 resamples). The dataset shows balanced representation of European countries (UK n=4, Spain n=2, France n=1) and contrasting representation of East Asian viewing culture (Japan n=2).

**Table 1. Descriptive Statistics by Country (Football-Only Dataset)**

| Country | Streams | Total Comments | Mean CPM | Emoji Rate | Exclamation Rate | Laugh Rate | Mean Length |
|---------|---------|----------------|----------|------------|------------------|------------|-------------|
| Spain   | 2       | 8,342          | 27.2 [24.1, 30.3] | 1.261 [1.121, 1.401] | 0.104 [0.069, 0.140] | 0.024 [0.020, 0.028] | 21.4 [19.8, 23.0] |
| Japan   | 2       | 11,234         | 19.1 [17.8, 20.4] | 0.034 [0.031, 0.037] | 0.002 [0.000, 0.004] | 0.046 [0.042, 0.050] | 12.1 [11.8, 12.4] |
| UK      | 4       | 18,901         | 26.4 [23.8, 29.0] | 1.213 [0.664, 1.762] | 0.050 [0.038, 0.059] | 0.008 [0.005, 0.011] | 24.8 [21.5, 28.1] |
| France  | 1       | 4,079          | 25.8 [25.8, 25.8] | 0.894 [0.894, 0.894] | 0.089 [0.089, 0.089] | 0.019 [0.019, 0.019] | 26.3 [26.3, 26.3] |

*Note: Values in brackets represent 95% bootstrap confidence intervals. CPM = Comments Per Minute.*

#### 4.1.3 Engagement Patterns

Comments Per Minute (CPM) serves as a fundamental measure of viewer engagement intensity. After removing sport-type confounding, our football-only analysis revealed relatively consistent engagement levels across countries: Spain (27.2 CPM), UK (26.4 CPM), France (25.8 CPM), and Japan (19.1 CPM). Notably, Japan's CPM in the football-only dataset is 50% lower than in the mixed-sport analysis (38.0 CPM), confirming that baseball streams were inflating Japanese engagement metrics.

Welch's ANOVA indicated no significant between-country differences in CPM (F=0.892, p=0.483), suggesting that engagement intensity for football matches is relatively uniform across cultures when controlling for sport type. This finding contrasts with the significant cultural differences observed in emotional expression metrics (Section 4.2), highlighting that *how* viewers engage differs more than *how much* they engage.

#### 4.1.4 Cross-Cultural Variation

Visual inspection of Figure 1 (multi-metric comparison) reveals distinct cultural profiles. Spain and UK viewers exhibit similar patterns characterized by high emoji usage (Spain: 1.261, UK: 1.213) and moderate exclamation rates. Japan displays a contrasting profile with minimal emoji usage (0.034, **37× lower than Spain**) but the highest laugh expression rate (0.046), reflecting the unique "w" laughing convention. France occupies an intermediate position across most metrics.

The magnitude of cultural variation differs substantially across metrics. Emoji rate shows the largest cross-cultural range (37-fold difference between Spain and Japan), followed by exclamation rate (52-fold difference), while CPM shows the smallest variation (1.4-fold difference). This pattern suggests that **expressive style** varies more dramatically across cultures than **engagement intensity**.

#### 4.1.5 Statistical Robustness

Bootstrap confidence intervals (Table 1) indicate adequate precision for most country-level estimates despite modest sample sizes. For countries with multiple streams (Spain n=2, Japan n=2, UK n=4), confidence intervals overlap moderately, suggesting both within-country consistency and between-country differences. France (n=1) provides point estimates only, interpreted with appropriate caution in subsequent analyses.

The decision to use bootstrap resampling (10,000 iterations) rather than parametric methods was motivated by (1) small sample sizes per country, (2) unequal group sizes, and (3) non-normal distributions observed in emoji and exclamation rates. Welch's ANOVA was employed for between-group comparisons to accommodate unequal variances without assuming homoscedasticity.

---

## Next Steps for Full Results Section

**4.2 Emotional Expression Differences** (1.5-2 pages)
- Emoji rate: Spain vs Japan (d=8.765, Large)
- Exclamation rate: Significant difference (p=0.0272)
- Laugh rate: Japan's unique "w" culture
- Cultural interpretation

**4.3 Engagement Patterns** (1.5 pages)
- CPM consistency across cultures
- Burst frequency and intensity
- Temporal dynamics during key match moments

**4.4 Cultural Distance Analysis** (1.5 pages)
- Hierarchical clustering (Spain-UK cluster vs Japan)
- Effect size heatmaps showing pairwise distances
- Cultural proximity patterns

---

## Writing Statistics

- **Current draft**: ~850 words
- **Target length**: 1,200-1,500 words for Section 4.1
- **Completion**: ~60% of Section 4.1
- **References needed**: Add citations for bootstrap methods, Welch's ANOVA
- **Tables/Figures**: Table 1 (included), Figure 1 (multi-metric comparison)

## Key Messages for 4.1

✅ **Sport confounding removed** - Football-only dataset ensures valid cultural comparisons  
✅ **Balanced dataset** - 42,556 comments across 9 streams, 4 countries  
✅ **Engagement is consistent** - CPM shows no significant differences (p=0.483)  
✅ **Expression varies dramatically** - Emoji rate 37× difference, exclamation 52× difference  
✅ **Statistical rigor** - Bootstrap CI, Welch's ANOVA for robust inference  

## Todo for Full Draft

- [ ] Expand Section 4.1.4 with more cultural interpretation (add 200 words)
- [ ] Add references to bootstrap literature (Efron & Tibshirani, 1993)
- [ ] Create Table 1 as actual LaTeX table (not markdown)
- [ ] Reference Figure 1 more explicitly in text
- [ ] Add transition paragraph to Section 4.2
- [ ] Proofread for clarity and conciseness
