# 精度向上と新機能の実装サマリー

## 実装日時
2025年11月7日

## 概要
event_comparison.pyに対して、現在のコードの精度を最大化するための改善と、新しい分析機能を追加しました。

---

## 1. 精度向上の実装

### 1.1 topic_jaccardの同義語正規化適用 ✅

**問題点:**
- 従来のtopic_jaccardは単純な集合演算（set intersection/union）を使用
- "goal", "ゴール", "gol" など同義語が別の単語として扱われていた
- その結果、90%のペアでtopic_jaccard=0.0となっていた

**解決策:**
```python
# 同義語正規化を適用してトピックを統一
normalized_A = set()
for topic in topics_A:
    normalized = normalize_with_synonyms(topic)
    normalized_A.add(normalized)

normalized_B = set()
for topic in topics_B:
    normalized = normalize_with_synonyms(topic)
    normalized_B.add(normalized)

intersection = len(normalized_A & normalized_B)
union = len(normalized_A | normalized_B)
topic_jaccard = intersection / union if union > 0 else 0.0
```

**期待効果:**
- 多言語トピックの適切な一致検出
- topic_jaccard > 0.0 のペア数が 10% → 40-50% に増加
- トピック重複検出の精度向上

---

## 2. 新機能の実装

### 2.1 時間的相関分析（Temporal Correlation Analysis）✅

**機能説明:**
- 2つのイベント間で、コメント数の時系列パターンがどれだけ似ているかを分析
- Pearson相関係数を使用して、統計的に有意な相関を検出
- 同じ実世界イベントは、視聴者の反応パターン（コメント数の増減）が類似する

**実装内容:**

#### データ収集
```python
# イベント前後±peak_pad範囲のコメント数を配列として取得
comment_counts_per_bin = []
for stream_key, evt in evts_dict.items():
    bin_id = int(evt.get("bin_id", -1))
    if bin_id >= 0 and stream_key in streams:
        stream_data = streams[stream_key]
        counts = []
        for offset in range(-peak_pad, peak_pad + 1):
            target_bin = bin_id + offset
            if 0 <= target_bin < len(stream_data.comment_counts):
                counts.append(stream_data.comment_counts[target_bin])
            else:
                counts.append(0)
        if counts:
            comment_counts_per_bin.extend(counts)
```

#### 相関計算
```python
from scipy.stats import pearsonr
temporal_correlation = 0.0

if len(counts_A) > 1 and len(counts_B) > 1:
    correlation, p_value = pearsonr(counts_A, counts_B)
    # 有意な相関のみ採用（p < 0.05）
    if not np.isnan(correlation) and p_value < 0.05:
        temporal_correlation = max(0.0, correlation)
```

#### 総合スコアへの統合
```python
# 時間的相関が高い場合、combined_scoreにボーナス（最大+10%）
if temporal_correlation > 0.5:
    combined_score = min(1.0, combined_score * (1.0 + temporal_correlation * 0.1))
```

**出力:**
- `temporal_correlation`: 0.0〜1.0（0.3以上が有意）
- CSV列として保存: event_to_event_pairs.csv

**活用方法:**
- 高い時間的相関（r > 0.6）→ 同一イベントの可能性が高い
- 低い相関（r < 0.3）→ 別イベントの可能性が高い
- embedding/topicと合わせて総合判定

---

### 2.2 イベント信頼度スコア（Confidence Score）✅

**機能説明:**
- イベント類似度の信頼性を評価する複合指標
- 複数の要因から総合的に信頼度を算出
- 低信頼度の誤検出を識別できる

**信頼度の構成要素:**

#### Factor 1: コメント数（多いほど信頼性高い）
```python
total_comments_A = len(event_A.get("comments", []))
total_comments_B = len(event_B.get("comments", []))
comment_factor = min(1.0, (total_comments_A + total_comments_B) / 200.0)
```
- 理由: コメント数が少ないと、偶然の一致が多くなる
- 200コメント以上で最大値1.0

#### Factor 2: トピックの明確性（適度なトピック数）
```python
topic_count_A = len(event_A.get("topics", set()))
topic_count_B = len(event_B.get("topics", set()))
topic_factor = min(1.0, (topic_count_A + topic_count_B) / 20.0)
```
- 理由: トピックが明確に抽出されているほど、意味のあるイベント
- 20トピック以上で最大値1.0

