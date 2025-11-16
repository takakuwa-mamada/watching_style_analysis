================================================================================
改善された統計分析レポート
================================================================================

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
    Spain  2 1.260885 1.120977 1.400794  0.279816 0.098930
    Japan  3 0.149977 0.031193 0.381432  0.350239 0.094502
       UK  4 1.212951 0.663690 1.762212  1.098523 0.279633
   France  1 0.894481 0.894481 0.894481  0.000000      NaN
      USA  1 0.414804 0.414804 0.414804  0.000000      NaN
Dominican  1 1.426356 1.426356 1.426356  0.000000      NaN
```

### Welch's ANOVA

- F-statistic: 2.493
- p-value: 0.1485
- **Result**: ❌ Not significant (p ≥ 0.05)

### Pairwise Effect Sizes (Cohen's d)

**Large effects (|d| ≥ 0.8)**:
- Spain vs Japan: d=5.566
- Spain vs France: d=nan
- Spain vs USA: d=nan
- Spain vs Dominican: d=nan
- Japan vs UK: d=-2.060
- Japan vs France: d=nan
- Japan vs USA: d=nan
- Japan vs Dominican: d=nan
- UK vs France: d=nan
- UK vs USA: d=nan
- UK vs Dominican: d=nan
- France vs USA: d=nan
- France vs Dominican: d=nan
- USA vs Dominican: d=nan

```
               pair  cohens_d  magnitude  n1  n2
     Spain vs Japan  5.565572      Large   2   3
        Spain vs UK  0.084399 Negligible   2   4
    Spain vs France       NaN      Large   2   1
       Spain vs USA       NaN      Large   2   1
 Spain vs Dominican       NaN      Large   2   1
        Japan vs UK -2.059867      Large   3   4
    Japan vs France       NaN      Large   3   1
       Japan vs USA       NaN      Large   3   1
 Japan vs Dominican       NaN      Large   3   1
       UK vs France       NaN      Large   4   1
          UK vs USA       NaN      Large   4   1
    UK vs Dominican       NaN      Large   4   1
      France vs USA       NaN      Large   1   1
France vs Dominican       NaN      Large   1   1
   USA vs Dominican       NaN      Large   1   1
```

---

## Laugh Rate

### Bootstrap 95% Confidence Intervals

```
    group  n     mean   ci_low  ci_high  ci_width   stderr
    Spain  2 0.021626 0.002646 0.040607  0.037961 0.013421
    Japan  3 0.036707 0.018454 0.047815  0.029362 0.007510
       UK  4 0.012199 0.008150 0.018377  0.010228 0.002650
   France  1 0.010220 0.010220 0.010220  0.000000      NaN
      USA  1 0.029319 0.029319 0.029319  0.000000      NaN
Dominican  1 0.000779 0.000779 0.000779  0.000000      NaN
```

### Welch's ANOVA

- F-statistic: 1.466
- p-value: 0.3247
- **Result**: ❌ Not significant (p ≥ 0.05)

### Pairwise Effect Sizes (Cohen's d)

**Large effects (|d| ≥ 0.8)**:
- Spain vs France: d=nan
- Spain vs USA: d=nan
- Spain vs Dominican: d=nan
- Japan vs UK: d=2.201
- Japan vs France: d=nan
- Japan vs USA: d=nan
- Japan vs Dominican: d=nan
- UK vs France: d=nan
- UK vs USA: d=nan
- UK vs Dominican: d=nan
- France vs USA: d=nan
- France vs Dominican: d=nan
- USA vs Dominican: d=nan

```
               pair  cohens_d magnitude  n1  n2
     Spain vs Japan -0.745356    Medium   2   3
        Spain vs UK  0.653300    Medium   2   4
    Spain vs France       NaN     Large   2   1
       Spain vs USA       NaN     Large   2   1
 Spain vs Dominican       NaN     Large   2   1
        Japan vs UK  2.200938     Large   3   4
    Japan vs France       NaN     Large   3   1
       Japan vs USA       NaN     Large   3   1
 Japan vs Dominican       NaN     Large   3   1
       UK vs France       NaN     Large   4   1
          UK vs USA       NaN     Large   4   1
    UK vs Dominican       NaN     Large   4   1
      France vs USA       NaN     Large   1   1
France vs Dominican       NaN     Large   1   1
   USA vs Dominican       NaN     Large   1   1
