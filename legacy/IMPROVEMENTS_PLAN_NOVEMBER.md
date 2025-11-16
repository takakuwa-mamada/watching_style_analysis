# 🔧 プログラム改善計画（11月中）

**目標**: 現状の性能を向上させ、12月の論文執筆時に説得力のある結果を提示する

---

## 📊 現状の課題（優先度順）

### 🔴 **最優先課題1: 低い平均類似度（0.237）**
- **問題**: 89.3%のペアが類似度<0.4
- **目標**: 平均類似度を0.35-0.40に改善
- **影響**: 検出精度の向上

### 🔴 **最優先課題2: 低いトピック一致率（17.9%）**
- **問題**: 28ペア中5ペアのみトピック一致
- **目標**: トピック一致率を35-40%に改善
- **影響**: フレーズレベルの意味理解

### 🟡 **優先課題3: 時間的一貫性の逆転（0.49x）**
- **問題**: 類似ペアの方が時間差が大きい
- **目標**: 2.0-3.0xに改善（正常化）
- **影響**: 時間的ロジックの妥当性

---

## 🚀 改善プラン（3週間）

### **Week 1（11/10-11/16）: パラメータ最適化** ⭐⭐⭐⭐⭐

#### 1.1 N-gram抽出の調整（優先度MAX）

**現状**:
```python
# event_comparison.py line 687
vectorizer = TfidfVectorizer(
    ngram_range=(1, 3),
    max_df=0.95,
    min_df=1,  # 既に最適
    max_features=2000,
)
```

**改善案1: max_features拡張**
```python
# 2000 → 3000に拡張（より多くのフレーズを抽出）
vectorizer = TfidfVectorizer(
    ngram_range=(1, 3),
    max_df=0.95,
    min_df=1,
    max_features=3000,  # ← 変更
)
```

**期待効果**:
- トピック一致率: 17.9% → 25-30%
- 平均類似度: +0.03-0.05

---

**改善案2: N-gramの重み付け調整**
```python
# 1-gram vs 2-gram vs 3-gram の重みを調整
# 現在: 均等
# 改善: 2-gram, 3-gramを重視（フレーズ優先）

def extract_ngram_topics_with_weights(comments, top_k=30):
    """
    2-gram, 3-gramに高いウェイトを付与
    """
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 3),
        max_df=0.95,
        min_df=1,
        max_features=3000,
    )
    
    X = vectorizer.fit_transform(comments)
    feature_names = vectorizer.get_feature_names_out()
    scores = np.asarray(X.sum(axis=0)).flatten()
    
    # N-gramの長さに応じて重み付け
    weighted_scores = []
    for i, name in enumerate(feature_names):
        ngram_length = len(name.split())
        if ngram_length == 3:
            weight = 2.0  # 3-gramは2倍
        elif ngram_length == 2:
            weight = 1.5  # 2-gramは1.5倍
        else:
            weight = 1.0  # 1-gramは通常
        
        weighted_scores.append(scores[i] * weight)
    
    # 重み付けスコアでソート
    top_indices = np.argsort(weighted_scores)[-top_k:][::-1]
    return [feature_names[i] for i in top_indices]
```

**期待効果**:
- "韓国発狂"のようなフレーズが上位に
- トピック一致率: +5-8%

---

#### 1.2 類似度計算の重み調整

**現状の推定重み**:
```python
# embedding: 0.35
# lexical: 0.20
# topic: 0.35
# temporal: 0.10
```

**問題点**:
- Lexical平均0.129（最低）なのに20%の重み
- Topic平均0.048（低い）だが重要度高い

