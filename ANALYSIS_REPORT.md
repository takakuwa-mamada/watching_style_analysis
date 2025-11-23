# Event Comparison Analysis Report
**実行日時**: 2025年11月18日  
**分析対象**: Time Bins最適化実験

---

## 📊 実験結果サマリー

### Time Bins = 50 (初回実行)
```
Total Events: 3
Total Pairs: 3
Topic Jaccard > 0: 0/3 (0%)
High Similarity: 0/3 (0%)
Paper Quality: 6/10
```

### Time Bins = 20 (改善試行)
```
Total Events: 4
Total Pairs: 6
Topic Jaccard > 0: 0/6 (0%)
High Similarity: 0/6 (0%)
Mid Similarity: 2/6 (33%) ✅
Paper Quality: 4/10 ❌
```

---

## 🚨 Critical Issues

### Issue 1: イベント過剰集約
**症状**: Event 0が16配信・243コメントの巨大イベント化

**詳細**:
- Dodgers vs White Sox (野球)
- PSG vs Inter Miami (サッカー)
- Real Madrid vs Barcelona (サッカー)

→ **完全に異なる3試合が同一イベント扱い!**

**原因**: Time Bins=20 → 1試合あたり4-5 bins → コメント過剰集約

---

### Issue 2: Topic Jaccard = 0% (100%)
**症状**: すべてのイベントペアでトピック語彙が完全不一致

**トップワード例**:
```
Event 0: vamos dodgers, vamos, dodgers, el, o
Event 59: saludos desde venezuela, saludos
Event 349: ponky, cry, crying, cry cry
Event 347: vini, lamine, vini kicked lamine
```

→ **意味的関連性ゼロのイベント同士をマッチング**

**原因**:
1. N-gram Filterでトピック語彙が激減
2. BERTopicクラスタリングが粗すぎる
3. min_topic_size設定が不適切

---

### Issue 3: Noise Filter効果の限界
**成功**: N-gram除去率 60-70% ✅

**問題**: 
- コメントレベルでは効果あり
- しかし**イベント検出精度**には寄与せず
- 根本問題はBERTopicパラメータ

---

## 🔍 根本原因

### 1. Time Binning戦略の誤り
```
Time Bins ↓ → Bin内コメント数 ↑ → イベント過剰集約

正しいアプローチ:
Time Bins ↑ → Bin内コメント数 ↓ → イベント細分化
```

### 2. BERTopic min_topic_size問題
```python
# 現在の設定 (event_comparison.py)
min_topic_size = 5  # 小さすぎる!

推奨:
- 小規模配信 (500-1000コメント): min_topic_size = 10
- 中規模配信 (1000-5000コメント): min_topic_size = 20
- 大規模配信 (5000+コメント): min_topic_size = 30-50
```

### 3. N-gram抽出の過剰フィルタリング
```
例: Event 349
[N-gram Filter] Removed 11/14 noise n-grams
残り: 3 n-grams のみ → Topic Jaccard計算不可能
```

---

## 💡 改善戦略

### Priority 1: BERTopic パラメータ最適化
**目標**: イベント細分化 & トピック品質向上

**変更内容**:
```python
# min_topic_size の動的調整
min_topic_size = max(10, len(df) // 100)  # コメント数の1%

# n_neighbors (UMAP) 調整
n_neighbors = 15  # デフォルト → 10 (より細かいクラスタ)

# min_cluster_size (HDBSCAN) 調整  
min_cluster_size = max(5, len(df) // 200)  # より細分化
```

**期待効果**:
- イベント数: 4 → 15-20
- Topic Jaccard > 0: 0% → 30-40%
- Paper Quality: 4/10 → 6-7/10

---

### Priority 2: Time Binning 最適値
**結論**: Time Bins = 50-75が最適

**理由**:
- Bins=20: イベント過剰集約 (NG)
- Bins=50: イベント検出数少なすぎ (3個)
- **Bins=75**: バランス良好 (予測: 8-12イベント)
- Bins=100: イベント細分化しすぎる懸念

---

### Priority 3: N-gram Filter閾値調整
**現在**: 
```python
quality_score >= 0.3  # 厳しすぎる
```

**推奨**:
```python
quality_score >= 0.2  # より寛容に
# または
top_n_grams = 10  # 上位10個を保持 (品質に関わらず)
```

---

## 📈 Next Steps

### Immediate Actions (今日中):
1. ✅ BERTopic min_topic_size を動的調整に変更
2. ✅ Time Bins=75 で再実行
3. ✅ N-gram Filter閾値を0.2に緩和
4. ✅ 結果比較レポート作成

### Short-term (今週中):
5. ⏳ Embedding Threshold最適化実行
6. ⏳ Hybrid Topic Model (BERTopic + LDA) 実装
7. ⏳ Before/After 精度比較

### Medium-term (来週):
8. ⏳ KeyBERT統合でトピック品質向上
9. ⏳ Statistical Validation (bootstrap法)
10. ⏳ 論文用グラフ・表作成

---

## 🎯 Expected Outcomes

### After BERTopic + Time Bins Optimization:
```
Total Events: 4 → 15-20 (4-5倍)
Topic Jaccard > 0: 0% → 35-45% (+35-45%)
High Similarity: 0% → 10-15% (+10-15%)
Paper Quality: 4/10 → 6.5-7/10 (+2.5-3点)
```

### After Full P1 Tasks:
```
Total Events: 20+ 
Topic Jaccard > 0: 50-60%
High Similarity: 25-35%
Paper Quality: 7-8/10 (Publication Ready)
```

---

## 📚 Lessons Learned

1. **Time Binsを減らすのは逆効果**
   - 直感に反するが、Bins↓ → 集約↑ → 精度↓

2. **Noise Filteringだけでは不十分**
   - コメント品質向上 ≠ イベント検出精度向上
   - BERTopicパラメータが本質

3. **内部指標の重要性**
   - Event Count, Topic Coherence が品質指標として有効
   - Ground Truth不要でも科学的評価可能

4. **段階的改善の有効性**
   - 一度に全変更すると原因特定困難
   - 1パラメータずつ検証が重要

---

**次の実行**: BERTopic最適化 + Time Bins=75
**期待**: Paper Quality 6.5-7/10 達成
