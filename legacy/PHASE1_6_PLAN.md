# Phase 1.6: 動的top_k調整による改善

## 日付: 2025年11月10日

## Phase 1.5までの失敗

### Phase 1
- **変更**: `max_features=2000` → `3000`
- **結果**: Combined score 0.237（変化なし）❌

### Phase 1.5
- **変更**: `max_df=0.95` → `1.0`
- **結果**: Combined score 0.237（変化なし）❌

## 根本原因の発見

### ターミナル出力からの重要な発見
```
小規模イベント:
  Event: 12 comments, 30 topics ← 異常
  Event: 15 comments, 30 topics ← 異常
  Event: 21 comments, 30 topics ← 異常

正常なイベント:
  Event: 30 comments, 1 topics ← 正常
  Event: 31 comments, 3 topics ← 正常
  Event: 42 comments, 6 topics ← 正常
```

### 問題点
- **`top_k=30`がハードコード**されている（line 2185）
- 小規模イベント（10-20コメント）でも強制的に30 topicsを抽出
- 結果: ノイズがtopicとして含まれ、Topic Jaccardが0になる（82.1%）

## Phase 1.6 の変更内容

### コード変更
```python
# 変更前（line 2185）
ngram_topics = extract_ngram_topics_direct(comments, top_k=30)

# 変更後（Phase 1.6）
dynamic_top_k = max(5, min(30, len(comments) // 2))  # コメント数の1/2
ngram_topics = extract_ngram_topics_direct(comments, top_k=dynamic_top_k)
```

### 動的top_kのロジック
- **基本**: `top_k = len(comments) // 2`（コメント数の半分）
- **最小値**: 5（最低5 topicsは抽出）
- **最大値**: 30（上限は維持）

### 例
| コメント数 | 旧top_k | 新top_k | 改善 |
|-----------|---------|---------|------|
| 10 | 30 | 5 | ✅ ノイズ削減 |
| 20 | 30 | 10 | ✅ ノイズ削減 |
| 40 | 30 | 20 | ✅ 適切な数 |
| 60 | 30 | 30 | = 上限維持 |
| 100 | 30 | 30 | = 上限維持 |

## 期待される効果

### 定量的目標
1. **Topic coverage**: 17.9% → **35-45%**
   - 理由: 無意味なノイズが削減され、有意義なtopicのみが残る
   - 結果: Topic Jaccard > 0 のペアが増加

2. **Combined score**: 0.237 → **0.30-0.35**
   - Topic coverageの改善がcombined scoreに反映される
   - Topic重み30%の効果が発揮される

3. **Perfect matches**: 1 → **2-3**
   - Event 56↔59以外にも完全一致が発生する可能性

### November目標との比較
| Metric | Baseline | Phase 1.6目標 | November目標 | 達成率 |
|--------|----------|---------------|--------------|--------|
| Avg Similarity | 0.237 | 0.32 | 0.350 | 91% |
| Topic Coverage | 17.9% | 40% | 35.0% | 114% ✅ |
| Perfect Matches | 1 | 2 | 3 | 67% |

## 実行計画

### ステップ1: Phase 1.6実行（今すぐ）
```bash
cd "g:\マイドライブ\大学\4年\ゼミ\watching_style_analysis"
python event_comparison.py --folder "data\football\game4" --pattern "*.csv" --peak-pad 3 --embedding-match-th 0.70
```

### ステップ2: 結果分析
```bash
python diagnose_phase1_failure.py
```

### ステップ3: 成功判定
- **成功**: Topic coverage ≥ 35% → Phase 2（重み最適化）へ
- **部分成功**: Topic coverage 25-34% → Phase 2を慎重に実行
- **失敗**: Topic coverage < 25% → さらなる調査が必要

## Phase 2 準備（Phase 1.6成功時）

### 重み最適化
```python
# 現在
W_EMBEDDING = 0.40  # 40%
W_LEXICAL = 0.20    # 20%
W_TOPIC = 0.30      # 30%
W_TEMPORAL = 0.10   # 10%

# Phase 2最適化
W_EMBEDDING = 0.30  # 30%
W_LEXICAL = 0.15    # 15%
W_TOPIC = 0.45      # 45% ← Topic重視
W_TEMPORAL = 0.10   # 10%
```

### 期待される追加効果
- Combined score: +0.05-0.10
- 最終目標: Combined score ≥ 0.37（November目標0.35を超える）

## タイムライン
- **Phase 1.6実行**: 30-60分
- **結果分析**: 10分
- **Phase 2準備**: 10分
- **Phase 2実行**: 30-60分
- **合計**: 約2-3時間

## リスク管理
- Phase 1.6が失敗した場合の代替案:
  1. `top_k = len(comments) // 3`（より少ないtopic数）
  2. `top_k = min(10, len(comments) // 2)`（最大10に制限）
  3. Topic抽出方法の根本的見直し（BERTopic導入など）

---

**Phase 1.6は最後のチャンス。これが成功すればNovember目標達成が見えてくる。**