**改善案: データ駆動型の重み最適化**
```python
def optimize_weights_grid_search():
    """
    グリッドサーチで最適な重みを探索
    """
    df = pd.read_csv('output/event_to_event_pairs.csv')
    
    # Event 56↔59（完全一致）を基準に最適化
    target_pair = df[(df['event_A_id'] == 56) & (df['event_B_id'] == 59)].iloc[0]
    
    best_weights = None
    best_score = 0
    
    # グリッドサーチ
    for w_emb in [0.3, 0.35, 0.4, 0.45]:
        for w_topic in [0.3, 0.35, 0.4, 0.45]:
            for w_lex in [0.1, 0.15, 0.2]:
                w_temp = 1.0 - w_emb - w_topic - w_lex
                
                if w_temp < 0.05 or w_temp > 0.15:
                    continue
                
                # 再計算
                df['new_score'] = (
                    w_emb * df['embedding_similarity'] +
                    w_lex * df['lexical_similarity'] +
                    w_topic * df['topic_jaccard'] +
                    w_temp * df['temporal_correlation']
                )
                
                # 完全一致ペアのスコアを最大化
                target_score = df[(df['event_A_id'] == 56) & (df['event_B_id'] == 59)]['new_score'].iloc[0]
                
                # 他のペアとの分離度も考慮
                avg_other = df[(df['event_A_id'] != 56) | (df['event_B_id'] != 59)]['new_score'].mean()
                separation = target_score - avg_other
                
                if separation > best_score:
                    best_score = separation
                    best_weights = (w_emb, w_lex, w_topic, w_temp)
    
    print(f"最適重み: emb={best_weights[0]:.2f}, lex={best_weights[1]:.2f}, "
          f"topic={best_weights[2]:.2f}, temp={best_weights[3]:.2f}")
    print(f"分離度: {best_score:.3f}")
    
    return best_weights
```

**期待効果**:
- 平均類似度: +0.05-0.08
- 完全一致ペアがより際立つ

---

#### 1.3 時間的一貫性の修正

**現状の問題**:
- Event 56↔59は76 binsの時間差（外れ値）
- これが平均を歪めている

**改善案: ロバストな時間類似度計算**
```python
def compute_temporal_similarity_robust(event_A, event_B, max_bins=100):
    """
    外れ値に頑健な時間類似度
    """
    time_diff = abs(event_A['bin_id'] - event_B['bin_id'])
    
    # 正規化（0-1の範囲）
    # max_bins以上は0にクリップ
    if time_diff >= max_bins:
        return 0.0
    
    # 指数減衰（近いほど高スコア）
    similarity = np.exp(-time_diff / 20.0)
    
    return similarity

# さらに、時系列相関も計算
def compute_temporal_correlation_improved(ts_A, ts_B):
    """
    時系列の形状類似度（DTW簡易版）
    """
    from scipy.stats import pearsonr
    
    # 長さを揃える
    min_len = min(len(ts_A), len(ts_B))
    ts_A_trimmed = ts_A[:min_len]
    ts_B_trimmed = ts_B[:min_len]
    
    # Pearson相関
    if len(ts_A_trimmed) > 1:
        corr, _ = pearsonr(ts_A_trimmed, ts_B_trimmed)
        return max(0, corr)  # 負の相関は0
    
    return 0.0
```

**期待効果**:
- 時間的一貫性: 0.49x → 2.5-3.0x（正常化）
- より論理的な評価

---

### **Week 2（11/17-11/23）: 新機能の追加** ⭐⭐⭐⭐

#### 2.1 感情スコアの追加

**目的**: コメントの興奮度を考慮

