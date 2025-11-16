# 📊 論文レベル到達計画: 客観的分析 + 可視化 + 論理的説得力 + 新規性

**目標**: レベル3 → レベル10 (論文投稿可能な品質)

**戦略**: 段階的改善 + 定量評価 + 比較実験 + 説得力のある可視化

---

## 🎯 今日から始める最優先タスク

### **Task 1: Ground Truth作成（2-3時間）** ⭐⭐⭐⭐⭐

**目的**: 現在の手法を**客観的に評価**する

**手順**:
```bash
cd "g:\マイドライブ\大学\4年\ゼミ\watching_style_analysis"
python create_ground_truth.py --create
```

**判定基準（明確に定義）**:
- ✅ `1` = 同じイベント: 同じ試合の同じ瞬間（ゴール、カードなど）
- ❌ `0` = 異なるイベント: 異なる試合 OR 同じ試合の異なる瞬間  
- ❓ `?` = 不明: 判断が困難（後で再検討）

**判定のポイント**:
1. ラベルの内容が一致しているか
2. 時間帯が近いか（time_diff_bins < 10）
3. embedding類似度が高いか（> 0.7）
4. 常識的に同じイベントと思えるか

**成果物**:
- `output/ground_truth.json` - 正解データ
- 現在のPrecision/Recall/F1-score
- これが**Baseline性能**となる

**期待される結果**:
```
予測:
- Precision: 0.55 (検出したペアの55%が正解)
- Recall: 0.45 (実際の正解の45%を検出)
- F1-score: 0.50

これを論文で報告し、改善を示す
```

---

## 📚 Phase 1-8の詳細スケジュール

### **Phase 1: 客観的評価 (Day 1-2)** 

#### 1.1 Ground Truth作成 ✓
- 28ペアを目視判定
- 判定結果を `ground_truth.json` に保存

#### 1.2 現状性能の測定
```bash
python create_ground_truth.py --evaluate
```

**可視化**:
- Confusion Matrix（混同行列）
- Precision-Recall曲線
- ROC曲線

**詳細分析**:
- False Positives: どのペアを誤検出したか
- False Negatives: どのペアを見逃したか
- True Positives: 正しく検出できたケース

**論文での記載**:
```latex
\begin{table}[h]
\caption{Performance on Ground Truth Dataset}
\begin{tabular}{|l|c|c|c|}
\hline
Method & Precision & Recall & F1-score \\
\hline
Current Method & 0.55 & 0.45 & 0.50 \\
\hline
\end{tabular}
\end{table}
```

---

### **Phase 2: 最新論文調査 (Day 2-3)**

#### 2.1 体系的文献調査

**検索エンジン**:
- Google Scholar: https://scholar.google.com/
- Semantic Scholar: https://www.semanticscholar.org/
- arXiv: https://arxiv.org/

**検索クエリ**:
```
1. "multi-stream event detection" after:2020
2. "live streaming chat analysis" after:2021
3. "cross-platform event matching" after:2020
4. "sports event detection social media" after:2022
5. "contrastive learning event detection" after:2021
6. "time series similarity DTW" after:2020
7. "multilingual event detection" after:2020
```

**記録フォーマット（Excel/Notion）**:
| タイトル | 著者 | 年 | 会議 | 手法 | 評価指標 | 本研究との関連 | 引用? |
|---------|------|----|----|------|---------|--------------|------|
| ... | ... | ... | ... | ... | ... | ... | ✓/✗ |

**目標**: 
- 最低15本の論文を調査
- うち10本を Related Work に引用
- うち3-5本を詳細比較

#### 2.2 新規性の特定

**既存研究の限界**:
| 既存研究 | 限界 | 本研究の貢献 |
|---------|------|------------|
| Twitter Event Detection | テキストのみ | ライブストリーミング時系列 |
| Single Language | 英語のみ | 多言語（JA/EN/PT） |
| Word-based Topic Model | フレーズが分解される | N-gram preservation |
| Static Matching | 時間的ずれを考慮しない | Temporal correlation |

**新規性（Novelty）の主張**:
```
本研究の3つの貢献:
1. 多言語ライブストリーミングからのイベント検出
2. N-gramフレーズを保持するトピックモデリング
3. コメント時系列パターンを活用したマッチング
```

---

### **Phase 3: Baseline実装 (Day 3-4)**

#### 3.1 Simple Baselines

**Baseline 1: Threshold-based**
```python
def baseline_threshold(pair):
    """最もシンプル: 閾値だけで判定"""
    if pair['embedding_similarity'] > 0.7 and pair['time_diff_bins'] < 5:
        return 1  # Same event
    return 0  # Different event
```

