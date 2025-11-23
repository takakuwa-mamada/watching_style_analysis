# 📊 Event Comparison 精度向上計画 (Paper Quality: 6/10 → 8-9/10)

**作成日**: 2025年11月17日  
**目標**: 2週間以内に学会論文レベルの分析精度を達成  
**現状**: Paper Quality Assessment = 6/10 (ACCEPTABLE, but needs improvement)  
**目標**: Paper Quality Assessment = 8-9/10 (PUBLICATION READY)

---

## 🎯 Executive Summary

### 現在の問題点分析

#### 1. **統計的問題**
```
Topic Matching Analysis:
  - topic_jaccard = 0: 8/10 (80.0%) ← 問題!
  - topic_jaccard > 0: 2/10 (20.0%)
  - Average topic_jaccard: 0.101 ← 低すぎる!

Similarity Distribution:
  - Low (<0.5): 7/10 (70.0%) ← 多すぎる!
  - High (>=0.7): 1/10 (10.0%) ← 少なすぎる!
```

#### 2. **方法論的問題**
- ❌ **N-gram extraction**: TF-IDF依存で文脈無視
- ❌ **BERTopic**: 小規模イベント(6-84コメント)に過剰適合
- ❌ **Embedding threshold**: 0.7は高すぎる可能性
- ❌ **Time binning**: 100 bins → データ分散、イベント検出低下

#### 3. **データ品質問題**
- ⚠️ "kkkkkk", "www", "laugh laugh" などノイズトピックが支配的
- ⚠️ 実質的な試合イベント(ゴール、ファウル等)の検出不足
- ⚠️ ストリーム間の時刻同期精度未検証

---

## 📋 Phase 1: 即効性のある改善 (Week 1: Nov 17-24)

### 1.1 パラメータ最適化 (Priority: 🔴 CRITICAL)

**目標**: Topic matching率を20% → 60%以上に向上

#### A. Time Binning の最適化
```python
# 現状
--time-bins 100  # → イベントが細分化されすぎ

# 改善案 (Grid Search実施)
time_bins_candidates = [20, 30, 50, 75, 100]
optimal_bins = find_optimal_bins(
    metric='f1_score',  # Precision vs Recall のバランス
    ground_truth='manual_annotation.csv'  # 手動アノテーション必要
)
```

**実装タスク**:
- [ ] `scripts/optimize_time_bins.py` 作成
- [ ] 手動アノテーション: 3試合×10イベント = 30 ground truth events
- [ ] Grid Search実行 (5分×5パラメータ = 25分)
- [ ] 最適パラメータをREADMEに記載

**期待効果**: Topic matching +20-30%

---

#### B. Embedding Threshold の調整
```python
# 現状
--embedding-match-th 0.7  # 厳しすぎる?

# 改善案 (ROC Curve分析)
thresholds = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75]
optimal_th = find_optimal_threshold(
    metric='f1_score',
    ground_truth='manual_annotation.csv'
)
```

**実装タスク**:
- [ ] `scripts/optimize_embedding_threshold.py` 作成
- [ ] ROC Curve, Precision-Recall Curve生成
- [ ] 最適閾値の理論的正当化 (論文で説明)

**期待効果**: False Negative削減、Recall +10-15%

---

#### C. Topic Jaccard Threshold の緩和
```python
# 現状
--jaccard-th 0.6  # BERTopicトピックの類似度

# 改善案 (段階的緩和)
jaccard_th_candidates = [0.3, 0.4, 0.5, 0.6]
# 注: トピックが異なっても、embedding類似度が高ければマッチ許可
```

**実装タスク**:
- [ ] Jaccard閾値の影響分析
- [ ] Embedding優先の重み付け検証

**期待効果**: Topic matching +15-20%

---

### 1.2 ノイズフィルタリング強化 (Priority: 🟠 HIGH)

**目標**: 意味のないトピック("kkk", "www")を排除

#### A. ストップワード拡張
```python
# 追加すべきストップワード
NOISE_PATTERNS = [
    r'^k{3,}$',           # kkkkkk
    r'^w{3,}$',           # wwwwww
    r'^laugh( laugh)*$',  # laugh laugh laugh
    r'^lol( lol)*$',      # lol lol lol
    r'^clap( clap)*$',    # clap clap clap
    r'^[0-9]+$',          # 数字のみ
    r'^[!]+$',            # 感嘆符のみ
    r'^emoji_\w+$',       # Emoji単体
]
```