**実装**:
```python
# 簡易感情分析
POSITIVE_WORDS_JA = ["すごい", "最高", "神", "やばい", "うまい", "勝", "ゴール"]
POSITIVE_WORDS_EN = ["goal", "amazing", "great", "wow", "nice", "win", "epic"]
POSITIVE_WORDS_PT = ["gol", "incrível", "ótimo", "legal", "vitória"]

NEGATIVE_WORDS_JA = ["ダメ", "最悪", "負け", "ミス", "やばい", "つまらん"]
NEGATIVE_WORDS_EN = ["miss", "bad", "lose", "terrible", "boring", "awful"]
NEGATIVE_WORDS_PT = ["perda", "ruim", "péssimo", "chato"]

def compute_sentiment_score(comments, lang='mixed'):
    """
    簡易感情スコア（-1 to 1）
    """
    pos_count = 0
    neg_count = 0
    
    for comment in comments:
        comment_lower = comment.lower()
        
        # ポジティブ語のカウント
        for word in POSITIVE_WORDS_JA + POSITIVE_WORDS_EN + POSITIVE_WORDS_PT:
            if word in comment_lower:
                pos_count += 1
        
        # ネガティブ語のカウント
        for word in NEGATIVE_WORDS_JA + NEGATIVE_WORDS_EN + NEGATIVE_WORDS_PT:
            if word in comment_lower:
                neg_count += 1
    
    total = len(comments)
    if total == 0:
        return 0.0
    
    # 正規化
    score = (pos_count - neg_count) / total
    return np.clip(score, -1.0, 1.0)

def compute_sentiment_similarity(event_A, event_B):
    """
    感情スコアの類似度
    """
    score_A = compute_sentiment_score(event_A['comments'])
    score_B = compute_sentiment_score(event_B['comments'])
    
    # 差が小さいほど類似
    diff = abs(score_A - score_B)
    similarity = 1.0 - (diff / 2.0)  # 0-1の範囲
    
    return similarity
```

**統合**:
```python
# 類似度計算に追加
combined_score = (
    0.35 * embedding_similarity +
    0.15 * lexical_similarity +
    0.35 * topic_jaccard +
    0.10 * temporal_correlation +
    0.05 * sentiment_similarity  # ← 新規
)
```

**期待効果**:
- 興奮度が似たイベントをより正確に検出
- 平均類似度: +0.02-0.03

---

#### 2.2 配信者数の活用

**現状**: 配信者数を考慮していない

**改善案**:
```python
def compute_broadcaster_coverage(event_A, event_B, total_broadcasters=4):
    """
    両イベントで何人の配信者が反応したか
    """
    broadcasters_A = set(event_A['broadcasters'])
    broadcasters_B = set(event_B['broadcasters'])
    
    # 和集合（少なくとも片方で反応）
    union = broadcasters_A | broadcasters_B
    coverage = len(union) / total_broadcasters
    
    return coverage

def compute_broadcaster_overlap(event_A, event_B):
    """
    共通配信者の割合
    """
    broadcasters_A = set(event_A['broadcasters'])
    broadcasters_B = set(event_B['broadcasters'])
    
    intersection = broadcasters_A & broadcasters_B
    union = broadcasters_A | broadcasters_B
    
    if len(union) == 0:
        return 0.0
    
    jaccard = len(intersection) / len(union)
    return jaccard
```

**活用方法**:
```python
# coverage が高いペア = 重要なイベント（論文で強調）
# overlap が高いペア = 同じイベントの可能性高い（重み増加）
```

---

### **Week 3（11/24-11/30）: 評価と可視化の強化** ⭐⭐⭐⭐

#### 3.1 改善前後の比較

**実装**:
```python
def compare_before_after():
    """
    改善前後の性能比較
    """
    # 改善前（現状）
    df_old = pd.read_csv('output/event_to_event_pairs.csv')
    
    # 改善後（新しい重み・パラメータで再実行）
    # ... 再実行 ...
    df_new = pd.read_csv('output/event_to_event_pairs_improved.csv')
    
    metrics = ['avg_similarity', 'topic_coverage', 'temporal_consistency']
    
    print("【改善前後の比較】")
    print(f"{'指標':<25} | 改善前 | 改善後 | 改善率")
    print("-" * 60)
    
    # 平均類似度
    old_avg = df_old['combined_score'].mean()
    new_avg = df_new['combined_score'].mean()
    improvement = (new_avg - old_avg) / old_avg * 100
    print(f"{'平均類似度':<25} | {old_avg:.3f} | {new_avg:.3f} | +{improvement:.1f}%")
    
    # トピック一致率
    old_coverage = len(df_old[df_old['topic_jaccard'] > 0]) / len(df_old)
    new_coverage = len(df_new[df_new['topic_jaccard'] > 0]) / len(df_new)
    improvement = (new_coverage - old_coverage) / old_coverage * 100
    print(f"{'トピック一致率':<25} | {old_coverage:.1%} | {new_coverage:.1%} | +{improvement:.1f}%")
    
    # 完全一致
    old_perfect = len(df_old[df_old['topic_jaccard'] == 1.0])
    new_perfect = len(df_new[df_new['topic_jaccard'] == 1.0])
    print(f"{'完全一致':<25} | {old_perfect} | {new_perfect} | +{new_perfect - old_perfect}")
```