#### Factor 3: 複数指標の一致度（consistency）
```python
consistency_scores = []
if embedding_sim is not None:
    consistency_scores.append(embedding_sim)
if topic_jaccard > 0:
    consistency_scores.append(topic_jaccard)
if lexical_sim > 0:
    consistency_scores.append(lexical_sim)

# 各スコアの標準偏差が小さいほど一致度が高い
consistency_factor = 1.0 - min(1.0, np.std(consistency_scores) / 0.5)
```
- 理由: embedding, topic, lexicalが全て高い → 確実な一致
- バラバラな値 → 偶然の一致の可能性

#### Factor 4: 時間的相関
```python
if temporal_correlation > 0.3:
    confidence_factors.append(temporal_correlation)
```
- 理由: 時間パターンも一致 → さらに信頼性アップ

#### 最終スコア
```python
confidence_score = np.mean(confidence_factors)
```
- 範囲: 0.0〜1.0
- 解釈:
  - 0.7以上: 高信頼度（確実な一致）
  - 0.5〜0.7: 中信頼度（一定の信頼性）
  - 0.5未満: 低信頼度（要注意）

**出力:**
- `confidence_score`: 0.0〜1.0
- CSV列として保存: event_to_event_pairs.csv

**活用方法:**
- 類似度が高くても信頼度が低い → 誤検出の可能性
- 類似度が中程度で信頼度が高い → 実際は一致の可能性
- 論文で結果の信頼性を議論する根拠となる

---

### 2.3 視覚化機能（Visualization）✅

**新しい分析図:**
`temporal_correlation_and_confidence_analysis.png`

#### 構成（2x2サブプロット）:

1. **時間的相関 vs メイン類似度の散布図**
   - X軸: temporal_correlation
   - Y軸: main_similarity
   - 色: confidence_score（viridisカラーマップ）
   - 用途: 3つの指標の関係を一目で把握

2. **信頼度スコアの分布ヒストグラム**
   - 全ペアの信頼度分布
   - 平均値を赤線で表示
   - 用途: 全体の信頼性レベルを評価

3. **有意な時間的相関の分布**
   - r > 0.3 のペアのみを抽出
   - 何ペア/全ペアを表示
   - 用途: 時間パターンが一致するペアの頻度

4. **指標間の相関マトリックス（ヒートマップ）**
   - main_similarity, topic_jaccard, lexical_similarity, temporal_correlation, confidence_scoreの相関
   - 用途: 各指標の独立性/相関関係を確認

**統計サマリー表示:**
```
=== 新機能の統計サマリー ===
時間的相関 (Temporal Correlation):
  - 平均: X.XXX
  - 中央値: X.XXX
  - 有意な相関 (r>0.3): XX/21 ペア (XX.X%)

信頼度スコア (Confidence Score):
  - 平均: X.XXX
  - 中央値: X.XXX
  - 高信頼度 (>0.7): XX/21 ペア
  - 中信頼度 (0.5-0.7): XX/21 ペア
  - 低信頼度 (<0.5): XX/21 ペア
```

---

## 3. 出力データの拡張

### 3.1 CSV出力の新カラム

**event_to_event_pairs.csv に追加:**
- `temporal_correlation`: 時間的相関係数（0.0〜1.0）
- `confidence_score`: 信頼度スコア（0.0〜1.0）

**従来のカラム:**
- event_A_id, event_B_id
- event_A_label, event_B_label
- main_similarity（メイン類似度）
- embedding_similarity
- topic_jaccard（←同義語正規化適用で精度向上）
- lexical_similarity
- combined_score
- time_diff_bins
- context_penalty

### 3.2 コンソール出力の拡張

**Top 10表示に新機能の情報を追加:**
```
Event XX <-> Event YY: similarity=0.XXX
  A: [イベントAのラベル]
  B: [イベントBのラベル]
  Metrics: emb=X.XXX, topic=X.XXX, lex=X.XXX, context=X.XXX
  新機能: temporal_corr=X.XXX, confidence=X.XXX  ← 追加
```

---

## 4. 依存関係の追加

**新規追加:**
- `scipy` パッケージ（Pearson相関計算用）
- `seaborn` パッケージ（相関マトリックスヒートマップ用）

**インストールコマンド:**
```bash
pip install scipy seaborn
```

---

## 5. 期待される効果

### 5.1 精度向上（topic_jaccard改善）
- **Before**: topic_jaccard = 0.0 が 90%（19/21ペア）
- **After（推定）**: topic_jaccard > 0.0 が 40-50%（8-10/21ペア）
- **効果**: トピック重複検出の精度が大幅に向上

### 5.2 誤検出の削減（confidence_score）
- **Before**: 高類似度でも誤検出の可能性を判断できない
- **After**: 低信頼度スコアで誤検出候補を識別
- **効果**: 結果の信頼性を定量的に評価可能

