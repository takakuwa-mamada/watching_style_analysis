# 精度向上と新機能の実装まとめ

## 実施日: 2025年11月7日

---

## 📊 実装した改善点

### 1. **topic_jaccardの同義語正規化適用**（精度向上）

#### 問題点
- 従来は単純な集合演算でトピック語を比較
- 同じ意味の異なる表記（"goal", "ゴール", "gol"）が別物として扱われる
- その結果、topic_jaccardの90%が0.0という低い一致率

#### 解決策
```python
# 従来の実装
topics_A = event_A["topics"]
topics_B = event_B["topics"]
intersection = len(topics_A & topics_B)  # 単純な文字列一致

# 改善後の実装
normalized_A = set()
for topic in topics_A:
    normalized = normalize_with_synonyms(topic)  # 同義語正規化
    normalized_A.add(normalized)

normalized_B = set()
for topic in topics_B:
    normalized = normalize_with_synonyms(topic)
    normalized_B.add(normalized)

intersection = len(normalized_A & normalized_B)  # 正規化後の比較
```

#### 期待される効果
- 多言語トピックの一致率が向上
- topic_jaccardが0.0のペアが減少（90% → 50-60%に改善見込み）
- 同義語辞書（25単語×平均4同義語）の活用により、より正確な類似度計算

---

### 2. **時間的相関分析の追加**（新機能）

#### 概要
コメント数の時系列パターンの相関を分析する新機能。同じイベントを視聴している場合、コメント数の増減パターンが類似することを利用。

#### 実装詳細

**Step 1: イベント表現に時系列データを追加**
```python
# aggregate_event_representation関数に追加
comment_counts_per_bin = []
for stream_key, evt in evts_dict.items():
    bin_id = int(evt.get("bin_id", -1))
    # イベント前後±peak_pad範囲のコメント数を取得
    for offset in range(-peak_pad, peak_pad + 1):
        target_bin = bin_id + offset
        if 0 <= target_bin < len(stream_data.comment_counts):
            counts.append(stream_data.comment_counts[target_bin])
```

**Step 2: Pearson相関係数の計算（scipy不要、numpy実装）**
```python
# compute_event_to_event_similarity関数に追加
counts_A = np.array(event_A["comment_counts_per_bin"])
counts_B = np.array(event_B["comment_counts_per_bin"])

# Pearson相関をnumpyで計算
mean_A = np.mean(counts_A)
mean_B = np.mean(counts_B)
std_A = np.std(counts_A)
std_B = np.std(counts_B)

if std_A > 0 and std_B > 0:
    correlation = np.mean((counts_A - mean_A) * (counts_B - mean_B)) / (std_A * std_B)
    if correlation > 0.3:  # 中程度以上の相関のみ採用
        temporal_correlation = correlation
```

**Step 3: Combined scoreへの反映**
```python
# 時間的相関が高い場合、combined_scoreにボーナス（最大+10%）
if temporal_correlation > 0.5:
    combined_score = min(1.0, combined_score * (1.0 + temporal_correlation * 0.1))
```

#### 期待される効果
- 同じイベントの検出精度が向上
- 異なるイベントでもembedding類似度が高い場合の誤検出を削減
- 時系列パターンという新しい視点からの検証

#### 活用例
- Event A: サッカーの試合、ゴール時にコメント急増
- Event B: 同じ試合の別配信、同じタイミングでコメント急増
- → temporal_correlation = 0.85（強い相関）→ 同一イベントと判定

---

### 3. **イベント信頼度スコアの計算**（新機能）

#### 概要
複数の指標から総合的にイベントペアの信頼度を評価する新機能。

#### 信頼度を構成する4つのFactor

**Factor 1: コメント数**
```python
total_comments = len(event_A["comments"]) + len(event_B["comments"])
comment_factor = min(1.0, total_comments / 200.0)
```
- コメント数が多いほど信頼性が高い
- 200コメント以上で最大スコア

**Factor 2: トピックの明確性**
```python
topic_count = len(event_A["topics"]) + len(event_B["topics"])
topic_factor = min(1.0, topic_count / 20.0)
```
- トピック数が適度にあるほど信頼性が高い
- 20トピック以上で最大スコア

**Factor 3: 複数指標の一致度**
```python
consistency_scores = [embedding_sim, topic_jaccard, lexical_sim]
consistency_factor = 1.0 - min(1.0, np.std(consistency_scores) / 0.5)
```
- embedding, topic, lexicalの3指標が全て似た値を示すほど一致度が高い
- 標準偏差が小さいほど信頼性が高い

**Factor 4: 時間的相関**
```python
if temporal_correlation > 0.3:
    confidence_factors.append(temporal_correlation)
```
- 時間的相関が0.3以上の場合、信頼度に加算

**最終的な信頼度スコア**
```python
confidence_score = np.mean(confidence_factors)  # 全Factorの平均
```

#### 期待される効果
- イベントペアの信頼度を0-1のスコアで定量化
- 信頼度が高いペアを優先的に分析可能
- 論文での議論において、結果の信頼性を示す根拠となる

#### 活用例
- confidence_score = 0.85: 非常に高信頼（複数指標が一致、コメント数多い）
- confidence_score = 0.45: 中程度（一部指標のみ一致、コメント数少ない）
- confidence_score = 0.20: 低信頼（指標が不一致、データ不足）

---

## 📈 CSV出力への追加カラム

### 新しく追加されたカラム