```

---

## Exclamation Rate

### Bootstrap 95% Confidence Intervals

```
    group  n     mean   ci_low  ci_high  ci_width   stderr
    Spain  2 0.104352 0.068519 0.140185  0.071667 0.025338
    Japan  3 0.005426 0.000000 0.011950  0.011950 0.002852
       UK  4 0.049653 0.037940 0.058963  0.021023 0.005625
   France  1 0.112417 0.112417 0.112417  0.000000      NaN
      USA  1 0.307212 0.307212 0.307212  0.000000      NaN
Dominican  1 0.129939 0.129939 0.129939  0.000000      NaN
```

### Welch's ANOVA

- F-statistic: 29.245
- p-value: 0.0004
- **Result**: ✅ Highly significant (p < 0.001) ****

### Pairwise Effect Sizes (Cohen's d)

**Large effects (|d| ≥ 0.8)**:
- Spain vs Japan: d=3.334
- Spain vs UK: d=1.973
- Spain vs France: d=nan
- Spain vs USA: d=nan
- Spain vs Dominican: d=nan
- Japan vs UK: d=-4.108
- Japan vs France: d=nan
- Japan vs USA: d=nan
- Japan vs Dominican: d=nan
- UK vs France: d=nan
- UK vs USA: d=nan
- UK vs Dominican: d=nan
- France vs USA: d=nan
- France vs Dominican: d=nan
- USA vs Dominican: d=nan

```
               pair  cohens_d magnitude  n1  n2
     Spain vs Japan  3.333981     Large   2   3
        Spain vs UK  1.973032     Large   2   4
    Spain vs France       NaN     Large   2   1
       Spain vs USA       NaN     Large   2   1
 Spain vs Dominican       NaN     Large   2   1
        Japan vs UK -4.108119     Large   3   4
    Japan vs France       NaN     Large   3   1
       Japan vs USA       NaN     Large   3   1
 Japan vs Dominican       NaN     Large   3   1
       UK vs France       NaN     Large   4   1
          UK vs USA       NaN     Large   4   1
    UK vs Dominican       NaN     Large   4   1
      France vs USA       NaN     Large   1   1
France vs Dominican       NaN     Large   1   1
   USA vs Dominican       NaN     Large   1   1
```

---

## Mean Length

### Bootstrap 95% Confidence Intervals

```
    group  n      mean    ci_low   ci_high  ci_width   stderr
    Spain  2 38.655463 26.588095 50.722831 24.134735 8.532918
    Japan  3 14.639075 11.748069 16.469033  4.720963 1.194082
       UK  4 35.138543 28.060376 44.741868 16.681492 4.459488
   France  1 36.941492 36.941492 36.941492  0.000000      NaN
      USA  1 31.047778 31.047778 31.047778  0.000000      NaN
Dominican  1 27.499292 27.499292 27.499292  0.000000      NaN
```

### Welch's ANOVA

- F-statistic: 1.964
- p-value: 0.2176
- **Result**: ❌ Not significant (p ≥ 0.05)

### Pairwise Effect Sizes (Cohen's d)

**Large effects (|d| ≥ 0.8)**:
- Spain vs Japan: d=2.385
- Spain vs France: d=nan
- Spain vs USA: d=nan
- Spain vs Dominican: d=nan
- Japan vs UK: d=-2.519
- Japan vs France: d=nan
- Japan vs USA: d=nan
- Japan vs Dominican: d=nan
- UK vs France: d=nan
- UK vs USA: d=nan
- UK vs Dominican: d=nan
- France vs USA: d=nan
- France vs Dominican: d=nan
- USA vs Dominican: d=nan

```
               pair  cohens_d magnitude  n1  n2
     Spain vs Japan  2.385491     Large   2   3
        Spain vs UK  0.284924     Small   2   4
    Spain vs France       NaN     Large   2   1
       Spain vs USA       NaN     Large   2   1
 Spain vs Dominican       NaN     Large   2   1
        Japan vs UK -2.519400     Large   3   4
    Japan vs France       NaN     Large   3   1
       Japan vs USA       NaN     Large   3   1
 Japan vs Dominican       NaN     Large   3   1
       UK vs France       NaN     Large   4   1
          UK vs USA       NaN     Large   4   1
    UK vs Dominican       NaN     Large   4   1
      France vs USA       NaN     Large   1   1
