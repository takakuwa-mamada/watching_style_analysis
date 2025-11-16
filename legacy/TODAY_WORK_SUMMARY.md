# Event Comparison - 今日の作業まとめ

## 実施した改善

### 1. 絵文字タイムラインの修正 ✅
**問題**: 縦長で見にくい、絵文字が文字化け

**解決策**:
- 図を転置（時間を横軸、絵文字を縦軸）
- 図のサイズを横長に調整
  - 横幅: `max(12, 0.4 * len(time_bins) + 2)`
  - 高さ: `max(4, 0.3 * len(emojis) + 1)`
- 絵文字フォント（seguiemj.ttf）を明示的に使用

**修正箇所**: `save_emoji_timeline_heatmap()` 関数 (1114行目付近)

### 2. 機能フラグの導入 ✅
**目的**: 不要な機能を無効化してパフォーマンス向上

**追加したフラグ** (145行目付近):
```python
ENABLE_WORDCLOUDS = False        # ワードクラウド生成（重い処理、ユーザー要求外）
ENABLE_DETAILED_METRICS = False  # 詳細なペアワイズメトリクス（ユーザー要求外）
ENABLE_JSON_EXPORT = True        # JSON出力（デバッグ用）
```

**効果**:
- ワードクラウド生成をスキップ（3箇所）
- 処理時間の短縮
- 将来的な機能追加・削除が容易

### 3. デバッグ出力の追加 ✅
**目的**: matched_event_presence.png が生成されない原因を特定

**追加した出力**:
```python
print(f"[DEBUG] Matching parameters: word_match_th={args.word_match_th}, time_match_th={args.time_match_th}")
print(f"[DEBUG] Total events: {sum(len(evts) for evts in events_by_stream.values())}")
print(f"[DEBUG] Similar event map created with {len(set(similar_event_map.values()))} unique groups")
```

## 現在の課題

### matched_event_presence.png が生成されない
**原因（推測）**:
1. 閾値が厳しすぎる（`word_match_th=0.2`, `time_match_th=5`）
2. テストデータに類似トピックが少ない
3. トピック分類の粒度が細かすぎる

**解決策（テスト中）**:
- 閾値を大幅に緩和: `word_match_th=0.05`, `time_match_th=20`
- `time_bins=100` に削減（処理高速化）
- デバッグ出力で実際のマッチング状況を確認

## 長期的な改善計画

### Phase 1: 緊急対応（今日〜明日）
- [x] 絵文字タイムライン修正
- [x] ワードクラウド無効化
- [x] デバッグ出力追加
- [ ] matched_event_presence.png の動作確認
- [ ] 最適な閾値の決定

### Phase 2: コードのモジュール化（1週間以内）
現在のコード構造:
```
event_comparison.py (2400行)
  ├─ トピック分類
  ├─ イベント抽出
  ├─ イベントマッチング
  ├─ 類似度計算
  ├─ 可視化（複数種類）
  └─ 絵文字分析
```

提案する構造:
```
watching_style_analysis/
  ├─ core/
  │   ├─ topic_modeling.py      # BERTopicの処理
  │   ├─ event_detection.py     # ピークイベント抽出
  │   ├─ event_matching.py      # 類似イベント検出
  │   └─ similarity.py          # JS距離計算
  ├─ visualization/
  │   ├─ heatmap.py             # ヒートマップ生成
  │   ├─ emoji_timeline.py      # 絵文字タイムライン
  │   └─ matched_events.py      # matched_event_presence.png
  ├─ utils/
  │   ├─ data_loader.py         # CSV読み込み
  │   ├─ preprocessing.py       # テキスト前処理
  │   └─ cache.py               # キャッシュ管理
  └─ main.py                    # メインスクリプト
```

**利点**:
- 各機能を個別にテスト・実行可能
- コードの再利用性向上
- 保守性の向上
- 並列処理の導入が容易

### Phase 3: パフォーマンス最適化（1ヶ月以内）

#### 3.1 キャッシュシステム
**目的**: BERTopicの結果を再利用して処理時間を大幅短縮

実装例:
```python
def process_stream_with_cache(csv_file, cache_dir="cache"):
    cache_file = os.path.join(cache_dir, f"{basename}_topics.pkl")
    
    if os.path.exists(cache_file) and not args.force_recalc:
        print(f"Loading cached topics from {cache_file}")
        with open(cache_file, "rb") as f:
            cached_data = pickle.load(f)
        return cached_data
    
    # 新規計算
    stream_data = process_stream(csv_file, ...)
    
    # キャッシュ保存
    with open(cache_file, "wb") as f:
        pickle.dump(stream_data, f)
    
    return stream_data
```

**効果**:
- 初回実行: 現在と同じ（数十分）
- 2回目以降: 数秒〜数分（トピック分類をスキップ）

#### 3.2 並列処理
**目的**: 複数CSVを並列処理

