# 学会発表用の推奨実行コマンド

**重要：埋め込みベースマッチング（--embedding-match-th）を使用することで、異なる言語・表現でも意味的に類似したトピックを正確にマッチングできます。**

## 高速テスト用（動作確認）
# 5-10分で完了、マッチング確認用
python event_comparison.py `
  --folder data/football/game4 `
  --pattern "*.csv" `
  --time-bins 50 `
  --n-events 3 `
  --focus-top 5 `
  --word-match-th 0.05 `
  --time-match-th 15 `
  --embedding-match-th 0.6 `
  --emoji-topk 5

## バランス型（推奨）★
# 15-20分で完了、論文・ポスター用
python event_comparison.py `
  --folder data/football/game4 `
  --pattern "*.csv" `
  --time-bins 100 `
  --n-events 5 `
  --focus-top 10 `
  --word-match-th 0.05 `
  --time-match-th 15 `
  --embedding-match-th 0.65 `
  --emoji-topk 10

## 高精度型（最終版）
# 30-40分で完了、学会発表本番用
python event_comparison.py `
  --folder data/football/game4 `
  --pattern "*.csv" `
  --time-bins 150 `
  --n-events 8 `
  --focus-top 15 `
  --word-match-th 0.05 `
  --time-match-th 12 `
  --embedding-match-th 0.7 `
  --emoji-topk 15 `
  --save-json

## パラメータ説明

### --time-bins
- 小さい（50）：処理高速、粗い分析
- 中程度（100）：バランス型
- 大きい（150-200）：精密だが重い

### --n-events
- 各配信者から抽出するピークイベント数
- 多いほど多くのイベントが比較対象になる

### --focus-top
- 上位何グループのトピックからイベントを抽出するか
- コメント数の多いトピックに絞ることで質を向上

### --word-match-th
- トピック間の単語一致度の閾値（Jaccard係数）
- **埋め込みマッチング使用時は0.05程度に設定**（補助的な役割）
- 埋め込み未使用時：0.1-0.15が推奨
- 注意：多言語・異なる表現では語彙が重ならないため、Jaccardのみでは不十分

### --embedding-match-th（重要！）
- コメント内容の意味的類似度の閾値（コサイン類似度）
- **推奨値：0.6-0.7**
- 低い（0.5-0.6）：多くマッチ、やや緩い
- 中程度（0.6-0.7）：バランス型★
- 高い（0.75以上）：非常に厳密、マッチが少ない
- **多言語配信の分析には必須**（日本語・英語・スペイン語など）

### --time-match-th
- 時間差の許容範囲（bins数）
- 大きいほど時間がずれたイベントもマッチ
- time-bins=100の場合、15 bins ≈ 試合時間の15%

### --emoji-topk
- 絵文字タイムラインに表示する上位絵文字数
- 多すぎると見づらい、少なすぎると情報不足

## 出力ファイル

### 主要な可視化（学会発表用）
- `output/matched_event_presence.png` - 類似トピックの時間帯別比較（メイン）
- `output/emoji_timelines/*.png` - 各配信者の絵文字タイムライン
- `output/timelines/*.png` - トピック時系列グラフ
- `output/event_comparison_results.png` - 配信者間距離行列

### データファイル
- `output/similar_event_comparison_results.csv` - 類似イベントの定量データ
- `output/similar_event_details.csv` - イベント詳細情報
- `output/emoji_rankings/emoji_rankings.csv` - 絵文字ランキング

## トラブルシューティング

### "No similar events matched" が出る場合
**解決策：埋め込みベースマッチングを使用する**
1. `--embedding-match-th 0.6` を追加（最優先）
2. `--word-match-th` を 0.05 に下げる
3. `--time-match-th` を 20 に上げる
4. `--time-bins` を 50 に下げる

**背景説明：**
- 各配信者が独自の語彙（スペイン語vs日本語など）を使用
- Jaccard係数（語彙の重なり）だけではマッチング不可
- 埋め込みベクトル（意味的類似度）が必須

### 処理が遅い場合
1. `--time-bins` を 50 に下げる
2. `--n-events` を 3 に減らす
3. `--focus-top` を 5 に減らす

### メモリエラーが出る場合
1. CSVファイルのサイズを確認
2. 一度に処理するファイル数を減らす
3. `--time-bins` を小さくする

## 実行チェックリスト

### 実行前
- [ ] data/footballフォルダにCSVファイルがある
- [ ] Python環境が有効化されている
- [ ] 必要なライブラリがインストール済み

### 実行中
- [ ] プログレスが進んでいる
- [ ] エラーが出ていない
- [ ] メモリ使用量が許容範囲内

### 実行後
- [ ] outputフォルダに画像ファイルが生成された
- [ ] matched_event_presence.png が存在する
- [ ] 絵文字タイムラインが生成された
- [ ] CSVファイルに数値データがある

## 結果の確認

### 定量的指標
1. **マッチした類似イベント数**: 10-50が目安
2. **平均類似度**: 0.3-0.7が正常
3. **各配信者のイベント数**: バランスが取れているか

### 定性的評価
1. **matched_event_presence.png**: 時間帯にパターンがあるか
2. **トピックラベル**: 意味のある内容か
3. **絵文字タイムライン**: 試合展開と一致するか

## 次のステップ

### 結果が良好な場合
1. 高精度型で再実行
2. 追加の可視化を生成
3. 統計分析を実施

### 結果が不十分な場合
1. パラメータを調整
2. データの前処理を見直し
3. トピック数を調整（jaccard-th）

## 学会発表用の図表作成

### 推奨される図表構成
1. **システム概要図**: 手法の全体像
2. **matched_event_presence.png**: メイン結果
3. **事例紹介**: 具体的なトピックとコメント例
4. **統計サマリー**: 定量的な評価指標
5. **絵文字タイムライン**: 補助資料

### 図表のブラッシュアップ
- 解像度: 300dpi以上
- フォントサイズ: 読みやすく
- カラーマップ: 見やすい配色
- ラベル: 簡潔で明確
