# 分析実行完了サマリー

**実行日時**: 2025年11月23日  
**ステータス**: ✅ すべての主要分析完了

## 📊 実行した分析

### 1. BERTopic分析（トピック抽出）
**スクリプト**: `scripts/analyze_topics_bertopic_football_only.py`  
**実行時間**: 約17分（埋め込み生成2分21秒 + UMAP 51秒 + HDBSCAN 13分）

**結果**:
- **263トピック**を抽出（外れ値を除く）
- **42,556コメント**を分析（4カ国、9配信）
- **カバレッジ**: 74.9%（31,892/42,556コメント）
- **外れ値**: 10,664コメント（25.1%）

**国別分布**:
- イギリス: 19,651コメント
- スペイン: 9,715コメント
- 日本: 9,276コメント
- フランス: 3,914コメント

**上位5トピック**:
1. Topic 0: 8,907コメント（混合言語：挨拶・社交）
2. Topic 1: 2,727コメント（"HALA MADRID"チャント）
3. Topic 2: 1,141コメント（絵文字リアクション）
4. Topic 3: 689コメント（選手議論）
5. Topic 4: 580コメント（ゴール反応）

**生成ファイル** (output/bertopic_analysis/):
- `topic_details.csv` - 全263トピックの詳細
- `country_topic_distribution.csv` - 国×トピック分布行列
- `country_topic_distribution.png` - 国別トピック可視化
- `topic_timeline.csv` - トピックの時系列推移
- `topic_timeline.png` - トピックタイムライン可視化

---

### 2. 時系列パターン分析（バースト検出）
**スクリプト**: `scripts/analyze_temporal_patterns_football_only.py`  
**実行時間**: 約2分

**結果**:
- **4つの主要バースト**を検出
- **時間範囲**: 0.0秒 〜 25,354.7秒（約7時間）
- **感情タイムライン**分析完了

**検出されたバースト**:
| バースト | 時間位置 | ピーク高 | 解釈 |
|---------|---------|---------|------|
| #1 | 19% | 1,158 | ゴール/重要イベント |
| #2 | 24% | 1,282 | 感情的反応 |
| #3 | 28% | 1,257 | チーム批判 |
| **#4** | **31%** | **1,363** | **試合終了/勝利** ⭐ |

**生成ファイル** (output/temporal_analysis/):
- `burst_details.csv` - 4バーストの詳細データ
- `burst_detection.png` - バースト検出可視化
- `emotion_timeline.csv` - 感情マーカーの時系列データ
- `emotion_timeline.png` - 感情タイムライン可視化
- `comment_density_overall.png` - 全体コメント密度
- `comment_density_by_country.png` - 国別コメント密度
- `country_temporal_heatmap.png` - 国別時系列ヒートマップ
- `country_temporal_patterns.csv` - 国別時系列パターンデータ

---

### 3. フットボール専用文化分析
**スクリプト**: `scripts/analyze_football_only.py`  
**実行時間**: 約1分

**結果**:
- スポーツ交絡を除去した純粋な文化差分析
- 9配信のみを対象（野球配信を除外）

**国別統計**:
| 国 | コメント数 | 絵文字率 | 平均文字数 | 平均CPM |
|----|-----------|---------|----------|---------|
| フランス | 3,914 | 0.894 | 36.9 | 25.8 |
| 日本 | 9,276 | 0.034 | 16.1 | 19.1 |
| スペイン | 9,715 | 1.261 | 38.7 | 27.2 |
| イギリス | 19,651 | 1.213 | 35.1 | 26.4 |

**生成ファイル** (output/football_only_analysis/):
- `football_only_results.csv` - 国別統計データ
- `emoji_rate_football_only.png` - 絵文字率比較
- `multi_metric_comparison_football_only.png` - 多指標比較
- `cultural_profiles_heatmap_football_only.png` - 文化プロファイルヒートマップ

---

### 4. 統計的分析（Bootstrap CI & 効果量）
**スクリプト**: `scripts/improve_statistical_analysis_football_only.py`  
**実行時間**: 約3分

**結果**:
- **Bootstrap 95%信頼区間**算出
- **Welch's ANOVA**実行（不等分散対応）
- **Cohen's d効果量**計算（ペアワイズ）

**有意差検出**:
- ✅ **exclamation_rate**: p=0.0272（有意差あり）
  - スペイン vs 日本: d=2.847（Large）
  - スペイン vs イギリス: d=1.973（Large）
  - 日本 vs イギリス: d=-4.183（Large）

**効果量（Large）**:
- emoji_rate: スペイン vs 日本（d=8.765）
- laugh_rate: 日本 vs イギリス（d=6.136）
- mean_length: 日本 vs イギリス（d=-2.135）

