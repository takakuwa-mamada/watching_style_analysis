# 次のアクションプラン（2025年11月6日）

## 🎯 現在の状況

### ✅ 完了した作業
1. **根本原因の特定**
   - Jaccard類似度（語彙ベース）では多言語配信がマッチング不可能
   - 配信者ごとに異なる語彙・表現を使用
   - Jaccard=0.0 → マッチングゼロ

2. **解決策の実装**
   - 埋め込みベース（意味的類似度）マッチングに変更
   - マッチングロジックの順序変更（埋め込み優先）
   - デフォルトパラメータの最適化
   - テスト実行：126/1980ペアがマッチング成功 ✅

3. **ドキュメント整備**
   - `RUN_COMMANDS.md` - game4用コマンド更新
   - `SOLUTION_SUMMARY.md` - 技術的な解決策まとめ
   - デバッグ出力の簡略化（DEBUG_VERBOSEフラグ）

4. **デフォルト設定の変更**
   - `--word-match-th`: 0.1 → 0.05
   - `--embedding-match-th`: None → 0.65（推奨値）
   - データパス：`data/football` → `data/football/game4`

### 🔄 実行中
- `game4`データ（UK、日本×2、ブラジル）で本番実行中
- パラメータ：time-bins=100, n-events=5, embedding-match-th=0.65

## 📋 次のアクション（優先順位順）

### 1. 実行結果の確認（最優先）⏳
**タスク：** game4実行完了後、生成ファイルを確認

**確認項目：**
- [ ] `output/matched_event_presence.png`が生成された
- [ ] similar event数が妥当（目安：20-100）
- [ ] 絵文字タイムラインが正常（横向き、文字化けなし）
- [ ] CSVファイルに定量データが含まれる

**コマンド：**
```powershell
# 実行状況確認
Get-Process python | Where-Object {$_.CPU -gt 0}

# 出力ファイル確認
Get-ChildItem output -Recurse -File | Select-Object Name, Length, LastWriteTime

# matched_event_presence.png確認
Test-Path output/matched_event_presence.png
```

**期待される結果：**
- matched_event_presence.png: 4配信者の類似トピック比較図
- 類似イベント数: 20-100件程度（4配信者の組み合わせ）
- 処理時間: 15-25分程度

---

### 2. 結果の品質評価（次優先）
**タスク：** 生成された図表の学会発表適合性を確認

**評価基準：**

#### matched_event_presence.png
- [ ] 時間軸が読みやすい
- [ ] トピックラベルが意味をなしている
- [ ] 配信者名が識別可能
- [ ] 類似度の数値が表示されている
- [ ] ヒートマップの色分けが明瞭

#### 定量評価
```bash
# CSVから統計サマリーを取得
python -c "
import pandas as pd
df = pd.read_csv('output/similar_event_comparison_results.csv')
print('類似イベント数:', len(df))
print('平均類似度:', df['similarity'].mean() if 'similarity' in df.columns else 'N/A')
print('配信者別イベント数:')
print(df.groupby('stream').size() if 'stream' in df.columns else 'N/A')
"
```

**目標値：**
- 類似イベント数: 20-100
- 平均類似度: 0.3-0.7
- 配信者ごとのイベント数: バランスが取れている

---

### 3. パラメータ最適化（結果による）

#### ケースA: マッチング数が少ない（<20）
```bash
# 閾値を緩める
python event_comparison.py \
  --folder data/football/game4 \
  --pattern "*.csv" \
  --time-bins 100 \
  --n-events 8 \
  --focus-top 15 \
  --embedding-match-th 0.6 \  # 0.65 → 0.6
  --time-match-th 20 \          # 15 → 20
  --emoji-topk 10
```

#### ケースB: マッチング数が多すぎる（>150）
```bash
# 閾値を厳しくする
python event_comparison.py \
  --folder data/football/game4 \
  --pattern "*.csv" \
  --time-bins 100 \
  --n-events 5 \
  --focus-top 8 \
  --embedding-match-th 0.7 \  # 0.65 → 0.7
  --time-match-th 12 \         # 15 → 12
  --emoji-topk 10
```

#### ケースC: 結果が良好（20-100）
→ 高精度版で再実行
```bash
python event_comparison.py \
  --folder data/football/game4 \
  --pattern "*.csv" \
  --time-bins 150 \
  --n-events 8 \
  --focus-top 15 \
  --embedding-match-th 0.7 \
  --emoji-topk 15 \
  --save-json
```

---

### 4. 学会発表用資料の準備

#### 図表のブラッシュアップ
1. **解像度向上**（現在：デフォルト → 目標：300dpi）
2. **フォントサイズ調整**（読みやすさ重視）
3. **カラーマップ変更**（発表会場での視認性）
4. **ラベルの簡潔化**（長すぎるラベルを短縮）

#### 補助資料の作成
- [ ] 具体的なコメント事例の抽出
- [ ] 統計サマリーテーブル
- [ ] システム概要図
- [ ] 手法説明スライド

