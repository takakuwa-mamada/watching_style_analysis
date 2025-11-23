================================================================================
Football Only版 統計分析レポート
================================================================================

## データセット

- ストリーム数: 9 streams
- 対象: El Clasico (Real Madrid vs Barcelona)
- 国: Spain (n=2), Japan (n=2), UK (n=4), France (n=1)
- スポーツ: Football のみ (Baseball除外)

## 方法論

- **信頼区間**: Bootstrap法 (n=10,000 resamples, 95% CI)
- **群間比較**: Welch's ANOVA (不等分散対応)
- **効果量**: Cohen's d
  - |d| < 0.2: Negligible
  - 0.2 ≤ |d| < 0.5: Small
  - 0.5 ≤ |d| < 0.8: Medium
  - |d| ≥ 0.8: Large

## Emoji Rate

### Bootstrap 95% Confidence Intervals

```
 group  n     mean   ci_low  ci_high  ci_width   stderr
France  1 0.894481 0.894481 0.894481  0.000000      NaN
 Japan  2 0.034249 0.031193 0.037304  0.006111 0.003055
 Spain  2 1.260885 1.120977 1.400794  0.279816 0.139908
    UK  4 1.212951 0.663690 1.762212  1.098523 0.322892
```

### Welch's ANOVA

- F-statistic: 2.771
- p-value: 0.1504
- **Result**: ❌ Not significant (p ≥ 0.05)

### Pairwise Effect Sizes (Cohen's d)

**Large effects (|d| ≥ 0.8)**:
- Spain vs Japan: d=8.765
- Spain vs France: d=nan
- Japan vs UK: d=-2.108
- Japan vs France: d=nan
- UK vs France: d=nan

```
           pair  cohens_d  magnitude  n1  n2
 Spain vs Japan  8.765349      Large   2   2
    Spain vs UK  0.084399 Negligible   2   4
Spain vs France       NaN      Large   2   1
    Japan vs UK -2.107574      Large   2   4
Japan vs France       NaN      Large   2   1
   UK vs France       NaN      Large   4   1
```

---

## Laugh Rate

### Bootstrap 95% Confidence Intervals

```
 group  n     mean   ci_low  ci_high  ci_width   stderr
France  1 0.010220 0.010220 0.010220  0.000000      NaN
 Japan  2 0.045834 0.043852 0.047815  0.003964 0.001982
 Spain  2 0.021626 0.002646 0.040607  0.037961 0.018981
    UK  4 0.012199 0.008150 0.018377  0.010228 0.003060
```

### Welch's ANOVA

- F-statistic: 3.286
- p-value: 0.1165
- **Result**: ❌ Not significant (p ≥ 0.05)

### Pairwise Effect Sizes (Cohen's d)

**Large effects (|d| ≥ 0.8)**:
- Spain vs Japan: d=-1.268
- Spain vs France: d=nan
- Japan vs UK: d=6.136
- Japan vs France: d=nan
- UK vs France: d=nan

```
           pair  cohens_d magnitude  n1  n2
 Spain vs Japan -1.268489     Large   2   2
    Spain vs UK  0.653300    Medium   2   4
Spain vs France       NaN     Large   2   1
    Japan vs UK  6.135860     Large   2   4
Japan vs France       NaN     Large   2   1
   UK vs France       NaN     Large   4   1
```

---

## Exclamation Rate

### Bootstrap 95% Confidence Intervals

```
 group  n     mean   ci_low  ci_high  ci_width   stderr
France  1 0.112417 0.112417 0.112417  0.000000      NaN
 Japan  2 0.002164 0.000000 0.004328  0.004328 0.002164
 Spain  2 0.104352 0.068519 0.140185  0.071667 0.035833
    UK  4 0.049653 0.037940 0.058963  0.021023 0.006495
```

### Welch's ANOVA

- F-statistic: 7.443
- p-value: 0.0272
- **Result**: ✅ Significant (p < 0.05) *

### Pairwise Effect Sizes (Cohen's d)

**Large effects (|d| ≥ 0.8)**:
- Spain vs Japan: d=2.847
- Spain vs UK: d=1.973
- Spain vs France: d=nan
- Japan vs UK: d=-4.183
- Japan vs France: d=nan
- UK vs France: d=nan

```
           pair  cohens_d magnitude  n1  n2
 Spain vs Japan  2.846562     Large   2   2
    Spain vs UK  1.973032     Large   2   4
Spain vs France       NaN     Large   2   1
    Japan vs UK -4.182561     Large   2   4
Japan vs France       NaN     Large   2   1
   UK vs France       NaN     Large   4   1
```

---

## Mean Length

### Bootstrap 95% Confidence Intervals

```
 group  n      mean    ci_low   ci_high  ci_width    stderr
France  1 36.941492 36.941492 36.941492  0.000000       NaN
 Japan  2 16.084578 15.700124 16.469033  0.768909  0.384454
 Spain  2 38.655463 26.588095 50.722831 24.134735 12.067368
    UK  4 35.138543 28.060376 44.741868 16.681492  5.149374
```

### Welch's ANOVA

- F-statistic: 1.801
- p-value: 0.2636
- **Result**: ❌ Not significant (p ≥ 0.05)

### Pairwise Effect Sizes (Cohen's d)

**Large effects (|d| ≥ 0.8)**:
- Spain vs Japan: d=1.869
- Spain vs France: d=nan
- Japan vs UK: d=-2.135
- Japan vs France: d=nan
- UK vs France: d=nan

