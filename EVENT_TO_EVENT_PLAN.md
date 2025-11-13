# Event-to-Event Comparison Implementation Plan

## 現在の問題

### ❌ 現在の実装
```
similar_event_comparison_results.csv:
- sim_event_id: 16, 31, 39 (各イベント)
- 列: "Bra.csv vs Ja_abema.csv (lex)" ← Stream間の比較
```

**問題点:**
- 各イベント内での配信者間（Stream間）の距離を計算
- イベント同士の類似度を計算していない
- ユーザーの要求と完全に異なる

### ✅ 求められている実装
```
event_to_event_similarity.csv:
- event_A_id: 16
- event_B_id: 31  
- similarity: 0.75
- shared_topics: ["goal", "brasil"]
- time_diff_sec: 120
```

**イベント間の類似度:**
- Event 16 vs Event 31
- Event 16 vs Event 39  
- Event 31 vs Event 39
- すべてのイベントペアの類似度マトリックス

---

## 新しい設計

### 1. イベント表現の統合
各イベント（複数配信者の盛り上がりをまとめたもの）を1つのベクトルで表現：

```python
def aggregate_event_representation(evts_dict, streams):
    """
    複数配信者のイベントを統合して1つの表現を作成
    
    Returns:
    - aggregated_embedding: 平均埋め込みベクトル
    - aggregated_comments: 全配信者のコメントを結合
    - aggregated_topics: トピック語の集合
    """
    all_comments = []
    all_embeddings = []
    all_topics = set()
    
    for stream_key, evt in evts_dict.items():
        comments, _ = extract_event_comments(streams[stream_key], evt, pad)
        all_comments.extend(comments)
        
        if evt.get("embedding") is not None:
            all_embeddings.append(evt["embedding"])
        
        top_words = evt.get("top_words", [])
        all_topics.update(top_words)
    
    # 平均埋め込みベクトル
    if all_embeddings:
        aggregated_embedding = np.mean(all_embeddings, axis=0)
    else:
        aggregated_embedding = None
    
    return {
        "embedding": aggregated_embedding,
        "comments": all_comments,
        "topics": all_topics,
        "num_streams": len(evts_dict),
        "stream_keys": list(evts_dict.keys())
    }
```

### 2. イベント間類似度計算

```python
def compute_event_to_event_similarity(event_A, event_B):
    """
    2つのイベント間の類似度を複数の指標で計算
    
    Returns:
    - embedding_similarity: 埋め込みベクトルのコサイン類似度
    - topic_jaccard: トピック語のJaccard係数
    - lexical_similarity: コメント内容のJS距離ベース類似度
    """
    # 1. 埋め込み類似度
    if event_A["embedding"] is not None and event_B["embedding"] is not None:
        embedding_sim = float(np.dot(event_A["embedding"], event_B["embedding"]))
    else:
        embedding_sim = None
    
    # 2. トピックJaccard
    topics_A = event_A["topics"]
    topics_B = event_B["topics"]
    if topics_A or topics_B:
        topic_jaccard = len(topics_A & topics_B) / len(topics_A | topics_B)
    else:
        topic_jaccard = 0.0
    
    # 3. 語彙類似度
    lex_dist = compute_lexical_distance(
        event_A["comments"], 
        event_B["comments"]
    )
    lexical_sim = 1.0 - lex_dist
    
    return {
        "embedding_similarity": embedding_sim,
        "topic_jaccard": topic_jaccard,
        "lexical_similarity": lexical_sim,
        "combined_score": (embedding_sim * 0.5 + lexical_sim * 0.3 + topic_jaccard * 0.2) if embedding_sim else None
    }
```

### 3. イベント間類似度マトリックス生成