### 5.3 検出力の向上（temporal_correlation）
- **Before**: embedding/topicのみで判定
- **After**: 時間パターンの一致も考慮
- **効果**: embedding類似度が中程度でも、時間相関が高ければ同一イベントと判定可能

### 5.4 論文への貢献
1. **新規性**: 時間的相関と信頼度スコアは独自の貢献
2. **説得力**: 複数指標による総合評価で結果の妥当性を示せる
3. **透明性**: 各ペアの信頼度を明示することで、議論の余地を提供
4. **視覚化**: 4つの分析図で包括的な評価を提示

---

## 6. 今後の拡張可能性

### 6.1 短期的な改善（5-10分）
- 閾値調整: temporal_correlationの閾値を最適化
- 重み調整: confidence_scoreの各Factorの重みを調整

### 6.2 中期的な改善（20-30分）
- 2-gram実装: 複合語（"penalty kick", "フリーキック"）の検出
- Player/Team名の抽出: 固有名詞の一致度を別指標として追加

### 6.3 長期的な改善（1-2時間）
- 機械学習モデル: 複数指標からの統合判定を学習
- クラスタリング: 類似イベントのグループ化と可視化

---

## 7. 実行方法

### 7.1 パッケージインストール
```bash
pip install scipy seaborn
```

### 7.2 実行
```bash
python event_comparison.py
```

### 7.3 出力確認
- **CSV**: `output/event_to_event_pairs.csv`
  - temporal_correlation列とconfidence_score列を確認
- **画像**: `output/temporal_correlation_and_confidence_analysis.png`
  - 4つのサブプロットで総合分析
- **コンソール**: 統計サマリーとTop 10ペアの詳細

---

## 8. コード変更サマリー

### 変更ファイル
- `event_comparison.py`

### 主な変更箇所
1. **Lines 1419-1436**: topic_jaccardに同義語正規化適用
2. **Lines 1327-1348**: aggregate_event_representationに時系列データ追加
3. **Lines 1447-1527**: compute_event_to_event_similarityに新機能追加
   - 時間的相関計算
   - 信頼度スコア計算
4. **Lines 1636-1638**: CSV出力に新カラム追加
5. **Lines 3161-3167**: 視覚化関数の呼び出し追加
6. **Lines 3176-3178**: Top10表示に新機能情報追加
7. **Lines 3485-3563**: visualize_temporal_correlation_and_confidence関数追加

### 総行数変更
- **Before**: ~3473行
- **After**: ~3573行（+100行）

---

## 9. 検証項目

### 9.1 実行前チェック
- [ ] scipy, seabornがインストール済み
- [ ] event_comparison.pyに構文エラーがないことを確認

### 9.2 実行後チェック
- [ ] event_to_event_pairs.csvにtemporal_correlation列が追加されている
- [ ] event_to_event_pairs.csvにconfidence_score列が追加されている
- [ ] temporal_correlation_and_confidence_analysis.pngが生成されている
- [ ] topic_jaccardが0.0でないペアが増えている（従来19/21 → 改善後8-12/21を期待）
- [ ] コンソールに統計サマリーが表示されている
- [ ] Top 10表示に新機能の値が含まれている

---

## 10. 想定される結果の解釈例

### Example 1: 高信頼度の一致
```
Event 55 <-> Event 77: similarity=0.193
  Metrics: emb=0.678, topic=0.125, lex=0.193, context=0.3
  新機能: temporal_corr=0.782, confidence=0.845
```
**解釈**: 
- 類似度は低めだが、時間的相関が極めて高い（0.782）
- 信頼度スコアも高い（0.845）
- → 同一イベントの可能性が高い（context=0.3は別スポーツの補正）

### Example 2: 低信頼度の疑わしい一致
```
Event 33 <-> Event 54: similarity=0.721
  Metrics: emb=0.721, topic=0.000, lex=0.344, context=1.0
  新機能: temporal_corr=0.124, confidence=0.312
```
**解釈**:
- embedding類似度は高い（0.721）
- しかしtopic_jaccard=0（トピックが一致しない）
- 時間的相関も低い（0.124）
- 信頼度スコアが低い（0.312）
- → 誤検出の可能性が高い

---

## まとめ

今回の実装により、以下を達成しました：

1. **精度向上**: topic_jaccardに同義語正規化を適用し、トピック重複検出を改善
2. **新機能1**: 時間的相関分析により、コメントパターンの類似性を定量化
3. **新機能2**: 信頼度スコアにより、結果の信頼性を評価
4. **視覚化**: 4つのサブプロットで包括的な分析を提供
5. **拡張性**: 今後の改善の基盤となる構造を構築

これらの改善は、論文の質を向上させ、結果の妥当性を強化するものです。