---

#### 3.2 詳細なエラー分析

**実装**:
```python
def analyze_failure_cases():
    """
    低類似度ペアの詳細分析
    """
    df = pd.read_csv('output/event_to_event_pairs.csv')
    
    # 類似度<0.3のペア
    low_sim = df[df['combined_score'] < 0.3]
    
    print(f"【低類似度ペアの分析】")
    print(f"総数: {len(low_sim)}ペア")
    
    for idx, row in low_sim.iterrows():
        print(f"\nEvent {row['event_A_id']} ↔ {row['event_B_id']}")
        print(f"  総合: {row['combined_score']:.3f}")
        print(f"  embedding: {row['embedding_similarity']:.3f}")
        print(f"  topic: {row['topic_jaccard']:.3f}")
        print(f"  時間差: {row['time_diff_bins']} bins")
        
        # 失敗原因の推測
        reasons = []
        if row['embedding_similarity'] < 0.4:
            reasons.append("埋め込みが低い（異なる内容）")
        if row['topic_jaccard'] == 0:
            reasons.append("トピック不一致（N-gram抽出失敗？）")
        if row['time_diff_bins'] > 50:
            reasons.append("時間差が大きい")
        
        print(f"  推定原因: {', '.join(reasons)}")
```

---

## 📅 実行スケジュール（11月）

| 週 | タスク | 所要時間 | 成果物 |
|----|--------|---------|--------|
| **Week 1** | N-gram最適化 | 2-3時間 | max_features=3000版 |
| Week 1 | 重み最適化 | 2時間 | 最適重みの決定 |
| Week 1 | 時間類似度修正 | 1時間 | ロバスト版実装 |
| **Week 2** | 感情分析追加 | 2時間 | sentiment_score |
| Week 2 | 配信者数活用 | 1時間 | broadcaster_overlap |
| Week 2 | 再実行 | 30分 | 改善版結果 |
| **Week 3** | 改善前後比較 | 1時間 | 比較レポート |
| Week 3 | エラー分析 | 1時間 | 失敗ケース分析 |
| Week 3 | 追加可視化 | 2時間 | 改善図表 |

**合計**: 約15時間（週5時間 × 3週間）

---

## 🎯 11月末の目標値

| 指標 | 現状 | 目標 | 達成条件 |
|------|------|------|---------|
| 平均類似度 | 0.237 | **0.35** | Week 1完了 |
| トピック一致率 | 17.9% | **35%** | Week 1完了 |
| 完全一致 | 1件 | **2-3件** | Week 1-2完了 |
| 時間的一貫性 | 0.49x | **2.5x** | Week 1完了 |
| 高品質ペア | 1件 | **3-5件** | Week 2完了 |

---

## ✅ 今週（Week 1）の具体的タスク

### **Task 1: max_features拡張（30分）** ⭐⭐⭐⭐⭐

**実行内容**:
1. `event_comparison.py` line 687を編集
2. `max_features=2000` → `max_features=3000`
3. 再実行して結果を比較

### **Task 2: 重み最適化スクリプト作成（1時間）**

**実行内容**:
1. `optimize_weights.py` を作成
2. グリッドサーチ実行
3. 最適重みを決定

### **Task 3: 時間類似度のロバスト化（1時間）**

**実行内容**:
1. `compute_temporal_similarity_robust()` 実装
2. `event_comparison.py` に統合
3. 再実行

---

## 💡 重要ポイント

1. **段階的改善**: 一度にすべて変更せず、1つずつ効果を確認
2. **比較の徹底**: 改善前後を必ず比較して数値化
3. **失敗の分析**: 何がうまくいかないかを理解する
4. **12月に備える**: 論文執筆時に説得力のある結果を用意

---

**まずは今週のTask 1から始めましょう！max_features拡張を実行しますか？**