```python
def generate_event_similarity_matrix(events_by_sim_id, streams, args):
    """
    全イベントペアの類似度を計算
    
    Returns:
    - similarity_matrix: N×N類似度行列
    - event_pairs_df: ペアごとの詳細データ
    """
    # 各イベントの統合表現を作成
    event_representations = {}
    for sim_id, evts_dict in events_by_sim_id.items():
        if len(evts_dict) < 2:  # 2配信者以上が参加しているイベントのみ
            continue
        event_representations[sim_id] = aggregate_event_representation(
            evts_dict, streams
        )
    
    # ペアワイズ類似度計算
    event_ids = sorted(event_representations.keys())
    n = len(event_ids)
    
    similarity_matrix = np.zeros((n, n))
    event_pairs = []
    
    for i in range(n):
        for j in range(i+1, n):
            event_A_id = event_ids[i]
            event_B_id = event_ids[j]
            
            event_A = event_representations[event_A_id]
            event_B = event_representations[event_B_id]
            
            sim_scores = compute_event_to_event_similarity(event_A, event_B)
            
            # 代表類似度（埋め込みまたは総合スコア）
            main_sim = sim_scores["embedding_similarity"] or sim_scores["combined_score"] or sim_scores["lexical_similarity"]
            
            similarity_matrix[i, j] = main_sim
            similarity_matrix[j, i] = main_sim
            
            # 詳細データ保存
            event_pairs.append({
                "event_A_id": event_A_id,
                "event_B_id": event_B_id,
                "event_A_streams": event_A["num_streams"],
                "event_B_streams": event_B["num_streams"],
                "embedding_similarity": sim_scores["embedding_similarity"],
                "topic_jaccard": sim_scores["topic_jaccard"],
                "lexical_similarity": sim_scores["lexical_similarity"],
                "combined_score": sim_scores["combined_score"],
                "main_similarity": main_sim,
            })
    
    # 対角線は1.0（自分自身との類似度）
    np.fill_diagonal(similarity_matrix, 1.0)
    
    # DataFrameに変換
    sim_df = pd.DataFrame(
        similarity_matrix,
        index=[f"Event_{i}" for i in event_ids],
        columns=[f"Event_{i}" for i in event_ids]
    )
    
    pairs_df = pd.DataFrame(event_pairs).sort_values("main_similarity", ascending=False)
    
    return sim_df, pairs_df
```

### 4. 可視化の改善

#### A. Event-to-Event類似度ヒートマップ
```python
def save_event_similarity_heatmap(sim_df, out_csv, out_png):
    """
    イベント間類似度の N×N ヒートマップ
    - X軸: Event 1, Event 2, ..., Event N
    - Y軸: Event 1, Event 2, ..., Event N
    - 色: 類似度（0-1）
    """
    sim_df.to_csv(out_csv, encoding="utf-8-sig")
    
    plt.figure(figsize=(12, 10))
    sns.heatmap(
        sim_df.values,
        xticklabels=sim_df.columns,
        yticklabels=sim_df.index,
        cmap="YlOrRd",
        vmin=0, vmax=1,
        annot=True,  # 数値を表示
        fmt=".2f",
        cbar_kws={"label": "Similarity"}
    )
    plt.title("Event-to-Event Similarity Matrix")
    plt.xlabel("Events")
    plt.ylabel("Events")
    plt.tight_layout()
    plt.savefig(out_png, dpi=300)
    plt.close()
```

#### B. 類似イベントクラスター可視化
```python
def visualize_event_clusters(sim_df, event_metadata, out_png):
    """
    イベントを類似度に基づいてクラスタリングして可視化
    - 2D空間にプロット（MDS/t-SNE）
    - 類似イベント同士を近くに配置
    - 時間軸で色分け
    """
    from sklearn.manifold import MDS
    
    # 距離行列に変換（1 - similarity）
    distance_matrix = 1.0 - sim_df.values
    
    # 2D空間に埋め込み
    mds = MDS(n_components=2, dissimilarity="precomputed", random_state=42)
    coords = mds.fit_transform(distance_matrix)
    
    plt.figure(figsize=(12, 8))
    scatter = plt.scatter(
        coords[:, 0],
        coords[:, 1],
        c=event_metadata["time_bin"],  # 時間で色分け
        s=event_metadata["num_streams"] * 100,  # サイズ=参加配信者数
        cmap="viridis",
        alpha=0.7
    )
    
    # ラベル追加
    for i, (x, y) in enumerate(coords):
        plt.annotate(
            f"E{event_metadata.iloc[i]['event_id']}",
            (x, y),
            fontsize=8
        )
    
    plt.colorbar(scatter, label="Time (bin)")
    plt.title("Event Similarity Clustering")
    plt.xlabel("MDS Dimension 1")
    plt.ylabel("MDS Dimension 2")
    plt.tight_layout()
    plt.savefig(out_png, dpi=300)
    plt.close()
```