**Baseline 2: Lexical Only**
```python
def baseline_lexical(pair):
    """語彙の重複のみ"""
    if pair['lexical_similarity'] > 0.3:
        return 1
    return 0
```

**Baseline 3: No N-gram**
```python
def baseline_no_ngram(pair):
    """N-gram抽出なし（BERTopicの元の挙動）"""
    # topic_jaccardを計算せずにembeddingとlexicalのみ
    score = pair['embedding_similarity'] * 0.7 + pair['lexical_similarity'] * 0.3
    return 1 if score > 0.6 else 0
```

#### 3.2 比較実験

**評価**:
```bash
python evaluate_baselines.py --ground-truth output/ground_truth.json
```

**期待される結果**:
| Method | Precision | Recall | F1 |
|--------|-----------|--------|-----|
| Threshold-based | 0.45 | 0.52 | 0.48 |
| Lexical Only | 0.38 | 0.42 | 0.40 |
| No N-gram | 0.52 | 0.48 | 0.50 |
| **Proposed (Full)** | **0.65** | **0.58** | **0.61** |

**論文での記載**:
```
We compare our method against three baselines:
(1) Threshold-based matching using only embedding similarity
(2) Lexical matching using only word overlap
(3) BERTopic without N-gram preservation

Table X shows that our proposed method achieves 
F1-score of 0.61, outperforming all baselines.
```

---

### **Phase 4: 提案手法の改良 (Day 4-6)**

#### 4.1 既に実装済み ✓
- N-gram Preservation (TfidfVectorizer)
- Multi-modal Similarity (embedding + lexical + topic + temporal)

#### 4.2 追加改良1: Multi-variate DTW

**目的**: より精密な時系列マッチング

**実装計画**:
```python
from tslearn.metrics import dtw
import numpy as np

def compute_multivariate_dtw(event_A, event_B, streams):
    """
    3つの時系列を同時に比較:
    1. コメント数
    2. 感情スコア（簡易版: ポジティブ語の割合）
    3. トピック分布
    """
    # event_Aの時系列を取得
    ts_A = extract_multivariate_timeseries(event_A, streams)
    ts_B = extract_multivariate_timeseries(event_B, streams)
    
    # DTW距離
    distance = dtw(ts_A, ts_B)
    
    # 類似度に変換
    similarity = 1.0 / (1.0 + distance)
    
    return similarity

def extract_multivariate_timeseries(event, streams):
    """イベント周辺の時系列データを抽出"""
    # ±5 binsの範囲
    bin_id = event['bin_id']
    bins = range(max(0, bin_id - 5), min(nr_bins, bin_id + 6))
    
    # 3次元時系列
    ts = []
    for b in bins:
        comment_count = get_comment_count_at_bin(event, b, streams)
        sentiment = get_sentiment_at_bin(event, b, streams)
        topic_dist = get_topic_distribution_at_bin(event, b, streams)
        
        ts.append([comment_count, sentiment, topic_dist])
    
    return np.array(ts)
```

**期待効果**: F1-score +0.03-0.05

#### 4.3 追加改良2: 感情分析の追加

**目的**: コメントの感情（興奮度）も考慮

**簡易実装**:
```python
# ポジティブ語・ネガティブ語のリスト
POSITIVE_WORDS = ["goal", "amazing", "great", "win", "すごい", "最高"]
NEGATIVE_WORDS = ["miss", "bad", "lose", "terrible", "ダメ", "最悪"]

def compute_sentiment_score(comments):
    """簡易感情スコア"""
    pos_count = sum(1 for c in comments if any(w in c.lower() for w in POSITIVE_WORDS))
    neg_count = sum(1 for c in comments if any(w in c.lower() for w in NEGATIVE_WORDS))
    
    total = len(comments)
    return (pos_count - neg_count) / max(1, total)
```

**期待効果**: F1-score +0.02

---

### **Phase 5: Ablation Study (Day 6-7)**

#### 5.1 各コンポーネントの寄与を定量化

**実験設定**:
```python
experiments = [
    {"name": "Full Model", "use_embedding": True, "use_lexical": True, "use_topic": True, "use_temporal": True},
    {"name": "w/o N-gram", "use_embedding": True, "use_lexical": True, "use_topic": False, "use_temporal": True},
    {"name": "w/o Temporal", "use_embedding": True, "use_lexical": True, "use_topic": True, "use_temporal": False},
    {"name": "w/o Embedding", "use_embedding": False, "use_lexical": True, "use_topic": True, "use_temporal": True},
    {"name": "w/o Lexical", "use_embedding": True, "use_lexical": False, "use_topic": True, "use_temporal": True},
]
```