1. **temporal_correlation** (float)
   - 時間的相関係数（0.0-1.0）
   - 0.3以上: 中程度の相関
   - 0.5以上: 強い相関
   - 0.7以上: 非常に強い相関

2. **confidence_score** (float)
   - イベントペアの信頼度スコア（0.0-1.0）
   - 0.7以上: 高信頼
   - 0.4-0.7: 中信頼
   - 0.4未満: 低信頼

### 既存カラムの改善

- **topic_jaccard**: 同義語正規化により、より正確な値を反映

---

## 🎯 精度向上の評価指標

### 定量的な改善目標

| 指標 | 改善前 | 改善後（目標） | 測定方法 |
|------|--------|---------------|---------|
| topic_jaccard = 0.0のペア数 | 90% (19/21) | 50-60% (10-13/21) | CSVのtopic_jaccard列を集計 |
| 誤検出の削減 | - | 20-30%削減 | temporal_correlationとcontext_penaltyの組み合わせ |
| 信頼度の高いペア検出 | - | confidence_score > 0.7が30%以上 | CSVのconfidence_score列を集計 |

### 定性的な改善効果

1. **多言語対応の強化**
   - 日本語/英語/ポルトガル語のトピックが統一的に処理される
   - 国際比較研究における精度向上

2. **時間軸の活用**
   - embedding類似度だけでなく、時系列パターンでも検証
   - 偽陽性（False Positive）の削減

3. **結果の信頼性向上**
   - 各ペアに信頼度スコアが付与
   - 論文執筆時の議論の根拠が明確化

---

## 🔧 技術的な工夫

### 1. scipy依存の削除
- **問題**: scipyのインストールに時間がかかる
- **解決**: Pearson相関をnumpyで実装
```python
correlation = np.mean((counts_A - mean_A) * (counts_B - mean_B)) / (std_A * std_B)
```

### 2. 軽量な実装
- 既存のnumpy/pandas/matplotlibのみで実装
- 追加の外部ライブラリ不要

### 3. 計算効率
- 時系列データは必要な範囲のみ取得（±peak_pad）
- 相関計算は配列化して一括処理

---

## 📝 今後の展開

### 短期的な拡張（1-2時間）
1. **temporal_correlationの可視化**
   - 時系列パターンの比較グラフを生成
   - 相関の高いペアと低いペアの視覚的比較

2. **confidence_scoreによるフィルタリング**
   - 信頼度の高いペアのみを抽出した別のCSV出力
   - 論文用の厳選されたデータセット作成

### 中期的な拡張（半日-1日）
1. **2-gram/3-gramトピックの導入**
   - "高校サッカー", "ワールドカップ"など複合語の検出
   - topic_jaccardのさらなる精度向上

2. **動的閾値の最適化**
   - embedding_threshold, temporal_correlation閾値の自動調整
   - データセットごとの最適化

3. **機械学習ベースの統合**
   - 複数指標（embedding, topic, lexical, temporal）を特徴量とした分類器
   - より高精度な同一イベント判定

---

## 📊 実行結果の確認方法

### CSV出力の確認
```python
import pandas as pd

df = pd.read_csv('output/event_to_event_pairs.csv')

# topic_jaccardの改善確認
print("topic_jaccard > 0の割合:")
print((df['topic_jaccard'] > 0).mean())

# 時間的相関の確認
print("\ntemporal_correlation分布:")
print(df['temporal_correlation'].describe())

# 信頼度スコアの確認
print("\nconfidence_score分布:")
print(df['confidence_score'].describe())

# 高信頼ペアの抽出
high_confidence = df[df['confidence_score'] > 0.7]
print(f"\n高信頼ペア: {len(high_confidence)}件")
```

### 改善効果の可視化
```python
import matplotlib.pyplot as plt

# topic_jaccardの分布
plt.hist(df['topic_jaccard'], bins=20)
plt.title('Topic Jaccard Distribution (After Synonym Normalization)')
plt.xlabel('Topic Jaccard')
plt.ylabel('Frequency')
plt.savefig('topic_jaccard_improved.png')

# 時間的相関 vs 類似度
plt.scatter(df['temporal_correlation'], df['main_similarity'])
plt.title('Temporal Correlation vs Similarity')
plt.xlabel('Temporal Correlation')
plt.ylabel('Main Similarity')
plt.savefig('temporal_vs_similarity.png')
```

---

## 🎓 論文への活用

### 記載すべき改善点

1. **手法の節**
   - 同義語正規化を用いたトピック比較
   - 時間的相関分析による検証層の追加
   - 信頼度スコアによる結果の品質管理

2. **結果の節**
   - topic_jaccardの改善率（90%→50%）
   - temporal_correlationによる偽陽性削減率
   - confidence_scoreの分布と高信頼ペアの特徴

3. **考察の節**
   - 多言語対応の重要性
   - 時系列パターンという新しい視点の有効性
   - 複数指標の統合による信頼性向上

---

## ✅ チェックリスト

- [x] topic_jaccardに同義語正規化を適用
- [x] 時間的相関分析機能を実装
- [x] イベント信頼度スコアを実装
- [x] CSV出力に新カラムを追加
- [x] scipy依存を削除（numpy実装）
- [x] 結果表示部分を更新
- [ ] 実行結果の確認
- [ ] 改善効果の定量評価
- [ ] 可視化の作成（オプション）
- [ ] 論文への記載内容の整理

---

**次のステップ**: 実行結果を確認し、改善効果を定量的に評価する
