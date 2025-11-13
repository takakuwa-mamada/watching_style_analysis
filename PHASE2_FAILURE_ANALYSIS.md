# Phase 2 Failure Analysis Report
# Date: 2025-11-10
# Author: Copilot Analysis

## Executive Summary

**Phase 2 FAILED**: Average combined_score decreased from 0.237 to 0.191 (-19.5%)

## What Happened

### Weight Changes (Phase 2)
- Embedding: 40% → 30% (⬇️ -10%)
- Lexical: 20% → 15% (⬇️ -5%)
- Topic: 40% → 55% (⬆️ +15%)

### Results
| Metric | Baseline (Phase 1.6) | Phase 2 | Change |
|--------|---------------------|---------|--------|
| Average combined_score | 0.237 | 0.191 | -0.046 (-19.5%) |
| November goal | 0.350 | 0.350 | Target |
| Achievement rate | 67.7% | 54.5% | ⬇️ -13.2% |

## Root Cause Analysis

### The Fatal Flaw

**Strategy**: Increase topic weight (40%→55%) to maximize Event 56↔59's perfect match

**Reality**: 
- Only **1 pair** (Event 56↔59) benefits from increased topic weight
- **27 pairs** (96.4%) suffer from decreased embedding weight
- 23/28 pairs (82.1%) have topic_jaccard = 0

### Mathematical Explanation

For pairs with **topic_jaccard = 0** (82.1% of all pairs):

**OLD formula (Phase 1.6)**:
```
score = embedding * 0.40 + 0 * 0.40 + lexical * 0.20
     = embedding * 0.40 + lexical * 0.20
```

**NEW formula (Phase 2)**:
```
score = embedding * 0.30 + 0 * 0.55 + lexical * 0.15
     = embedding * 0.30 + lexical * 0.15
```

**Result**: Score decreases by:
- `embedding * 0.10` (10% embedding loss)
- `lexical * 0.05` (5% lexical loss)

### Specific Examples

**Event 5 ↔ Event 6** (worst case):
- Embedding: 0.934 (very high)
- Topic: 0.083 (nearly zero)
- Lexical: 0.000
- OLD score: 0.934 * 0.4 + 0.083 * 0.4 + 0 * 0.2 = **0.407**
- NEW score: 0.934 * 0.3 + 0.083 * 0.55 + 0 * 0.15 = **0.326**
- Loss: **-0.081** (-19.9%)

**Event 56 ↔ Event 59** (only winner):
- Embedding: 0.917
- Topic: 1.000 (perfect)
- Lexical: 0.245
- OLD score: 0.917 * 0.4 + 1.0 * 0.4 + 0.245 * 0.2 = **0.816**
- NEW score: 0.917 * 0.3 + 1.0 * 0.55 + 0.245 * 0.15 = **0.862**
- Gain: **+0.046** (+5.6%)

### Net Effect

- **1 pair gained +0.046**
- **27 pairs lost collectively: -1.283** (average -0.048 per pair)
- **Net change: -0.046 overall**

## Why This Strategy Failed

1. **Wrong assumption**: Assumed increasing topic weight would help overall average
2. **Ignored majority**: 82.1% of pairs have no topic overlap (topic_jaccard = 0)
3. **Zero multiplication**: When topic = 0, increasing topic weight from 40%→55% has ZERO effect
4. **Collateral damage**: Decreasing embedding weight (40%→30%) hurt 96.4% of pairs

## Comparison with Terminal Output

The terminal output showed:
- `Average Similarity: 0.471`

But our analysis shows:
- `Average combined_score: 0.191`

**Explanation**: The 0.471 in terminal is **embedding_similarity average**, NOT combined_score average.

## Lesson Learned

**Golden Rule**: Never decrease the weight of a component that most pairs depend on (embedding), 
even to increase the weight of a component that helps only a few pairs (topic).

**Better Strategy**: 
- Accept data limitation (82.1% have no topic match)
- Keep embedding weight high (it's working well)
- Topic weight increase only helps if >50% of pairs have topic>0

## Recommendation

**Revert to Phase 1.6 weights** (embedding 0.4, lexical 0.2, topic 0.4):
- Better overall average (0.237 vs 0.191)
- Still 67.7% toward November goal
- More balanced approach

OR

**Try Phase 2.5** (embedding 0.45, lexical 0.15, topic 0.40):
- Increase embedding (most pairs depend on it)
- Slight decrease lexical (least important)
- Keep topic at 40% (balanced)
- Expected: Average >0.25

## Data Limitation Reality

The fundamental issue remains:
- Only 1 true similar pair (Event 56↔59) with shared discussion topic
- Other pairs have surface similarity only
- No amount of weight optimization can create topic matches that don't exist in the data

**November Goal (0.35) remains challenging** due to data constraints, not system limitations.