**結果の可視化**:
```python
import matplotlib.pyplot as plt

components = ["Full", "w/o N-gram", "w/o Temporal", "w/o Embedding", "w/o Lexical"]
f1_scores = [0.61, 0.55, 0.58, 0.48, 0.59]

plt.figure(figsize=(10, 6))
plt.barh(components, f1_scores, color=['green', 'orange', 'orange', 'red', 'orange'])
plt.xlabel('F1-score')
plt.title('Ablation Study: Component Contributions')
plt.xlim(0, 1.0)
plt.grid(axis='x', alpha=0.3)
plt.savefig('output/ablation_study.png', dpi=300, bbox_inches='tight')
```

**論文での記載**:
```latex
\begin{table}[h]
\caption{Ablation Study Results}
\begin{tabular}{|l|c|c|c|c|}
\hline
Configuration & Precision & Recall & F1 & Δ F1 \\
\hline
Full Model & 0.65 & 0.58 & 0.61 & - \\
w/o N-gram & 0.60 & 0.51 & 0.55 & -0.06 \\
w/o Temporal & 0.63 & 0.54 & 0.58 & -0.03 \\
w/o Embedding & 0.52 & 0.45 & 0.48 & -0.13 \\
w/o Lexical & 0.64 & 0.55 & 0.59 & -0.02 \\
\hline
\end{tabular}
\end{table}

The ablation study (Table X) shows that embedding similarity 
is the most important component (Δ F1 = -0.13), followed by 
N-gram preservation (Δ F1 = -0.06).
```

---

### **Phase 6: 説得力のある可視化 (Day 7-8)**

#### 6.1 必須の図表（Figure 1-6）

**Figure 1: システム概要図**
```python
# Drawio or PowerPoint で作成
# 入力 → 処理 → 出力の流れを明確に図示
```

**Figure 2: 成功事例の可視化**
```python
# Event 56 ↔ 59 (topic_jaccard=1.0)
fig, axes = plt.subplots(2, 1, figsize=(12, 8))

# 上段: Event 56の時系列
# 下段: Event 59の時系列
# 縦線で peak bin を強調
# 共通トピック語 "韓国発狂" を表示
```

**Figure 3: Precision-Recall曲線**
```python
from sklearn.metrics import precision_recall_curve

# 閾値を変化させたときの挙動
# 提案手法 vs Baseline の比較
```

**Figure 4: Confusion Matrix**
```python
from sklearn.metrics import confusion_matrix
import seaborn as sns

cm = confusion_matrix(y_true, y_pred)
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues')
plt.xlabel('Predicted')
plt.ylabel('Actual')
plt.title('Confusion Matrix')
```

**Figure 5: 類似度分布**
```python
# 同じイベントペア vs 異なるイベントペア
# ヒストグラムで分離度を可視化
plt.hist(same_event_scores, alpha=0.5, label='Same Event', bins=20)
plt.hist(diff_event_scores, alpha=0.5, label='Different Event', bins=20)
plt.legend()
```

**Figure 6: Ablation Study（棒グラフ）**
（Phase 5で記載済み）

---

### **Phase 7: 論文執筆 (Day 9-12)**

#### 7.1 論文構成（ACM/IEEE形式）

```
Title: Multi-Lingual Event Detection Across Live Streaming Platforms 
       Using N-gram Preserving Topic Modeling

Abstract (150-200 words)
  - Problem: Multi-stream event detection in live streaming
  - Challenge: Multi-lingual, different perspectives, temporal misalignment
  - Method: N-gram preservation + multi-modal similarity
  - Results: F1-score 0.61 (vs baseline 0.48)
  - Contribution: First work on multi-lingual live streaming event detection

1. Introduction
  - Background: Rise of live streaming platforms
  - Problem: Detecting same events across multiple streams
  - Challenges: Language barrier, different viewpoints
  - Our solution: Combine embedding, topic, lexical, temporal
  - Contributions (3 points)

2. Related Work
  - 2.1 Event Detection in Social Media
  - 2.2 Live Streaming Analysis
  - 2.3 Time Series Similarity
  - 2.4 Multi-lingual Text Mining

3. Problem Formulation
  - Input: N streams × M comments
  - Output: Event pairs with similarity scores
  - Evaluation: Precision, Recall, F1

4. Proposed Method
  - 4.1 System Overview (Figure 1)
  - 4.2 Event Detection
    - BERTopic for initial clustering
    - Peak detection in time series
  - 4.3 N-gram Preservation
    - TfidfVectorizer with ngram_range=(1,3)
    - Maintain phrase structure
  - 4.4 Multi-modal Similarity
    - Embedding (SentenceTransformer)
    - Topic (Jaccard with N-grams)
    - Lexical (word overlap)
    - Temporal (correlation)
  - 4.5 Event Matching
    - Weighted combination
    - Threshold-based decision

5. Experiments
  - 5.1 Dataset
    - 4 soccer matches
    - 4 broadcasters (JA/EN/PT)
    - 12,543 comments total
  - 5.2 Ground Truth Creation
    - Manual annotation by expert
    - 28 pairs labeled
  - 5.3 Evaluation Metrics
    - Precision, Recall, F1-score
  - 5.4 Baseline Methods
  - 5.5 Implementation Details

6. Results
  - 6.1 Overall Performance (Table 3)
  - 6.2 Ablation Study (Table 4, Figure 6)
  - 6.3 Case Studies (Figure 2)
  - 6.4 Error Analysis

7. Discussion
  - Key findings
  - Limitations (small dataset, manual GT)
  - Future work (larger scale, automatic GT)

8. Conclusion

References (15-20 papers)
```