**生成ファイル** (output/football_only_statistical_analysis/):
- `FOOTBALL_ONLY_STATISTICAL_REPORT.md` - 統計レポート
- 8指標 × 2可視化（Bootstrap CI + 効果量ヒートマップ）= **16 PNG**
- 8指標 × 2データ（Bootstrap + 効果量）= **16 CSV**
- **合計32ファイル**

---

## 📁 生成されたファイル数

| フォルダ | ファイル数 | 内容 |
|---------|----------|------|
| `output/bertopic_analysis/` | 5 | トピック抽出結果 |
| `output/temporal_analysis/` | 8 | 時系列・バースト検出 |
| `output/football_only_analysis/` | 4 | 文化分析 |
| `output/football_only_statistical_analysis/` | 33 | 統計分析 |
| **合計** | **50** | **CSV + PNG + MD** |

---

## 🔬 主要な発見

### 文化的エンゲージメントスタイル（4類型）

1. **🇯🇵 日本: ソーシャル・カジュアルスタイル**
   - 特徴: 挨拶トピックに32.95%
   - パターン: 持続的エンゲージメント（10-19%ピーク）
   - 絵文字率: 0.034（最低）
   - 平均文字数: 16.1文字（最短）

2. **🇪🇸 スペイン: 伝統的チャントスタイル**
   - 特徴: チームチャントに18.28%
   - パターン: 前半集中（0-9%ピーク）
   - 絵文字率: 1.261
   - 感嘆符率: 0.104（有意に高い, p<0.05）

3. **🇬🇧 イギリス: 分析的・論争重視スタイル**
   - 特徴: ペナルティ/オフサイド議論で最高値
   - パターン: 漸増型（4-9%ピーク）
   - 絵文字率: 1.213
   - コメント数: 19,651（最多）

4. **🇫🇷 フランス: 感情的・絵文字多用スタイル**
   - 特徴: 絵文字反応10.99%
   - パターン: 序盤スパイク（0-9%集中、その後離脱）
   - 絵文字率: 0.894
   - 平均文字数: 36.9文字

### 時系列パターン

**4つの主要エンゲージメントバースト**:
- 試合全体を通じて4つのピークを検出
- 最大バーストは31%地点（試合終了時）で1,363コメント

**国別時間パターン**:
- フランス: 序盤型（早期離脱）
- 日本: 持続型（一貫したエンゲージメント）
- スペイン: 前半型（ハーフタイムで減少）
- イギリス: 漸増型（試合を通じて分析的注目）

---

## 🎯 次のステップ

### 短期（1週間以内）
- [ ] 統計レポートの精査（有意差の解釈）
- [ ] 論文用図表の選定（8-10図）
- [ ] Results Section 4.4-4.5の執筆

### 中期（2週間以内）
- [ ] Discussion Sectionの執筆
- [ ] 制限事項セクションの明確化
- [ ] 学術的貢献の整理

### 長期（1ヶ月以内）
- [ ] 論文全体の推敲
- [ ] 査読者向けQ&A準備
- [ ] 学会投稿（目標: 2026年1月20日）

---

## 📊 データ品質確認

✅ **データ完全性**:
- 全42,556コメント読み込み成功
- 欠損値なし
- タイムスタンプ正常

✅ **分析妥当性**:
- BERTopicカバレッジ74.9%（良好）
- 外れ値率25.1%（許容範囲）
- トピック数263（詳細な分析が可能）

✅ **統計的信頼性**:
- Bootstrap CI算出済み
- 効果量（Cohen's d）計算済み
- 小サンプルサイズ考慮（Welch's ANOVA使用）

---

## 🚀 Git操作履歴

```bash
# コミット: 42f4602
git add output/
git commit -m "results: Complete all analysis executions"
git push origin feature/latest
```

**プッシュサイズ**: 2.14 MB（42ファイル）  
**ブランチ**: feature/latest  
**リモート**: origin (GitHub)

---

## 💾 バックアップ推奨

重要ファイル:
- ✅ `output/bertopic_analysis/topic_details.csv`
- ✅ `output/temporal_analysis/burst_details.csv`
- ✅ `output/football_only_statistical_analysis/FOOTBALL_ONLY_STATISTICAL_REPORT.md`
- ✅ すべての可視化PNG（論文用図表候補）

---

## 📧 連絡事項

分析実行完了。すべての結果はGitHubにプッシュ済み。  
論文執筆の準備が整いました。

---

**作成日時**: 2025年11月23日 20:55  
**ステータス**: ✅ 分析フェーズ完了 → 論文執筆フェーズへ
