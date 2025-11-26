# feature/latestからmainへのマージ手順

## 🔄 GitHubでプルリクエストを作成する方法（推奨）

### ステップ1: GitHubにアクセス
1. ブラウザで以下のURLにアクセス:
   ```
   https://github.com/takakuwa-mamada/watching_style_analysis
   ```

### ステップ2: プルリクエストを作成
1. 「Pull requests」タブをクリック
2. 「New pull request」ボタンをクリック
3. ベースブランチ: `main`
4. 比較ブランチ: `feature/latest`
5. 「Create pull request」をクリック

### ステップ3: プルリクエスト情報を入力
**タイトル**:
```
feat: Complete analysis execution and repository reorganization
```

**説明**:
```markdown
## 📊 変更概要

このPRは、リポジトリの大規模なクリーンアップと全分析の実行結果を含みます。

### ✅ 完了した作業

#### 1. リポジトリ整理
- 154個の不要な.mdファイル削除
- 新しい包括的なREADME.md作成（日本語）
- MITライセンス追加
- .gitignore作成（cache/を除外）

#### 2. 分析実行
- **BERTopic分析**: 263トピック抽出（42,556コメント）
- **時系列分析**: 4つの主要バースト検出
- **フットボール専用分析**: スポーツ交絡除去
- **統計分析**: Bootstrap CI、Cohen's d効果量計算

#### 3. 結果生成
- **50出力ファイル**生成（CSV 17件、PNG 32件、MD 1件）
- 統計的有意差検出: exclamation_rate (p=0.0272)

#### 4. ドキュメント
- ANALYSIS_EXECUTION_SUMMARY.md作成
- docs/INTEGRATED_ANALYSIS_REPORT.md保存

### 📁 変更ファイル数
- 追加: 53ファイル
- 削除: 154ファイル
- 変更: 3ファイル

### 🔬 主要な発見

**4つの文化的エンゲージメントスタイル**:
- 🇯🇵 日本: ソーシャル・カジュアル（持続型）
- 🇪🇸 スペイン: 伝統的チャント（前半集中型）
- 🇬🇧 イギリス: 分析的・論争重視（漸増型）
- 🇫🇷 フランス: 感情的・絵文字多用（序盤スパイク型）

### 📊 コミット履歴
1. `c873e5e` - docs: Clean up repository for open-source release
2. `6a7d3b6` - docs: Translate README.md to Japanese
3. `42f4602` - results: Complete all analysis executions
4. `0f18309` - docs: Add comprehensive analysis execution summary
5. `43fa8d7` - chore: Update LICENSE and README.md formatting

### ✅ レビューポイント
- [ ] README.mdの日本語内容が適切か
- [ ] 分析結果ファイル（output/）が正しく追加されているか
- [ ] 不要なファイルが適切に削除されているか
- [ ] LICENSEファイルが正しく追加されているか

### 📝 次のステップ
マージ後:
- ✅ 分析完了
- 📝 論文執筆フェーズへ
- 🎯 投稿目標: 2026年1月20日
```

### ステップ4: マージ
1. プルリクエストをレビュー
2. 「Merge pull request」をクリック
3. マージ方法を選択:
   - **Merge commit**: すべてのコミット履歴を保持（推奨）
   - Squash and merge: 1つのコミットにまとめる
   - Rebase and merge: リニアな履歴を保持
4. 「Confirm merge」をクリック

---

## 🖥️ コマンドラインでマージする方法（代替案）

### オプション1: GitHubでマージした後にローカルを更新

```bash
# mainブランチに切り替え
git checkout main

# リモートから最新を取得
git pull origin main

# feature/latestブランチを削除（オプション）
git branch -d feature/latest
```

### オプション2: ローカルでマージ（outputフォルダの問題がある場合は非推奨）

```bash
# mainブランチに切り替え
git checkout main

# feature/latestをマージ
git merge feature/latest

# リモートにプッシュ
git push origin main
```

---

## ⚠️ 注意事項

**現在の問題**:
- `output/`フォルダへのアクセス権限の問題
- ローカルでのブランチ切り替えが失敗する可能性

**推奨される方法**:
✅ **GitHubのウェブインターフェースでプルリクエストを作成してマージ**

この方法が最も安全で、コンフリクトの解決も簡単です。

---

## 📊 マージ後の確認

```bash
# mainブランチに切り替え
git checkout main

# 最新を取得
git pull origin main

# ログを確認
git log --oneline -10

# ファイル数を確認
ls output -Recurse | Measure-Object
```

---

**作成日時**: 2025年11月23日 21:10  
**ブランチ**: feature/latest → main  
**ステータス**: プルリクエスト作成待ち