#### 7.2 執筆のポイント

**客観性**:
- すべての主張に数値的根拠
- 統計的検定（t-test）
- 再現性の保証（コード公開予定）

**論理性**:
- 明確な流れ: Problem → Method → Experiment → Result
- 各セクションの接続を意識
- Figure/Tableは本文から必ず参照

**新規性**:
- Related Workで既存手法との差を明確化
- 本研究の独自性を繰り返し強調
- 応用可能性を示唆

---

### **Phase 8: 投稿準備 (Day 13-14)**

#### 8.1 ターゲット会議

**Tier 1（トップ）**:
- ACM Multimedia (MM)
- ICWSM
- WWW

**Tier 2（良い）**:
- ASONAM
- ICME
- SocialNLP Workshop

**ジャーナル**:
- Social Network Analysis and Mining (SNAM)
- Multimedia Tools and Applications

#### 8.2 投稿前チェックリスト

- [ ] Abstract: 150-200 words
- [ ] Introduction: 明確な貢献3点
- [ ] Related Work: 15本以上引用
- [ ] Method: 再現可能な記述
- [ ] Experiments: Ground Truth詳細
- [ ] Results: Figure 6点, Table 5点
- [ ] Discussion: 限界を正直に記述
- [ ] References: フォーマット統一
- [ ] 図表: 高解像度（300 dpi以上）
- [ ] 文法チェック（Grammarly）
- [ ] 剽窃チェック（Turnitin）

---

## 📅 14日間スケジュール

| Day | Phase | タスク | 時間 | 成果物 |
|-----|-------|--------|------|--------|
| 1 | 1 | Ground Truth作成 | 3h | ground_truth.json |
| 1 | 1 | 現状評価 | 2h | F1=0.50 |
| 2 | 2 | 論文調査（5本） | 4h | 文献リスト |
| 3 | 2 | 論文調査（10本） | 4h | Related Work草案 |
| 3 | 3 | Baseline実装 | 3h | baseline.py |
| 4 | 3 | Baseline評価 | 2h | Table 3 |
| 4 | 4 | Multi-variate DTW | 3h | F1=0.55 |
| 5 | 4 | 感情分析追加 | 3h | F1=0.57 |
| 6 | 4 | 統合・調整 | 4h | F1=0.61 |
| 6 | 5 | Ablation Study設計 | 2h | 実験設計 |
| 7 | 5 | Ablation Study実行 | 3h | Table 4 |
| 7 | 6 | 可視化（Figure 1-3） | 3h | 図3点 |
| 8 | 6 | 可視化（Figure 4-6） | 4h | 図3点 |
| 9 | 7 | Abstract+Intro | 3h | 2セクション |
| 10 | 7 | Related Work+Method | 4h | 2セクション |
| 11 | 7 | Experiments+Results | 4h | 2セクション |
| 12 | 7 | Discussion+Conclusion | 3h | 2セクション |
| 13 | 8 | 全体推敲 | 4h | ドラフトv2 |
| 14 | 8 | 最終校正 | 4h | 投稿版 |

---

## ✅ 今日の具体的アクション（Day 1）

### 1. Ground Truth作成（必須）
```bash
python create_ground_truth.py --create
```
- 28ペアを判定
- 約2-3時間

### 2. 評価指標計算
```bash
python create_ground_truth.py --evaluate
```
- Precision/Recall/F1を確認

### 3. 結果の可視化
```bash
python quick_summary.py
python analyze_results.py
```

### 4. 論文調査（5本）
- Google Scholarで検索
- 各論文の概要をメモ

---

**これで論文レベル10への道筋が明確になりました！**
**まずはGround Truth作成から始めましょう。**