France vs Dominican       NaN     Large   1   1
   USA vs Dominican       NaN     Large   1   1
```

---

## Mean Cpm

### Bootstrap 95% Confidence Intervals

```
    group  n      mean    ci_low   ci_high  ci_width    stderr
    Spain  2 27.176682 26.619718 27.733645  1.113927  0.393833
    Japan  3 38.017717 11.470449 75.932099 64.461650 15.886644
       UK  4 26.417118 23.396277 29.437960  6.041683  1.598695
   France  1 25.750000 25.750000 25.750000  0.000000       NaN
      USA  1 47.226496 47.226496 47.226496  0.000000       NaN
Dominican  1 50.981949 50.981949 50.981949  0.000000       NaN
```

### Welch's ANOVA

- F-statistic: 0.464
- p-value: 0.7914
- **Result**: ❌ Not significant (p ≥ 0.05)

### Pairwise Effect Sizes (Cohen's d)

**Large effects (|d| ≥ 0.8)**:
- Spain vs France: d=nan
- Spain vs USA: d=nan
- Spain vs Dominican: d=nan
- Japan vs France: d=nan
- Japan vs USA: d=nan
- Japan vs Dominican: d=nan
- UK vs France: d=nan
- UK vs USA: d=nan
- UK vs Dominican: d=nan
- France vs USA: d=nan
- France vs Dominican: d=nan
- USA vs Dominican: d=nan

```
               pair  cohens_d magnitude  n1  n2
     Spain vs Japan -0.393930     Small   2   3
        Spain vs UK  0.235775     Small   2   4
    Spain vs France       NaN     Large   2   1
       Spain vs USA       NaN     Large   2   1
 Spain vs Dominican       NaN     Large   2   1
        Japan vs UK  0.539433    Medium   3   4
    Japan vs France       NaN     Large   3   1
       Japan vs USA       NaN     Large   3   1
 Japan vs Dominican       NaN     Large   3   1
       UK vs France       NaN     Large   4   1
          UK vs USA       NaN     Large   4   1
    UK vs Dominican       NaN     Large   4   1
      France vs USA       NaN     Large   1   1
France vs Dominican       NaN     Large   1   1
   USA vs Dominican       NaN     Large   1   1
```

---

## Burst Freq Per Hour

### Bootstrap 95% Confidence Intervals

```
    group  n     mean   ci_low  ci_high  ci_width   stderr
    Spain  2 0.491641 0.422535 0.560748  0.138212 0.048865
    Japan  3 1.296217 0.740741 1.702128  0.961387 0.234684
       UK  4 0.568850 0.339828 0.820126  0.480298 0.129921
   France  1 0.394737 0.394737 0.394737  0.000000      NaN
      USA  1 1.282051 1.282051 1.282051  0.000000      NaN
Dominican  1 0.649819 0.649819 0.649819  0.000000      NaN
```

### Welch's ANOVA

- F-statistic: 2.415
- p-value: 0.1566
- **Result**: ❌ Not significant (p ≥ 0.05)

### Pairwise Effect Sizes (Cohen's d)

**Large effects (|d| ≥ 0.8)**:
- Spain vs Japan: d=-1.961
- Spain vs France: d=nan
- Spain vs USA: d=nan
- Spain vs Dominican: d=nan
- Japan vs UK: d=1.859
- Japan vs France: d=nan
- Japan vs USA: d=nan
- Japan vs Dominican: d=nan
- UK vs France: d=nan
- UK vs USA: d=nan
- UK vs Dominican: d=nan
- France vs USA: d=nan
- France vs Dominican: d=nan
- USA vs Dominican: d=nan

```
               pair  cohens_d magnitude  n1  n2
     Spain vs Japan -1.960556     Large   2   3
        Spain vs UK -0.292019     Small   2   4
    Spain vs France       NaN     Large   2   1
       Spain vs USA       NaN     Large   2   1
 Spain vs Dominican       NaN     Large   2   1
        Japan vs UK  1.858628     Large   3   4
    Japan vs France       NaN     Large   3   1
       Japan vs USA       NaN     Large   3   1
 Japan vs Dominican       NaN     Large   3   1
       UK vs France       NaN     Large   4   1
          UK vs USA       NaN     Large   4   1
    UK vs Dominican       NaN     Large   4   1
      France vs USA       NaN     Large   1   1
France vs Dominican       NaN     Large   1   1
   USA vs Dominican       NaN     Large   1   1