実装例:
```python
from multiprocessing import Pool

def main():
    csv_files = get_csv_files(...)
    
    # 並列処理でトピック分類
    with Pool(processes=4) as pool:
        streams = pool.map(process_stream_parallel, csv_files)
    
    # イベントマッチングは逐次処理
    event_map = match_events_across_streams(...)
```

**効果**:
- 4つのCSVを処理する場合、理論上4倍高速
- 実際は2〜3倍程度の高速化が期待できる

#### 3.3 軽量モデルの検討
現在のモデル:
```python
EMB_NAME = "sentence-transformers/xlm-r-100langs-bert-base-nli-stsb-mean-tokens"
```

代替案:
```python
# オプション1: より軽量な多言語モデル
EMB_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# オプション2: 日本語特化モデル（日本語のみの場合）
EMB_NAME = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
```

**トレードオフ**:
- 速度: 2〜3倍高速
- 精度: やや低下する可能性（要検証）

### Phase 4: ユーザビリティ向上

#### 4.1 プログレスバー
```python
from tqdm import tqdm

for csv_file in tqdm(csv_files, desc="Processing streams"):
    process_stream(csv_file, ...)
```

#### 4.2 設定ファイル対応
```yaml
# config.yaml
topic_modeling:
  time_bins: 100
  jaccard_th: 0.5

event_matching:
  word_match_th: 0.05
  time_match_th: 20

visualization:
  enable_wordclouds: false
  enable_emoji_timeline: true
```

#### 4.3 ログレベル制御
```python
import logging

parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING"], default="INFO")
logging.basicConfig(level=args.log_level)
```

## 技術的な補足

### なぜ類似トピックがマッチしないのか？

#### 可能性1: Jaccard類似度の閾値が高すぎる
**Jaccard類似度**:
```
J(A, B) = |A ∩ B| / |A ∪ B|
```

例:
- トピックA: ["goal", "score", "game"]
- トピックB: ["goal", "match", "play"]
- Jaccard = 1/5 = 0.2

`word_match_th=0.2` だと、5つの語のうち1つしか共通していないとマッチしない。

#### 可能性2: 時間差の閾値が狭すぎる
`time_match_th=5` だと、binが5つ以内でないとマッチしない。

`time_bins=300` の場合:
- 1 bin ≈ 試合時間 / 300
- 例: 2時間の試合 → 1 bin = 24秒
- 5 bins = 120秒 = 2分

同じ出来事でも配信者によって2分以上ズレることは十分あり得る。

#### 解決策
1. `word_match_th` を 0.05〜0.1 に下げる
2. `time_match_th` を 10〜20 に上げる
3. `time_bins` を 50〜100 に減らす（1 bin が長くなる）

### 今後のテスト推奨パラメータ

**バランス型**（精度と速度のバランス）:
```bash
python event_comparison.py \
  --folder data/football \
  --pattern "*.csv" \
  --time-bins 100 \
  --n-events 5 \
  --focus-top 10 \
  --word-match-th 0.1 \
  --time-match-th 15 \
  --emoji-topk 10
```

**高速型**（動作確認用）:
```bash
python event_comparison.py \
  --folder data/football \
  --pattern "*.csv" \
  --time-bins 50 \
  --n-events 3 \
  --focus-top 5 \
  --word-match-th 0.05 \
  --time-match-th 20 \
  --emoji-topk 5
```

**高精度型**（最終成果物用）:
```bash
python event_comparison.py \
  --folder data/football \
  --pattern "*.csv" \
  --time-bins 200 \
  --n-events 10 \
  --focus-top 20 \
  --word-match-th 0.15 \
  --time-match-th 10 \
  --emoji-topk 15
```

## 次のステップ

1. **現在のテスト結果を確認**
   - デバッグ出力を見て、何件のイベントがマッチしたか確認
   - matched_event_presence.png が生成されたか確認

2. **最適な閾値を決定**
   - 複数のパラメータでテスト実行
   - 結果を比較して最適な設定を決定

3. **ドキュメント整備**
   - README.md に使い方を明記
   - パラメータの説明を詳細に記載
   - サンプルコマンドを追加

4. **モジュール化の検討**
   - 2週間以内にリファクタリング計画を立てる
   - 段階的に実装

5. **テストケースの追加**
   - 小規模データでユニットテスト
   - 期待される出力との比較

## まとめ

### 今日の成果
- ✅ 絵文字タイムライン修正（横長、フォント対応）
- ✅ ワードクラウド無効化（パフォーマンス向上）
- ✅ デバッグ出力追加
- ⏳ matched_event_presence.png の動作確認中

### 残りの課題
- matched_event_presence.png の生成確認
- 最適な閾値の決定
- 長期的なリファクタリング計画の実行

### 推奨される次のアクション
1. テスト結果を確認
2. 閾値を調整して再テスト
3. 動作が確認できたら、モジュール化を検討