---

## 実装手順

### Step 1: イベント表現の統合関数を追加（Lines ~2000）
```python
def aggregate_event_representation(...):
    # 上記の実装
```

### Step 2: イベント間類似度計算関数を追加（Lines ~2050）
```python
def compute_event_to_event_similarity(...):
    # 上記の実装
```

### Step 3: 類似度マトリックス生成を追加（Lines ~2100）
```python
def generate_event_similarity_matrix(...):
    # 上記の実装
```

### Step 4: main()関数内で呼び出し（Lines ~2150）
```python
if similar_results:
    # 既存のstream間比較はそのまま
    
    # 新規: イベント間類似度計算
    print("[INFO] Computing event-to-event similarity...")
    sim_matrix_df, event_pairs_df = generate_event_similarity_matrix(
        events_by_sim_id, streams, args
    )
    
    # 保存
    out_csv = os.path.join(OUT_DIR, "event_to_event_similarity_matrix.csv")
    out_png = os.path.join(OUT_DIR, "event_to_event_similarity_matrix.png")
    save_event_similarity_heatmap(sim_matrix_df, out_csv, out_png)
    
    pairs_csv = os.path.join(OUT_DIR, "event_to_event_pairs.csv")
    event_pairs_df.to_csv(pairs_csv, index=False, encoding="utf-8-sig")
```

---

## 期待される出力

### 1. event_to_event_similarity_matrix.csv
```
,Event_16,Event_31,Event_39,...
Event_16,1.0,0.75,0.42,...
Event_31,0.75,1.0,0.68,...
Event_39,0.42,0.68,1.0,...
```

### 2. event_to_event_pairs.csv
```
event_A_id,event_B_id,embedding_similarity,topic_jaccard,lexical_similarity,combined_score,main_similarity
16,31,0.78,0.45,0.72,0.75,0.78
31,39,0.65,0.55,0.60,0.62,0.65
16,39,0.40,0.25,0.45,0.42,0.42
```

### 3. event_to_event_similarity_matrix.png
- N×Nヒートマップ
- 対角線=1.0（自分自身）
- 明るい色=高類似度
- 数値表示あり

---

## トピック分類の検証

### 問題点の可能性
1. **Jaccard閾値が高すぎる**
   - `--jaccard-th 0.6` → 多くのトピックが統合されない
   - 試合の同じ場面でも別トピックに分類

2. **BERTopicのパラメータ**
   - `min_topic_size` が大きすぎる
   - `-1`（ノイズ）トピックが多い

3. **語彙の正規化**
   - `normalize_term`の効果が不十分
   - 類義語が別トピックに

### 検証方法
```python
# トピック分類の品質確認
for stream_key, sd in streams.items():
    print(f"\n=== {os.path.basename(stream_key)} ===")
    print(f"Total topics: {len(sd.group_top_words)}")
    print(f"Topics after grouping: {len(set(sd.df_valid['topic'].values))}")
    
    # 各トピックの代表語を表示
    for gid, words in sd.group_top_words.items():
        print(f"Group {gid}: {' / '.join(words[:5])}")
```

---

## 次のアクション

1. **イベント間類似度計算の実装**（最優先）
2. **トピック分類の検証**
3. **可視化の改善**（読みやすく）
4. **パラメータ調整**（jaccard-th など）