```
           pair  cohens_d magnitude  n1  n2
 Spain vs Japan  1.869458     Large   2   2
    Spain vs UK  0.284924     Small   2   4
Spain vs France       NaN     Large   2   1
    Japan vs UK -2.135348     Large   2   4
Japan vs France       NaN     Large   2   1
   UK vs France       NaN     Large   4   1
```

---

## Mean Cpm

### Bootstrap 95% Confidence Intervals

```
 group  n      mean    ci_low   ci_high  ci_width   stderr
France  1 25.750000 25.750000 25.750000  0.000000      NaN
 Japan  2 19.060526 11.470449 26.650602 15.180153 7.590077
 Spain  2 27.176682 26.619718 27.733645  1.113927 0.556963
    UK  4 26.417118 23.396277 29.437960  6.041683 1.846014
```

### Welch's ANOVA

- F-statistic: 0.941
- p-value: 0.4868
- **Result**: ❌ Not significant (p ≥ 0.05)

### Pairwise Effect Sizes (Cohen's d)

**Large effects (|d| ≥ 0.8)**:
- Spain vs Japan: d=1.066
- Spain vs France: d=nan
- Japan vs UK: d=-1.178
- Japan vs France: d=nan
- UK vs France: d=nan

```
           pair  cohens_d magnitude  n1  n2
 Spain vs Japan  1.066444     Large   2   2
    Spain vs UK  0.235775     Small   2   4
Spain vs France       NaN     Large   2   1
    Japan vs UK -1.177576     Large   2   4
Japan vs France       NaN     Large   2   1
   UK vs France       NaN     Large   4   1
```

---

## Burst Freq Per Hour

### Bootstrap 95% Confidence Intervals

```
 group  n     mean   ci_low   ci_high  ci_width   stderr
France  1 0.919775 0.919775  0.919775  0.000000      NaN
 Japan  2 7.563183 3.254973 11.871393  8.616420 4.308210
 Spain  2 1.082762 0.952381  1.213142  0.260761 0.130381
    UK  4 1.361289 0.694028  2.028549  1.334521 0.406593
```

### Welch's ANOVA

- F-statistic: 2.675
- p-value: 0.1582
- **Result**: ❌ Not significant (p ≥ 0.05)

### Pairwise Effect Sizes (Cohen's d)

**Large effects (|d| ≥ 0.8)**:
- Spain vs Japan: d=-1.504
- Spain vs France: d=nan
- Japan vs UK: d=1.984
- Japan vs France: d=nan
- UK vs France: d=nan

```
           pair  cohens_d magnitude  n1  n2
 Spain vs Japan -1.503514     Large   2   2
    Spain vs UK -0.392154     Small   2   4
Spain vs France       NaN     Large   2   1
    Japan vs UK  1.983523     Large   2   4
Japan vs France       NaN     Large   2   1
   UK vs France       NaN     Large   4   1
```

---

## Mean Burst Duration

### Bootstrap 95% Confidence Intervals

```
 group  n  mean  ci_low  ci_high  ci_width  stderr
France  1 10.00   10.00     10.0      0.00     NaN
 Japan  2 10.00   10.00     10.0      0.00    0.00
 Spain  2 10.00   10.00     10.0      0.00    0.00
    UK  4  9.75    9.25     10.0      0.75    0.25
```

### Welch's ANOVA

- F-statistic: 0.309
- p-value: 0.8189
- **Result**: ❌ Not significant (p ≥ 0.05)

### Pairwise Effect Sizes (Cohen's d)

**Large effects (|d| ≥ 0.8)**:
- Spain vs Japan: d=nan
- Spain vs France: d=nan
- Japan vs France: d=nan
- UK vs France: d=nan

```
           pair  cohens_d magnitude  n1  n2
 Spain vs Japan       NaN     Large   2   2
    Spain vs UK   0.57735    Medium   2   4
Spain vs France       NaN     Large   2   1
    Japan vs UK   0.57735    Medium   2   4
Japan vs France       NaN     Large   2   1
   UK vs France       NaN     Large   4   1
```

---

## Mean Burst Intensity

### Bootstrap 95% Confidence Intervals

```
 group  n     mean   ci_low  ci_high  ci_width   stderr
France  1 3.805825 3.805825 3.805825  0.000000      NaN
 Japan  2 6.163644 4.165009 8.162278  3.997269 1.998635
 Spain  2 3.258253 2.722325 3.794180  1.071855 0.535927
    UK  4 4.819821 4.178007 5.461634  1.283627 0.401714
```

### Welch's ANOVA

- F-statistic: 1.474
- p-value: 0.3281
- **Result**: ❌ Not significant (p ≥ 0.05)

### Pairwise Effect Sizes (Cohen's d)

**Large effects (|d| ≥ 0.8)**:
- Spain vs Japan: d=-1.404
- Spain vs UK: d=-1.971
- Spain vs France: d=nan
- Japan vs UK: d=0.853
- Japan vs France: d=nan
- UK vs France: d=nan

```
           pair  cohens_d magnitude  n1  n2
 Spain vs Japan -1.404085     Large   2   2
    Spain vs UK -1.970941     Large   2   4
Spain vs France       NaN     Large   2   1
    Japan vs UK  0.853089     Large   2   4
Japan vs France       NaN     Large   2   1
   UK vs France       NaN     Large   4   1
```

---
