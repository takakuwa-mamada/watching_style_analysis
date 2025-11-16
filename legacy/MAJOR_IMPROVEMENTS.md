# 論文レベル精度改善の実装サマリー

## 実施日時: 2025年11月7日

---

## 🔥 実装した抜本的改善（レベル2→10を目指す）

### 1. **N-gramトピックモデリング** ⭐⭐⭐ 最重要

#### 変更内容
```python
# 従来: 単語レベルのみ
vectorizer_model = CountVectorizer(max_features=6000, min_df=1)
# → "Real", "Madrid", "Barcelona" を個別に抽出

# 改善後: 1-gram, 2-gram, 3-gram
vectorizer_model = CountVectorizer(
    max_features=8000,
    ngram_range=(1, 3),  # 【重要】フレーズ抽出を有効化
    max_df=0.95  # 一般的な単語（"the", "a"）を除外
)
# → "Real Madrid", "penalty kick", "World Cup final" を抽出
```

#### 期待効果
- **topic_jaccard > 0が19% → 50-70%に改善**
- フレーズレベルの意味理解により精度大幅向上
- "Real Madrid"のような重要な固有名詞を正しく認識

---

### 2. **TF-IDF重み付きJaccard係数** ⭐⭐ 重要

#### 変更内容
```python
# 従来: すべての単語が等価
intersection = len(topics_A & topics_B)
union = len(topics_A | topics_B)
jaccard = intersection / union

# 改善後: 重要度に応じた重み付け
for topic in all_topics:
    # 出現頻度が低い（重要な）単語に高い重みを付与
    weight = min(5.0, 1.0 / (frequency + 0.1))
    weighted_intersection += weight (if both have it)
    weighted_union += weight
weighted_jaccard = weighted_intersection / weighted_union
```

#### 期待効果
- **より意味的に正確な類似度計算**
- 一般的な単語（"the", "a", "in"）の影響を削減
- 重要な固有名詞（チーム名、選手名）を重視

---

### 3. **多言語同義語辞書の大幅拡張** ⭐⭐ 重要

#### 変更内容
```
従来: 22語 → 改善後: 45語以上（+100%増加）

【追加カテゴリ】
1. チーム名（サッカー）
   - Real Madrid, Barcelona, Liverpool, PSG等

2. チーム名（野球）
   - Yankees, Dodgers, Red Sox, Giants等

3. 詳細な用語
   - shoot/shot/シュート
   - goalkeeper/goalie/ゴールキーパー
   - freekick/フリーキック
   - hit/ヒット/安打

4. 試合フェーズ
   - halftime/ハーフタイム
   - overtime/延長
```

#### 期待効果
- **チーム名や選手名の多言語対応**
- より細かい用語の統一
- 表現の揺れへの対応力向上

---

### 4. **スポーツキーワード辞書の拡張** ⭐ 中要度

#### 変更内容
```
野球: 14語 → 33語 (+135%増加)
サッカー: 17語 → 38語 (+124%増加)

【追加された野球キーワード】
球、投球、打撃、走者、塁、イニング、回、表、裏、
ストライク、ボール、アウト、セーフ、ヒット、安打、
Yankees, Dodgers, MLB等

【追加されたサッカーキーワード】
シュート、ドリブル、パス、クロス、前半、後半、
ハーフタイム、延長、PK戦、
Real Madrid, Barcelona, Liverpool等
```

#### 期待効果
- **context_penalty適用率の向上**
- 異なるスポーツの誤マッチを削減
- より広範なスポーツ用語に対応

---

## 📊 期待される改善結果

### 定量的目標（現状 → 目標）

| 指標 | 現状（レベル2） | 目標（レベル10） | 改善率 |
|------|----------------|-----------------|--------|
| topic_jaccard > 0 | 4/21 (19%) | **13-15/21 (60-70%)** | +250% |
| 平均類似度 | 0.327 | **0.600+** | +84% |
| 低類似度ペア(<0.5) | 16/21 (76%) | **4-6/21 (20-30%)** | -60% |
| 高類似度ペア(>0.7) | 3/21 (14%) | **8-10/21 (40-50%)** | +200% |

### 定性的改善

1. **フレーズレベルの理解**
   - ❌ 従来: "Real", "Madrid" → 別々の単語
   - ✅ 改善: "Real Madrid" → 1つのフレーズとして認識

2. **重要度を考慮した比較**
   - ❌ 従来: "goal"と"the"が同じ重み
   - ✅ 改善: "goal"が5倍の重み、"the"は軽視

3. **チーム名の認識**
   - ❌ 従来: "Barcelona"だけ
   - ✅ 改善: "Barcelona", "Barça", "バルセロナ"を統一

---

## 🎯 各改善の独立した効果

| 改善 | 独立効果 | 累積効果 |
|------|---------|---------|
| N-gram | topic_jaccard +30-40% | 19% → 50-60% |
| TF-IDF重み付け | 類似度精度 +15-20% | 0.327 → 0.45 |
| 同義語拡張 | topic_jaccard +10-15% | 60% → 70% |
| キーワード拡張 | 誤検出 -20% | context適用率向上 |

**合計期待効果**: レベル2 → レベル8-9

---

## 💡 技術的な工夫

### 1. N-gramの効率的な実装
```python
# CountVectorizerの設定
ngram_range=(1, 3)  # 1-gram, 2-gram, 3-gram
max_df=0.95  # 95%以上に出現する一般語を除外
max_features=8000  # 特徴量を6000→8000に増加
```

### 2. 重み付けJaccardの数式
```
weight(w) = min(5.0, 1.0 / (min_frequency + 0.1))

weighted_jaccard = Σ weight(w) for w in intersection
                   / Σ weight(w) for w in union
```

### 3. メモリ効率
- N-gramによる特徴量増加にもかかわらず
- max_df=0.95により一般語を削減
- 実質的なメモリ増加は最小限

---

## 📈 実行結果の確認方法

実行完了後、以下で結果を確認：

```python
import pandas as pd

df = pd.read_csv('output/event_to_event_pairs.csv')

print("=== 改善効果の確認 ===")
print(f"topic_jaccard > 0: {(df['topic_jaccard'] > 0).sum()}/{len(df)}")
print(f"平均類似度: {df['main_similarity'].mean():.3f}")
print(f"低類似度ペア(<0.5): {(df['main_similarity'] < 0.5).sum()}/{len(df)}")
print(f"高類似度ペア(>0.7): {(df['main_similarity'] > 0.7).sum()}/{len(df)}")

# Before/After比較
print("\n=== Before/After ===")
print("topic_jaccard > 0: 4/21 (19%) → ??/21 (??%)")
print("平均類似度: 0.327 → ?.???")
```

---

## ✅ 実装完了チェックリスト

- [x] N-gramトピックモデリング（ngram_range=(1,3)）
- [x] TF-IDF重み付きJaccard係数
- [x] 多言語同義語辞書の拡張（22語→45語）
- [x] スポーツキーワード辞書の拡張（野球33語、サッカー38語）
- [ ] 実行完了と結果確認
- [ ] 改善効果の定量評価
- [ ] 論文レベル（10）達成の判定

---

**次のステップ**: 実行完了を待ち、結果を評価して追加改善の必要性を判断