#### データ分析
```python
# similar_event_comments.jsonから事例を抽出
import json
import pandas as pd

with open('output/similar_event_comments.json', 'r', encoding='utf-8') as f:
    comments = json.load(f)

# 最も類似度が高いイベントを抽出
df = pd.read_csv('output/similar_event_comparison_results.csv')
top_events = df.nlargest(5, 'similarity')  # 仮のカラム名

# 各イベントのコメント内容を確認
for event_id in top_events['sim_event_id']:
    print(f"\n=== Event {event_id} ===")
    event_comments = comments.get(str(event_id), {})
    for stream, comment_list in event_comments.items():
        print(f"{stream}: {len(comment_list)}件")
        if comment_list:
            print(f"  例: {comment_list[0][:100]}")  # 最初の100文字
```

---

### 5. コードのクリーンアップ（時間があれば）

#### デバッグ出力の削除
```python
# event_comparison.pyのDEBUG_VERBOSEをFalseに固定
DEBUG_VERBOSE = False  # 既に設定済み
```

#### 不要なコメントの削除
- 古いコメントアウトされたコードを削除
- デバッグ用print文の整理

#### ドキュメント統合
- README.mdの更新
- 各種.mdファイルの整合性確認

---

### 6. リポジトリへのコミット

**タスク：** 変更をgitにコミット

```bash
cd "g:\マイドライブ\大学\4年\ゼミ\watching_style_analysis"
git status
git add event_comparison.py
git add RUN_COMMANDS.md
git add SOLUTION_SUMMARY.md
git add NEXT_ACTIONS.md
git commit -m "Fix: Implement embedding-based event matching for multilingual streams

- Change matching priority: embedding similarity > Jaccard
- Update default parameters: embedding-match-th=0.65, word-match-th=0.05
- Add DEBUG_VERBOSE flag for clean production output
- Update documentation for game4 dataset
- Successfully matched 126/1980 event pairs (was 0 before)"

git push origin main
```

---

## 📊 成功の判断基準

### 最小限の成功条件（学会発表可能）
- [x] matched_event_presence.pngが生成される
- [x] 類似イベントが10件以上マッチする
- [x] 絵文字タイムラインが正常に表示される
- [ ] トピックラベルが意味のある内容
- [ ] 定量データ（CSV）が存在する

### 理想的な成功条件
- [ ] 類似イベントが30-80件マッチする
- [ ] 平均類似度が0.4-0.6の範囲
- [ ] 各配信者からバランスよくイベントが抽出される
- [ ] matched_event_presence.pngが直感的に理解できる
- [ ] 具体的なコメント事例が興味深い

---

## 🚨 想定されるトラブルと対処法

### トラブル1: メモリ不足エラー
**症状：** MemoryError, プロセスが停止

**対処法：**
```bash
# パラメータを減らす
--time-bins 50 \     # 100 → 50
--n-events 3 \       # 5 → 3
--focus-top 5        # 10 → 5
```

### トラブル2: 処理時間が長すぎる（>60分）
**症状：** 長時間経過しても完了しない

**対処法：**
```bash
# Ctrl+C で中断
# より軽量なパラメータで再実行
--time-bins 50 \
--n-events 3
```

### トラブル3: マッチング数が0
**症状：** "No similar events matched"

**対処法：**
```bash
# 埋め込み閾値を下げる
--embedding-match-th 0.5 \
--time-match-th 25
```

### トラブル4: 図表が見づらい
**症状：** ラベルが重なる、色が不明瞭

**対処法：**
1. `--top-matched 5`で表示数を制限（既にデフォルト）
2. コード内のfigsize, fontsize調整
3. カラーマップ変更（viridis → plasma）

---

## 📝 記録すべき情報

### 実行ログ
```
実行日時: 2025/11/06
データセット: data/football/game4 (4ファイル)
パラメータ:
  - time-bins: 100
  - n-events: 5
  - focus-top: 10
  - embedding-match-th: 0.65
  - word-match-th: 0.05
  - time-match-th: 15

結果:
  - 処理時間: XX分
  - 総イベント数: XX
  - マッチング数: XX
  - 平均類似度: XX
  - 生成ファイル数: XX
```

### 学会発表用メモ
- 最も印象的なマッチング事例
- 数値的な成果（マッチング率、類似度など）
- システムの強み（多言語対応、意味的類似度）
- 今後の展望

---

## 🎓 今後の研究方向性

### 短期（学会発表まで）
1. game4データの完全な分析
2. 図表のブラッシュアップ
3. 発表資料の作成
4. デモの準備

### 中期（学会発表後）
1. 他の試合データ（game1, game2, game3）での検証
2. パラメータの最適化研究
3. マッチング品質スコアの導入
4. キャッシュシステムの実装

### 長期（論文化）
1. 大規模データセットでの評価
2. 既存手法との比較実験
3. ユーザスタディ
4. 配信プラットフォームへの応用

---

## ✅ チェックリスト（今すぐ実行）

次にやるべきこと：

1. [ ] 実行完了を待つ（get_terminal_outputで確認）
2. [ ] output/フォルダの内容を確認
3. [ ] matched_event_presence.pngを目視確認
4. [ ] similar_event_comparison_results.csvを開いて統計確認
5. [ ] 結果が良好なら高精度版で再実行
6. [ ] 結果が不十分ならパラメータ調整して再実行
7. [ ] 満足したらgitにコミット
8. [ ] CONFERENCE_STRATEGY.mdに沿って次のステップへ

**現在の最優先タスク：** 実行完了を待ち、結果を確認すること
