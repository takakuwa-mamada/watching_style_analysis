# 🚀 実行可能スクリプト一覧

このリポジトリで実行できる分析スクリプトの完全ガイドです。

---

## 📂 scripts/ フォルダ (メイン分析)

### 🏆 **推奨実行順序 (Football-Only分析)**

#### 1️⃣ **Football-Only分析** (交絡除去版)
```bash
python scripts/analyze_football_only.py
```
**機能**: 
- El Clásico限定の9配信を分析 (Spain: 2, Japan: 2, UK: 4, France: 1)
- スポーツ交絡を除去した純粋な文化比較
- 5軸メトリクス (Emoji, Exclamation, Laugh, Length, CPM) を計算

**生成物**:
- `output/football_only_analysis/football_only_results.csv`
- `output/football_only_analysis/emoji_rate_football_only.png`
- `output/football_only_analysis/multi_metric_comparison_football_only.png` ⭐
- `output/football_only_analysis/cultural_profiles_heatmap_football_only.png`

**実行時間**: 約30-60秒

---

#### 2️⃣ **統計分析 (Football-Only)** 
```bash
python scripts/improve_statistical_analysis_football_only.py
```
**機能**:
- Bootstrap 95% CI (10,000 resamples)
- Welch's ANOVA (不等分散対応)
- Cohen's d 効果量 (全ペア)
- 16枚の高品質図表生成

**生成物**:
- `output/football_only_statistical_analysis/` (33ファイル)
  - Bootstrap CI図: 8枚
  - 効果量ヒートマップ: 8枚
  - CSV統計テーブル: 16枚
  - `FOOTBALL_ONLY_STATISTICAL_REPORT.md`

**実行時間**: 約30-45秒

---

#### 3️⃣ **スポーツ交絡の比較図**
```bash
python scripts/create_sport_confounding_comparison.py
```
**機能**:
- Mixed版 vs Football-Only版の比較
- Baseball効果の可視化 (2×CPM差)
- 文化差の安定性確認

**生成物**:
- `output/sport_confounding_comparison/sport_confounding_cpm_comparison.png` ⭐
- `output/sport_confounding_comparison/sport_confounding_emoji_comparison.png`
- `output/sport_confounding_comparison/sport_confounding_effect_sizes.png`
- `output/sport_confounding_comparison/sport_confounding_summary_table.png`

**実行時間**: 約20-30秒

---

#### 4️⃣ **論文用図の選定**
```bash
python scripts/select_paper_figures.py
```
**機能**:
- 47枚の図から論文用6-8枚を選定
- 統計的有意性・効果量でスコアリング
- Main Figure / Supplementary を分類

**生成物**:
- `output/FIGURE_SELECTION_REPORT.md`
- `output/figure_selection.json`

**実行時間**: 数秒

---

### 📊 **個別分析スクリプト**

#### 5️⃣ **感情表現分析**
```bash
python scripts/analyze_emotional_expression.py
```
**機能**:
- Emoji rate (絵文字使用頻度)
- Exclamation rate (感嘆符使用頻度)
- Laugh rate (笑い表現頻度)
- 国別・時系列分析

**対象**: Mixed版データ (12配信、6か国)

---

#### 6️⃣ **エンゲージメント分析**
```bash
python scripts/analyze_engagement_patterns.py
```
**機能**:
- CPM (Comments Per Minute)
- Burst分析 (頻度・強度・持続時間)
- ピーク検出
- 時間的ダイナミクス

**対象**: Mixed版データ

---

#### 7️⃣ **文化的類似度分析**
```bash
python scripts/analyze_cultural_similarity.py
```
**機能**:
- 階層的クラスタリング
- 国間距離行列
- デンドログラム生成
- 文化グループの特定

**対象**: Mixed版データ

---

#### 8️⃣ **包括的レポート生成**
```bash
python scripts/generate_comprehensive_report.py
```
**機能**:
- 全分析の統合レポート
- Markdownフォーマット
- 表・図へのリンク
- 論文用サマリー

---

#### 9️⃣ **統計分析 (Mixed版)**
```bash
python scripts/improve_statistical_analysis.py
```
**機能**:
- Mixed版 (12配信、6か国) の統計分析
- Bootstrap CI, Welch's ANOVA, Cohen's d
- 31枚の図表生成

**注意**: Football-Only版を推奨 (交絡除去済み)

---

#### 🔟 **論文用図作成**
```bash
python scripts/create_paper_figures.py
```
**機能**:
- 論文投稿用の高解像度図
- フォーマット調整
- キャプション生成

---

#### 1️⃣1️⃣ **イベント比較 (メインスクリプト)**
```bash
python scripts/event_comparison.py
```
**機能**:
- 最も包括的な分析スクリプト
- 5軸すべてを実行
- Event-to-Event類似度
- 多数の図表を生成

**注意**: 実行時間が長い (数分)

---

## 🛠️ utils/ フォルダ (ユーティリティ)

### データ処理ツール

#### **YouTubeチャット処理**
```bash
python utils/youtube_chat_csv.py
```
**機能**: YouTubeライブチャットデータの前処理

---

#### **Twitchチャット処理**
```bash
python utils/twitch_chat_csv.py
```
**機能**: Twitchライブチャットデータの前処理

---

#### **チャット整理**
```bash
python utils/chat_sort.py
```
**機能**: チャットログの整理・クリーニング