**実装タスク**:
- [ ] `utils/noise_filter.py` 作成
- [ ] event_comparison.py に統合
- [ ] フィルタリング前後の比較レポート生成

**期待効果**: Topic quality +30-40%, Event coherence向上

---

#### B. 最小コメント数閾値
```python
# 現状: 1コメントでもイベント化
MIN_COMMENTS_PER_EVENT = 5  # 統計的に有意なサンプルサイズ

# 理論的根拠
# - コメント数が少ないとトピックが不安定
# - ノイズ(ボット、スパム)の影響を受けやすい
```

**実装タスク**:
- [ ] イベント検出後にフィルタリング追加
- [ ] 最小コメント数の影響分析

**期待効果**: False Positive削減 -20-30%

---

### 1.3 評価指標の追加 (Priority: 🟡 MEDIUM)

**目標**: Paper Quality Assessmentの客観性向上

#### A. Ground Truth アノテーション
```csv
# manual_annotation.csv (例)
stream,timestamp,event_type,description,importance
Ja_abema,3413,goal,Japan scores first goal,HIGH
Bra,11037,celebration,Brazil fans celebrate,MEDIUM
UK,5447,controversy,Referee decision disputed,HIGH
```

**実装タスク**:
- [ ] 手動アノテーション (3試合×10イベント = 30件)
- [ ] アノテーター間信頼性 (Cohen's Kappa ≥ 0.7)
- [ ] `scripts/validate_ground_truth.py` 作成

**所要時間**: 2-3時間

---

#### B. 定量的評価指標
```python
# 追加すべき指標
metrics = {
    'precision': TP / (TP + FP),
    'recall': TP / (TP + FN),
    'f1_score': 2 * (precision * recall) / (precision + recall),
    'mean_average_precision': MAP,  # Ranking quality
    'normalized_mutual_information': NMI,  # Clustering quality
    'silhouette_score': silhouette,  # Event separation
}
```

**実装タスク**:
- [ ] `scripts/evaluate_event_detection.py` 作成
- [ ] Confusion Matrix生成
- [ ] 評価レポート自動生成

**期待効果**: 論文の信頼性 +大幅向上

---

## 📋 Phase 2: 根本的な方法論改善 (Week 2: Nov 25-Dec 1)

### 2.1 Hybrid Topic Modeling (Priority: 🔴 CRITICAL)

**問題**: BERTopicが小規模データ(6-84コメント/event)に不適切

#### A. LDA + BERTopic ハイブリッド
```python
from sklearn.decomposition import LatentDirichletAllocation
from bertopic import BERTopic

def hybrid_topic_model(docs, n_topics=10):
    # Step 1: BERTopicでEmbedding
    embeddings = embedding_model.encode(docs)
    
    # Step 2: UMAPで次元削減
    umap_embeddings = umap.UMAP(n_components=5).fit_transform(embeddings)
    
    # Step 3: LDAでトピック抽出 (小規模データに強い)
    vectorizer = CountVectorizer(max_features=500)
    doc_term_matrix = vectorizer.fit_transform(docs)
    lda = LatentDirichletAllocation(n_components=n_topics)
    lda_topics = lda.fit_transform(doc_term_matrix)
    
    # Step 4: 両者の結果を統合
    combined_topics = merge_topics(bertopic_topics, lda_topics)
    return combined_topics
```

**実装タスク**:
- [ ] `utils/hybrid_topic_model.py` 作成
- [ ] BERTopic vs LDA vs Hybrid 性能比較
- [ ] 最適な統合重み決定 (α_bert=0.6, α_lda=0.4)

**期待効果**: Topic coherence +20-30%, 小規模データ対応

---

### 2.2 Contextual N-gram Extraction (Priority: 🟠 HIGH)

**問題**: TF-IDFが文脈を無視、"kkk"などノイズを抽出

#### A. BERT-based Keyphrase Extraction
```python
from keybert import KeyBERT

kw_model = KeyBERT(model='paraphrase-multilingual-MiniLM-L12-v2')

def extract_contextual_keyphrases(docs, top_n=5):
    # BERT embeddingベースのキーフレーズ抽出
    keyphrases = kw_model.extract_keywords(
        docs, 
        keyphrase_ngram_range=(1, 3),  # 1-3 word phrases
        stop_words='english',  # + 日本語、スペイン語
        top_n=top_n,
        diversity=0.5  # Max Marginal Relevance (多様性確保)
    )
    return keyphrases
```

**実装タスク**:
- [ ] `pip install keybert` 追加
- [ ] 多言語ストップワード整備
- [ ] TF-IDF vs KeyBERT 比較

**期待効果**: N-gram質 +40-50%, ノイズ削減

---

#### B. Named Entity Recognition (NER)
```python
import spacy

nlp_en = spacy.load('en_core_web_sm')
nlp_ja = spacy.load('ja_core_news_sm')

def extract_entities(docs, lang='ja'):
    nlp = nlp_ja if lang == 'ja' else nlp_en
    entities = []
    for doc in docs:
        doc_nlp = nlp(doc)
        entities.extend([
            ent.text for ent in doc_nlp.ents 
            if ent.label_ in ['PERSON', 'ORG', 'EVENT', 'GPE']
        ])
    return Counter(entities).most_common(10)
```

**実装タスク**:
- [ ] spaCy NER統合
- [ ] 選手名、チーム名の自動抽出
- [ ] エンティティベースのイベントラベル生成

**期待効果**: イベント解釈性 +大幅向上

---

### 2.3 時系列分析の強化 (Priority: 🟡 MEDIUM)

#### A. Dynamic Time Warping (DTW)
```python
from dtaidistance import dtw

def compute_temporal_similarity(ts1, ts2):
    # 時系列パターンの類似度 (位相ずれに頑健)
    distance = dtw.distance(ts1, ts2)
    similarity = 1 / (1 + distance)
    return similarity
```

**実装タスク**:
- [ ] DTWベースの時間的マッチング
- [ ] Temporal correlationの精度向上
- [ ] 位相ずれ(lag)の可視化

**期待効果**: Temporal correlation精度 +15-20%

---

#### B. Change Point Detection
```python
import ruptures as rpt

def detect_events_via_changepoint(cpm_series):
    # CPMの急激な変化点 = イベント候補
    algo = rpt.Pelt(model='rbf').fit(cpm_series)
    changepoints = algo.predict(pen=10)
    return changepoints
```

**実装タスク**:
- [ ] Change point detectionアルゴリズム統合
- [ ] BERTopicとの結果比較
- [ ] アンサンブル手法の検討

**期待効果**: Event detection recall +10-15%

---

## 📋 Phase 3: 統計的妥当性の確保 (Dec 2-7)

### 3.1 Cross-Validation (Priority: 🔴 CRITICAL)

**目標**: 学会査読に耐える統計的妥当性

#### A. K-Fold Cross-Validation
```python
from sklearn.model_selection import KFold

def cross_validate_event_detection(streams, k=5):
    kf = KFold(n_splits=k, shuffle=True, random_state=42)
    results = []
    
    for train_idx, test_idx in kf.split(streams):
        train_streams = [streams[i] for i in train_idx]
        test_streams = [streams[i] for i in test_idx]
        
        # Train: パラメータ最適化
        model = optimize_parameters(train_streams)
        
        # Test: 検証
        precision, recall, f1 = evaluate_model(model, test_streams)
        results.append({'precision': precision, 'recall': recall, 'f1': f1})
    
    return pd.DataFrame(results)
```

**実装タスク**:
- [ ] K-Fold CV実装 (k=5)
- [ ] 平均性能 ± 標準偏差レポート
- [ ] Fold間の分散分析 (ANOVA)

**期待効果**: 結果の再現性・一般化性能保証

---

### 3.2 統計的有意性検定 (Priority: 🟠 HIGH)

#### A. Bootstrap Confidence Intervals
```python
from scipy.stats import bootstrap

def bootstrap_ci(data, statistic=np.mean, n_resamples=10000):
    rng = np.random.default_rng(42)
    res = bootstrap(
        (data,), 
        statistic, 
        n_resamples=n_resamples,
        confidence_level=0.95,
        random_state=rng
    )
    return res.confidence_interval
```

**実装タスク**:
- [ ] 全評価指標にBootstrap CI追加
- [ ] 95% CIを図表に表示
- [ ] CI幅の妥当性検討

**期待効果**: 統計的信頼性 +大幅向上

---

#### B. Inter-Rater Reliability
```python
from sklearn.metrics import cohen_kappa_score

def compute_inter_rater_reliability(annotator1, annotator2):
    kappa = cohen_kappa_score(annotator1, annotator2)
    # Interpretation:
    # 0.81-1.0: Almost perfect agreement
    # 0.61-0.80: Substantial agreement
    # 0.41-0.60: Moderate agreement
    return kappa
```

**実装タスク**:
- [ ] 複数人でGround Truth作成 (n≥2)
- [ ] Cohen's Kappa計算 (目標: κ≥0.7)
- [ ] 不一致事例の再検討

**期待効果**: アノテーション品質保証

---

### 3.3 ベースライン比較 (Priority: 🟡 MEDIUM)

#### A. Baseline Methods
```python
baselines = {
    'Random': random_event_detection,
    'TF-IDF + Cosine': tfidf_cosine_similarity,
    'LDA': lda_topic_model,
    'BERTopic (original)': bertopic_original,
    'Proposed (Hybrid)': proposed_hybrid_method,
}
```

**実装タスク**:
- [ ] 5つのベースライン実装
- [ ] 統一評価プロトコルで比較
- [ ] 統計的有意差検定 (Wilcoxon signed-rank test)

**期待効果**: 手法の優位性の実証

---

## 📋 Phase 4: 論文品質向上 (Dec 8-14)

### 4.1 Ablation Study (Priority: 🔴 CRITICAL)

**目標**: 各コンポーネントの寄与を定量化

```python
configurations = [
    {'embedding': True, 'topic': False, 'lexical': False},  # Embedding only
    {'embedding': False, 'topic': True, 'lexical': False},  # Topic only
    {'embedding': False, 'topic': False, 'lexical': True},  # Lexical only
    {'embedding': True, 'topic': True, 'lexical': False},   # Emb + Topic
    {'embedding': True, 'topic': True, 'lexical': True},    # All (proposed)
]

for config in configurations:
    performance = evaluate(config)
    print(f"Config: {config}, F1: {performance['f1']:.3f}")
```

**実装タスク**:
- [ ] Ablation Study実装
- [ ] 各コンポーネントの寄与グラフ作成
- [ ] 統計的有意差検定

**期待効果**: 論文のRobustness向上

---

### 4.2 Error Analysis (Priority: 🟠 HIGH)

#### A. False Positive分析
```python
def analyze_false_positives(predictions, ground_truth):
    fp_cases = [p for p in predictions if p not in ground_truth]
    
    # FPの原因分類
    categories = {
        'noise': [],      # ノイズトピック
        'spam': [],       # ボット・スパム
        'temporal': [],   # 時刻ずれ
        'semantic': [],   # 意味的類似性誤判定
    }
    
    for fp in fp_cases:
        category = classify_error(fp)
        categories[category].append(fp)
    
    return categories
```

**実装タスク**:
- [ ] FP/FN事例の詳細分析
- [ ] エラー原因のカテゴリ化
- [ ] 改善提案の生成

**期待効果**: 手法の限界の明確化 (Limitations section)

---

### 4.3 可視化の改善 (Priority: 🟡 MEDIUM)

#### A. インタラクティブ可視化
```python
import plotly.graph_objects as go

def create_interactive_timeline(events):
    fig = go.Figure()
    
    for stream in events['stream'].unique():
        stream_events = events[events['stream'] == stream]
        fig.add_trace(go.Scatter(
            x=stream_events['timestamp'],
            y=stream_events['cpm'],
            mode='lines+markers',
            name=stream,
            hovertext=stream_events['top_words'],
        ))
    
    fig.write_html('output/interactive_timeline.html')
```

**実装タスク**:
- [ ] Plotlyによるインタラクティブ図表
- [ ] イベントホバー時に詳細表示
- [ ] ズーム・パン機能

**期待効果**: 論文の視覚的説得力向上

---

## 📊 実装優先順位マトリックス

| タスク | Impact | Effort | Priority | Week |
|--------|--------|--------|----------|------|
| **Time Binning最適化** | 🔴 High | 🟢 Low | P1 | Week 1 |
| **Embedding Threshold調整** | 🔴 High | 🟢 Low | P1 | Week 1 |
| **ノイズフィルタリング** | 🔴 High | 🟡 Med | P1 | Week 1 |
| **Ground Truth作成** | 🔴 High | 🟡 Med | P1 | Week 1 |
| **Hybrid Topic Model** | 🟠 Med | 🔴 High | P2 | Week 2 |
| **KeyBERT統合** | 🟠 Med | 🟡 Med | P2 | Week 2 |
| **Cross-Validation** | 🔴 High | 🟡 Med | P2 | Week 2 |
| **Ablation Study** | 🔴 High | 🟢 Low | P2 | Week 2 |
| **NER統合** | 🟡 Low | 🔴 High | P3 | Optional |
| **DTW実装** | 🟡 Low | 🔴 High | P3 | Optional |

**凡例**:
- Impact: 🔴 High, 🟠 Medium, 🟡 Low
- Effort: 🔴 High (>1日), 🟡 Med (4-8時間), 🟢 Low (<4時間)
- Priority: P1 (必須), P2 (推奨), P3 (オプション)

---

## 🎯 期待される成果 (2週間後)

### 定量的目標

| 指標 | 現状 | 目標 | 改善幅 |
|------|------|------|--------|
| **Topic Jaccard (>0)** | 20% | 60% | +40% |
| **High Similarity (≥0.7)** | 10% | 40% | +30% |
| **F1 Score** | ? | 0.75+ | - |
| **Precision** | ? | 0.80+ | - |
| **Recall** | ? | 0.70+ | - |
| **Paper Quality** | 6/10 | 8-9/10 | +2-3 |

### 定性的目標

- ✅ **学会査読基準**を満たす統計的妥当性
- ✅ **再現性**を保証するパラメータ最適化プロトコル
- ✅ **ベースライン比較**による手法の優位性実証
- ✅ **Ablation Study**による各コンポーネントの寄与定量化
- ✅ **Ground Truth**による客観的評価
- ✅ **Error Analysis**による手法の限界明示

---

## 📝 論文執筆への反映

### Methods Section 追加項目

#### 3.X Event Detection and Matching
```markdown
3.X.1 Hybrid Topic Modeling
- BERTopic + LDA統合手法の説明
- 小規模データへの対応の正当化

3.X.2 Contextual Keyphrase Extraction
- KeyBERT-based N-gram抽出
- 多言語対応のストップワード設計

3.X.3 Parameter Optimization
- Grid Search + Cross-Validation
- 最適パラメータの理論的根拠

3.X.4 Evaluation Protocol
- Ground Truth作成手順
- Inter-rater reliability (Cohen's Kappa)
- Evaluation metrics (Precision, Recall, F1)
```

### Results Section 追加項目

#### 4.X Event Detection Performance
```markdown
4.X.1 Baseline Comparison
- 5つのベースライン手法との比較
- 統計的有意差検定結果 (p<0.05)

4.X.2 Ablation Study
- 各コンポーネントの寄与
- 最適重み (α_emb=0.7, α_topic=0.2, α_lex=0.1)

4.X.3 Cross-Validation Results
- 5-fold CV平均性能 ± 標準偏差
- 一般化性能の保証
```

### Discussion Section 追加項目

#### 5.X Limitations
```markdown
5.X.1 Data Scale Limitations
- 9ストリームのみ (今後の拡張方向)

5.X.2 Language Processing Challenges
- スラング、新語への対応限界
- 多言語NERの精度課題

5.X.3 Temporal Synchronization
- ストリーム間の時刻ずれ (±5秒)
```

---

## 🚀 実行計画 (2週間スケジュール)

### Week 1 (Nov 17-24): Quick Wins

| 日付 | タスク | 所要時間 | 担当 |
|------|--------|----------|------|
| **11/17 (日)** | Ground Truth作成 (30 events) | 3時間 | ✅ |
| **11/18 (月)** | Time Binning最適化 | 4時間 | - |
| **11/19 (火)** | Embedding Threshold最適化 | 4時間 | - |
| **11/20 (水)** | ノイズフィルタリング実装 | 3時間 | - |
| **11/21 (木)** | 評価スクリプト作成 | 3時間 | - |
| **11/22 (金)** | 中間評価・レポート作成 | 2時間 | - |
| **11/23-24** | バッファ・予備 | - | - |

**Week 1目標**: Paper Quality 6/10 → 7/10

---

### Week 2 (Nov 25-Dec 1): Deep Improvements

| 日付 | タスク | 所要時間 | 担当 |
|------|--------|----------|------|
| **11/25 (月)** | Hybrid Topic Model実装 | 6時間 | - |
| **11/26 (火)** | KeyBERT統合 | 4時間 | - |
| **11/27 (水)** | Cross-Validation実装 | 4時間 | - |
| **11/28 (木)** | Ablation Study実行 | 3時間 | - |
| **11/29 (金)** | ベースライン比較実験 | 4時間 | - |
| **11/30 (土)** | 最終評価・統計検定 | 3時間 | - |
| **12/1 (日)** | レポート完成・コミット | 2時間 | - |

**Week 2目標**: Paper Quality 7/10 → 8-9/10

---

## 📚 必要なライブラリ追加

```bash
# Week 1
pip install keybert  # Contextual keyphrase extraction
pip install spacy  # NER
python -m spacy download en_core_web_sm
python -m spacy download ja_core_news_sm

# Week 2
pip install dtaidistance  # Dynamic Time Warping
pip install ruptures  # Change point detection
pip install plotly  # Interactive visualization
pip install scikit-learn  # Cross-validation, metrics
```

---

## ✅ チェックリスト

### Phase 1 (Week 1)
- [ ] Ground Truth 30 events作成完了
- [ ] Cohen's Kappa ≥ 0.7 達成
- [ ] Time Binning最適化 (Grid Search)
- [ ] Embedding Threshold最適化 (ROC Curve)
- [ ] ノイズフィルタリング実装
- [ ] 評価スクリプト完成
- [ ] Week 1レポート作成

### Phase 2 (Week 2)
- [ ] Hybrid Topic Model実装・検証
- [ ] KeyBERT統合完了
- [ ] Cross-Validation実施 (k=5)
- [ ] Ablation Study完了
- [ ] ベースライン比較完了
- [ ] 統計的有意差検定完了
- [ ] Paper Quality ≥ 8/10 達成

### Phase 3 (論文執筆時)
- [ ] Methods Section更新
- [ ] Results Section更新
- [ ] Limitations Section追加
- [ ] 図表更新 (Bootstrap CI追加)
- [ ] 再現性確保 (パラメータ明記)

---

## 📊 成功指標

### 最低基準 (学会投稿可能レベル)
- ✅ Topic Jaccard (>0): **≥50%**
- ✅ F1 Score: **≥0.70**
- ✅ Cohen's Kappa: **≥0.70**
- ✅ Cross-Validation: **標準偏差 <0.05**
- ✅ Paper Quality: **≥8/10**

### 理想的目標
- 🎯 Topic Jaccard (>0): **≥60%**
- 🎯 F1 Score: **≥0.75**
- 🎯 Precision: **≥0.80**
- 🎯 Recall: **≥0.70**
- 🎯 Paper Quality: **9/10**

---

## 🎓 学術的正当性の確保

### 1. 再現性
- ✅ 全パラメータをREADMEに明記
- ✅ Random seed固定 (seed=42)
- ✅ データセット公開準備
- ✅ コード公開 (GitHub)

### 2. 妥当性
- ✅ Ground Truth with Inter-rater reliability
- ✅ Cross-Validation
- ✅ Baseline comparison
- ✅ Statistical significance testing

### 3. 透明性
- ✅ Ablation Study (各コンポーネントの寄与)
- ✅ Error Analysis (FP/FN分析)
- ✅ Limitations明記
- ✅ 失敗実験も報告

---

## 📞 サポート体制

### 質問・相談
- Advisor定期ミーティング (11/24, 12/1)
- 技術的問題: Stack Overflow, GitHub Issues
- 統計的助言: 統計担当教員

### 進捗報告
- 毎日: Git commit with詳細メッセージ
- 週次: Progress report (この計画書更新)
- 最終: Comprehensive report (Dec 1)

---

**このロードマップに従えば、2週間で学会論文レベル(Paper Quality 8-9/10)を達成できます!** 🚀

**次のステップ**: Ground Truth作成から開始しましょう! 📝
