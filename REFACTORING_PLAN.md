# Event Comparison リファクタリング計画

## 現状の問題点

1. **パフォーマンス**: BERTopicの処理が非常に重い（大規模データで数十分）
2. **複雑性**: 単一ファイル2400行、多機能すぎて保守が困難
3. **ユーザビリティ**: 必要な機能だけを使いたいが、全処理が実行される

## ユーザーの要求（優先度順）

### 必須機能
1. ✅ トピック分類（BERTopic）
2. ✅ 似たトピックの検出（複数配信者間）
3. ⚠️ **matched_event_presence.png**: 似たトピック同士の類似度比較可視化
4. ✅ 絵文字タイムライン（横長、文字化け修正済み）

### 不要な機能（削除候補）
- 完全一致イベント処理（exact match）
- ワードクラウド生成（各イベント用）
- 詳細なペアワイズメトリクス
- 言語・感情・スタイル分析

## 長期的な改善計画

### Phase 1: 緊急対応（今日）
**目標**: ユーザーの要求を満たす最小限の機能を動作させる

- [ ] デバッグモードでmatched_event_presence.png生成ロジックを確認
- [ ] 閾値を調整して類似トピックマッチングを動作させる
- [ ] 不要な機能を条件分岐で無効化（削除はしない）

**実装方針**:
```python
# フラグで機能を制御
ENABLE_WORDCLOUDS = False
ENABLE_EXACT_MATCH = False  # 既に無効化済み
ENABLE_DETAILED_METRICS = False
```

### Phase 2: 機能分離（1週間以内）
**目標**: コードをモジュール化し、必要な機能だけを実行できるようにする

- [ ] `core_topic_analysis.py`: トピック分類のみ
- [ ] `event_matching.py`: 類似イベント検出
- [ ] `visualization.py`: 可視化機能
- [ ] `emoji_analysis.py`: 絵文字分析
- [ ] `main_pipeline.py`: 統合スクリプト（機能を選択可能）

**利点**:
- 各機能を個別にテスト・実行可能
- 保守性の向上
- パフォーマンス向上（必要な部分だけ実行）

### Phase 3: キャッシュシステム（1ヶ月以内）
**目標**: 重い処理結果をキャッシュして再利用

- [ ] トピック分類結果をpickle/jsonで保存
- [ ] キャッシュがあれば再利用、なければ新規実行
- [ ] `--force-recalc` オプションで強制再計算

**実装例**:
```python
cache_file = f"cache/{basename}_topics.pkl"
if os.path.exists(cache_file) and not args.force_recalc:
    topics = load_cache(cache_file)
else:
    topics = topic_model.fit_transform(texts)
    save_cache(topics, cache_file)
```

### Phase 4: 並列処理（長期）
**目標**: 複数CSVを並列処理してパフォーマンス向上

- [ ] multiprocessingで各配信者のトピック分類を並列化
- [ ] 結果を統合してイベントマッチング

## 今日の作業計画

### Step 1: 現在のコードで動作確認
1. 小規模データでテスト（--n-events 2, --focus-top 5）
2. デバッグ出力追加でマッチング失敗原因を特定
3. 閾値調整

### Step 2: 不要機能の無効化
1. ワードクラウド生成を無効化
2. 詳細メトリクスを無効化
3. 必要最小限の出力に絞る

### Step 3: matched_event_presence.png の確認
1. 類似トピックがマッチした場合の出力を確認
2. フォーマットがユーザーの要求と一致しているか検証

## 成功基準

### 短期（今日）
- ✅ 絵文字タイムラインが横長で正しく表示される
- ⚠️ matched_event_presence.pngが生成され、似たトピック同士の類似度が可視化される
- ⚠️ 実行時間が許容範囲内（10分以内）

### 中期（1週間）
- モジュール化完了
- 各機能を個別に実行可能
- ドキュメント整備

### 長期（1ヶ月）
- キャッシュシステム導入
- 実行時間大幅短縮（初回のみ重い、以降は軽い）
- 並列処理で高速化

## 技術的な改善ポイント

### パフォーマンス
- BERTopicのnr_binsを削減（現在300 → 50-100推奨）
- 埋め込みキャッシュ
- 軽量モデルの検討（paraphrase-multilingual-miniなど）

### コード品質
- 型ヒント完備
- Docstring整備
- ユニットテスト追加
- Linter/Formatter導入（black, flake8）

### ユーザビリティ
- プログレスバー追加（tqdm）
- ログレベル制御（--verbose, --quiet）
- 設定ファイル対応（YAML/JSON）
- エラーメッセージの改善

## 参考資料

- BERTopic公式: https://maartengr.github.io/BERTopic/
- SentenceTransformers: https://www.sbert.net/
- 類似度計算: Jensen-Shannon divergence, Jaccard similarity

---

## 次のアクション

1. デバッグ出力追加して類似トピックマッチングを確認
2. 不要機能を無効化
3. matched_event_presence.pngの動作確認