---

#### **トピック分析**
```bash
python utils/topic.py
```
**機能**: LDAトピックモデリング

---

#### **簡易トピック比較**
```bash
python utils/simple_topic_comparison.py
```
**機能**: トピック間の簡易比較

---

## 📋 実行環境

### 必要なパッケージ
```bash
pip install -r requirements.txt
```

### 主要パッケージ
- `pandas` - データ処理
- `numpy` - 数値計算
- `scipy` - 統計分析
- `matplotlib` - 可視化
- `seaborn` - 統計的可視化
- `scikit-learn` - 機械学習

---

## 🎯 推奨ワークフロー

### 🏆 **論文用の完全分析 (Football-Only推奨)**

```bash
# Step 1: Football-Only分析 (交絡除去)
python scripts/analyze_football_only.py

# Step 2: 統計分析 (Bootstrap CI, ANOVA, Cohen's d)
python scripts/improve_statistical_analysis_football_only.py

# Step 3: スポーツ交絡の可視化
python scripts/create_sport_confounding_comparison.py

# Step 4: 論文用図の選定
python scripts/select_paper_figures.py
```

**所要時間**: 約2-3分  
**生成図表**: 31枚以上  
**統計**: Bootstrap CI, Welch's ANOVA, Cohen's d

---

### 📊 **Mixed版の参考分析 (Supplementary用)**

```bash
# Step 1: 個別分析
python scripts/analyze_emotional_expression.py
python scripts/analyze_engagement_patterns.py
python scripts/analyze_cultural_similarity.py

# Step 2: 統計分析 (Mixed版)
python scripts/improve_statistical_analysis.py

# Step 3: 包括的レポート
python scripts/generate_comprehensive_report.py
```

**所要時間**: 約3-5分  
**用途**: Supplementary Material

---

## ⚠️ 実行時の注意点

### データの存在確認
```bash
# data/ フォルダにチャットデータがあることを確認
ls data/
```

### 出力フォルダ
- 実行すると自動的に `output/` 配下に結果が保存されます
- 既存ファイルは上書きされます

### メモリ使用量
- 大規模データ分析: 2-4GB RAM推奨
- 通常分析: 1-2GB RAM で十分

### エラーハンドリング
- データが見つからない場合: `FileNotFoundError`
- メモリ不足: `MemoryError`
- パッケージ不足: `ModuleNotFoundError` → `pip install -r requirements.txt`

---

## 📊 生成される主要ファイル

### Football-Only分析
```
output/
├── football_only_analysis/
│   ├── football_only_results.csv              # 数値データ
│   ├── emoji_rate_football_only.png           # Emoji比較
│   ├── multi_metric_comparison_football_only.png  # ⭐ 5軸総合比較
│   └── cultural_profiles_heatmap_football_only.png  # クラスタリング
│
├── football_only_statistical_analysis/
│   ├── *_bootstrap_ci.png (8枚)               # Bootstrap CI
│   ├── *_effect_sizes_heatmap.png (8枚)       # Cohen's d
│   ├── *_bootstrap_ci.csv (8枚)               # 数値データ
│   ├── *_effect_sizes.csv (8枚)               # 効果量データ
│   └── FOOTBALL_ONLY_STATISTICAL_REPORT.md    # 統計レポート
│
└── sport_confounding_comparison/
    ├── sport_confounding_cpm_comparison.png   # ⭐ CPM比較
    ├── sport_confounding_emoji_comparison.png # Emoji安定性
    ├── sport_confounding_effect_sizes.png     # 効果量変化
    └── sport_confounding_summary_table.png    # 包括的サマリー
```

---

## 🎓 論文執筆用の重要ファイル

### Main Figures (6-8枚推奨)
1. `multi_metric_comparison_football_only.png` - Overview
2. `exclamation_rate_bootstrap_ci.png` - 統計的有意差 (p<0.05)
3. `emoji_rate_bootstrap_ci.png` - 最大効果量 (d=8.765)
4. `mean_cpm_bootstrap_ci.png` - エンゲージメント
5. `cultural_profiles_heatmap_football_only.png` - クラスタリング
6. `exclamation_rate_effect_sizes_heatmap.png` - 効果量

### Supplementary Figures
- `sport_confounding_cpm_comparison.png` - スポーツ交絡証明
- `sport_confounding_summary_table.png` - 包括的サマリー
- その他のBootstrap CI図・効果量図

---

## 💡 ヒント

### 並列実行
```bash
# 個別分析は独立しているので並列実行可能
python scripts/analyze_emotional_expression.py &
python scripts/analyze_engagement_patterns.py &
python scripts/analyze_cultural_similarity.py &
wait
```

### 特定の図だけ再生成
- スクリプトを編集してコメントアウト
- 必要な部分だけ実行

### デバッグモード
- スクリプト内の `print()` 文でデバッグ情報を確認
- エラー時は `-v` オプション (将来実装予定)

---

## 📞 サポート

問題が発生した場合:
1. `requirements.txt` の再インストール
2. データパスの確認
3. Python バージョン確認 (3.8以上推奨)
4. メモリ使用量の確認

---

**最終更新**: 2025年11月16日  
**リポジトリ進捗**: 80% Complete  
**推奨実行**: Football-Only分析 (交絡除去済み)