```

---

## Mean Burst Duration

### Bootstrap 95% Confidence Intervals

```
    group  n     mean   ci_low  ci_high  ci_width   stderr
    Spain  2 3.000000 3.000000 3.000000  0.000000 0.000000
    Japan  3 5.111111 2.000000 7.333333  5.333333 1.308409
       UK  4 3.541667 2.000000 6.125000  4.125000 1.150747
   France  1 4.000000 4.000000 4.000000  0.000000      NaN
      USA  1 7.200000 7.200000 7.200000  0.000000      NaN
Dominican  1 8.666667 8.666667 8.666667  0.000000      NaN
```

### Welch's ANOVA

- F-statistic: 1.116
- p-value: 0.4406
- **Result**: ❌ Not significant (p ≥ 0.05)

### Pairwise Effect Sizes (Cohen's d)

**Large effects (|d| ≥ 0.8)**:
- Spain vs Japan: d=-0.932
- Spain vs France: d=nan
- Spain vs USA: d=nan
- Spain vs Dominican: d=nan
- Japan vs France: d=nan
- Japan vs USA: d=nan
- Japan vs Dominican: d=nan
- UK vs France: d=nan
- UK vs USA: d=nan
- UK vs Dominican: d=nan
- France vs USA: d=nan
- France vs Dominican: d=nan
- USA vs Dominican: d=nan

```
               pair  cohens_d magnitude  n1  n2
     Spain vs Japan -0.931552     Large   2   3
        Spain vs UK -0.235354     Small   2   4
    Spain vs France       NaN     Large   2   1
       Spain vs USA       NaN     Large   2   1
 Spain vs Dominican       NaN     Large   2   1
        Japan vs UK  0.580124    Medium   3   4
    Japan vs France       NaN     Large   3   1
       Japan vs USA       NaN     Large   3   1
 Japan vs Dominican       NaN     Large   3   1
       UK vs France       NaN     Large   4   1
          UK vs USA       NaN     Large   4   1
    UK vs Dominican       NaN     Large   4   1
      France vs USA       NaN     Large   1   1
France vs Dominican       NaN     Large   1   1
   USA vs Dominican       NaN     Large   1   1
```

---

## Mean Burst Intensity

### Bootstrap 95% Confidence Intervals

```
    group  n     mean   ci_low  ci_high  ci_width   stderr
    Spain  2 3.453589 2.812468 4.094709  1.282241 0.453341
    Japan  3 5.113972 2.963174 8.194971  5.231797 1.290296
       UK  4 4.809761 4.157887 5.461634  1.303747 0.354851
   France  1 3.805825 3.805825 3.805825  0.000000      NaN
      USA  1 5.810298 5.810298 5.810298  0.000000      NaN
Dominican  1 7.453618 7.453618 7.453618  0.000000      NaN
```

### Welch's ANOVA

- F-statistic: 0.868
- p-value: 0.5520
- **Result**: ❌ Not significant (p ≥ 0.05)

### Pairwise Effect Sizes (Cohen's d)

**Large effects (|d| ≥ 0.8)**:
- Spain vs UK: d=-1.610
- Spain vs France: d=nan
- Spain vs USA: d=nan
- Spain vs Dominican: d=nan
- Japan vs France: d=nan
- Japan vs USA: d=nan
- Japan vs Dominican: d=nan
- UK vs France: d=nan
- UK vs USA: d=nan
- UK vs Dominican: d=nan
- France vs USA: d=nan
- France vs Dominican: d=nan
- USA vs Dominican: d=nan

```
               pair  cohens_d  magnitude  n1  n2
     Spain vs Japan -0.723370     Medium   2   3
        Spain vs UK -1.610393      Large   2   4
    Spain vs France       NaN      Large   2   1
       Spain vs USA       NaN      Large   2   1
 Spain vs Dominican       NaN      Large   2   1
        Japan vs UK  0.164989 Negligible   3   4
    Japan vs France       NaN      Large   3   1
       Japan vs USA       NaN      Large   3   1
 Japan vs Dominican       NaN      Large   3   1
       UK vs France       NaN      Large   4   1
          UK vs USA       NaN      Large   4   1
    UK vs Dominican       NaN      Large   4   1
      France vs USA       NaN      Large   1   1
France vs Dominican       NaN      Large   1   1
   USA vs Dominican       NaN      Large   1   1
```

---
