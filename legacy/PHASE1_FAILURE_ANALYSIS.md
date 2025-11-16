# Phase 1 失敗分析と次のステップ

## 日付: 2025年11月10日

## Phase 1 実行内容
- **変更**: `max_features=2000` → `max_features=3000`
- **目的**: Topic coverageを17.9%→25%に改善
- **実行時間**: 約30-60分

## Phase 1 結果

### 定量的結果
```
Total pairs: 28
Average combined_score: 0.237 (変化なし, +0.000)
Topic coverage: 17.9% (変化なし, 5/28 pairs)
Perfect matches: 1 (Event 56↔59)
High-quality pairs (>=0.5): 1 (3.6%)
```

### 各成分の統計
```
Embedding類似度    : 0.4706 (±0.1817)
Topic Jaccard     : 0.0478 (±0.1913)
Lexical類似度     : 0.1292 (±0.0774)
Temporal相関      : 0.1346 (±0.2267)
最終スコア        : 0.2375 (±0.1458)
```

### Topic Jaccard分析
- **topic_jaccard = 0**: 23/28 ペア (82.1%)
- **topic_jaccard > 0**: 5/28 ペア (17.9%)
- **topic_jaccard = 1.0**: 1/28 ペア (3.6%) - Event 56↔59のみ

### Combined Score分布
- **Low (<0.3)**: 24/28 ペア (85.7%)
- **Mid (0.3-0.5)**: 3/28 ペア (10.7%)
- **High (>=0.5)**: 1/28 ペア (3.6%)

## 失敗の原因分析

### 根本原因
**`max_features`の増加はTopic matchingに影響しなかった**

### 詳細な原因
1. **min_df/max_dfパラメータが厳しすぎる**
   - 現在: `min_df=1, max_df=0.95`
   - 問題: 小規模イベント（10-20コメント）でトピックが抽出できない
   - 証拠: "After pruning, no terms remain" 警告が多数発生

2. **max_featuresはEmbedding類似度に影響しない**
   - SentenceTransformerベースのembeddingはTfidfVectorizerと独立
   - max_features増加はTopic抽出のみに影響（理論上）
   - しかし、min_df/max_dfで先にフィルタリングされるため効果なし

3. **小規模イベントの問題**
   - 10-20コメントのイベントが多数
   - max_df=0.95 → 1つのイベント内で2回以上出現する語のみ残る
   - 結果: ほとんどの語が除外される

## Phase 1の評価
- **総合評価**: ❌ **失敗**
- **Success Rate**: 0% (目標を一切達成せず)
- **Baseline比較**: 改善なし（+0.000）

## 次のステップ: Phase 1.5

### 優先度1: min_df/max_df 調整（即実行）
**変更内容:**
```python
# 現在
max_df=0.95,  # 95%以上の文書に出現する語は除外
min_df=1,     # 最低1回出現する語のみ

# 提案（Phase 1.5）
max_df=1.0,   # 100%出現する語も含める（小規模イベント対応）
min_df=1,     # 最低1回出現する語のみ（維持）
```

**期待される効果:**
- 小規模イベント（10-20コメント）でのTopic抽出成功率向上
- "After pruning, no terms remain" 警告の減少
- Topic coverage: 17.9% → 30-40% (予測)
- Combined score: 0.237 → 0.28-0.32 (予測)

**実行時間:** 約30-60分

### 優先度2: Phase 2（重み最適化）
Phase 1.5の結果を見てから実行を判断

**変更内容:**
```python
# 現在
W_EMBEDDING = 0.40  # 40%
W_LEXICAL = 0.20    # 20%
W_TOPIC = 0.30      # 30%
W_TEMPORAL = 0.10   # 10%

# Phase 2最適化（Phase2_optimize.py分析結果）
W_EMBEDDING = 0.30  # 30%
W_LEXICAL = 0.15    # 15%
W_TOPIC = 0.45      # 45% ← Topic重視
W_TEMPORAL = 0.10   # 10%
```

**期待される効果:**
- 既存のTopic matchを最大限活用
- Better separation (F1=0.46)
- Combined score: +0.05-0.10の追加改善

## 実行計画

### ステップ1: Phase 1.5実行（今すぐ）
1. `event_comparison.py`のmax_dfを0.95→1.0に変更（2箇所）
2. 変更をバックアップ
3. 実行（30-60分）
4. 結果分析

### ステップ2: Phase 1.5評価
- Topic coverage目標: 30%以上
- Combined score目標: 0.28以上
- 成功なら→Phase 2へ
- 失敗なら→min_df=0も試す

### ステップ3: Phase 2実行（Phase 1.5成功時）
1. 重みパラメータを最適値に変更
2. 実行（30-60分）
3. 結果分析
4. November目標（avg=0.35, topic=35%）達成確認

## 時間見積もり
- Phase 1.5: 実装10分 + 実行60分 + 分析10分 = 80分
- Phase 2: 実装10分 + 実行60分 + 分析10分 = 80分
- **合計**: 約3時間（慎重に進める）

## November目標との比較
| Metric | Baseline | Current | Target | Progress |
|--------|----------|---------|--------|----------|
| Avg Similarity | 0.237 | 0.237 | 0.350 | 0% ❌ |
| Topic Coverage | 17.9% | 17.9% | 35.0% | 0% ❌ |
| Perfect Matches | 1 | 1 | 3 | 33% ⚠️ |

**現状**: 目標達成まで遠い（Phase 1.5とPhase 2の実行が必須）

## 結論
Phase 1は失敗したが、**根本原因を特定できた**ことは成功。
次はPhase 1.5（max_df調整）を実行し、小規模イベントのTopic抽出を改善する。
