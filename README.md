# Watching Style Analysis: Cross-Cultural Live Stream Chat Study

![Progress](https://img.shields.io/badge/Progress-80%25-brightgreen)
![Status](https://img.shields.io/badge/Status-Active-success)
![Deadline](https://img.shields.io/badge/Deadline-Jan%2020%2C%202026-blue)

**研究テーマ**: ライブ配信チャットの視聴スタイル国際比較  
**対象**: El Clásico (Real Madrid vs FC Barcelona) 9配信、4か国  
**進捗**: 80% (データ分析完了、論文執筆中)  
**提出締切**: 2026年1月20日

---

## 📊 プロジェクト概要

本研究は、ライブストリーミング視聴中のチャットコメントを分析し、**文化による視聴スタイルの違い**を定量化します。スペイン、日本、イギリス、フランスの4か国でEl Clásico配信のチャットを収集し、5軸で比較しました。

### 🎯 研究目的
1. **感情表現の文化差**: 絵文字、感嘆符、笑い表現の使用頻度
2. **エンゲージメントパターン**: CPM（分あたりコメント数）、バースト特性
3. **文化的距離**: 国間の類似度、階層的クラスタリング

### 🔬 主要な発見
- **スポーツ交絡の発見**: Baseball配信はFootball配信の**2倍のCPM** → Football限定分析で解決
- **感嘆符率**: 統計的有意差 (p=0.0272)、日本が極端に低い
- **絵文字率**: スペインvs日本で**37倍の差** (Cohen's d=8.765, Huge effect)
- **笑い表現**: 日本の"w"文化がユニーク (0.046 vs 0.008-0.024)

---

## 📁 フォルダ構成

```
watching_style_analysis/
├── scripts/                    # 🔧 現在使用中の分析スクリプト
│   ├── analyze_football_only.py              # Football限定分析(交絡除去)
│   ├── improve_statistical_analysis_football_only.py  # 統計再計算
│   ├── create_sport_confounding_comparison.py  # Mixed vs Football比較
│   ├── select_paper_figures.py                # 論文用図の選定
│   ├── event_comparison.py                    # メイン分析スクリプト
│   ├── analyze_emotional_expression.py        # 感情表現分析
│   ├── analyze_engagement_patterns.py         # エンゲージメント分析
│   ├── analyze_cultural_similarity.py         # 文化的類似度分析
│   ├── generate_comprehensive_report.py       # 総合レポート生成
│   ├── improve_statistical_analysis.py        # Mixed版統計分析
│   └── create_paper_figures.py                # 図表生成
│
├── docs/                       # 📝 論文関連ドキュメント
│   ├── PAPER_SUBMISSION_SCHEDULE.md           # 65日スケジュール
│   ├── RESULTS_SECTION_4_1_DRAFT.md           # Results Section初稿
│   ├── 80_PERCENT_ACHIEVEMENT_REPORT.md       # 80%達成レポート
│   ├── SPORT_CONFOUNDING_ANALYSIS_REPORT.md   # 交絡分析レポート
│   ├── FIGURE_SELECTION_REPORT.md             # 図選定レポート
│   ├── CONFERENCE_STRATEGY.md                 # 学会戦略
│   ├── FINAL_ACADEMIC_REPORT.md               # 総合アカデミックレポート
│   ├── NEW_FEATURES_SUMMARY.md                # 新機能サマリー
│   ├── FINAL_RESULTS_REPORT.md                # 最終結果レポート
│   ├── FINAL_ANALYSIS.md                      # 最終分析
│   ├── FINAL_SUMMARY.md                       # 総括
│   └── FIGURE_EXPLANATIONS.md                 # 図の説明
│
├── output/                     # 📊 分析結果・図表
│   ├── football_only_analysis/                # Football限定分析結果
│   ├── football_only_statistical_analysis/    # Football統計分析(16図+CSV)
│   ├── sport_confounding_comparison/          # 交絡比較図(4枚)
│   ├── FIGURE_SELECTION_REPORT.md             # 図選定レポート
│   ├── figure_selection.json                  # 図選定データ
│   └── (その他31枚以上の図表)
│
├── data/                       # 📥 入力データ (チャットログ)
│
├── utils/                      # 🛠️ ユーティリティ
│   ├── chat_sort.py                           # チャット整理
│   ├── topic.py                               # トピック分析
│   ├── simple_topic_comparison.py             # 簡易比較
│   ├── twitch_chat_csv.py                     # Twitchチャット処理
│   └── youtube_chat_csv.py                    # YouTubeチャット処理
│
├── legacy/                     # 📦 旧バージョン・過去のレポート
│   └── (54+ files: 古い分析スクリプト、プラン、レポート)
│
├── archived/                   # 🗄️ バックアップ・診断ファイル
│   └── (12+ files: バックアップ、診断、整理スクリプト)
│
├── README.md                   # このファイル
└── requirements.txt            # Python依存パッケージ
```

---

## 🚀 使い方

### 1. 環境構築
```bash
# Python 3.8以上推奨
pip install -r requirements.txt
```

### 2. メイン分析の実行
```bash
# Football-Only分析 (推奨: 交絡除去済み)
python scripts/analyze_football_only.py

# 統計分析 (Bootstrap CI, Welch's ANOVA, Cohen's d)
python scripts/improve_statistical_analysis_football_only.py

# スポーツ交絡の比較図作成
python scripts/create_sport_confounding_comparison.py

# 論文用図の選定
python scripts/select_paper_figures.py
```

### 3. 個別分析
```bash
# 感情表現分析
python scripts/analyze_emotional_expression.py

# エンゲージメント分析
python scripts/analyze_engagement_patterns.py

# 文化的類似度分析
python scripts/analyze_cultural_similarity.py
```

---

## 📈 分析手法

### データセット
- **イベント**: El Clásico (Real Madrid vs FC Barcelona)
- **配信数**: 9配信 (Spain: 2, Japan: 2, UK: 4, France: 1)
- **総コメント数**: 42,556
- **期間**: 2020-2023年

### 5軸分析
1. **Emoji Rate** (emojis/comment): 絵文字使用頻度
2. **Exclamation Rate** (!!/comment): 感嘆符使用頻度
3. **Laugh Rate** (w, lol, haha/comment): 笑い表現頻度
4. **Comment Length** (characters): コメント文字数
5. **CPM** (Comments Per Minute): エンゲージメント強度

### 統計手法
- **Bootstrap 95% CI** (10,000 resamples): 小サンプルでも頑健
- **Welch's ANOVA**: 不等分散対応の分散分析
- **Cohen's d**: 効果量（実質的差の大きさ）
- **階層的クラスタリング**: 文化的距離の可視化

---

## 📊 主要結果

### Mixed版 vs Football-Only版の比較

| メトリクス | Mixed版 | Football-Only | 変化 | 解釈 |
|-----------|---------|---------------|------|------|
| **Japan CPM** | 38.0 | 19.1 | **-50%** | Baseball混在が数値を押し上げていた |
| **Emoji rate (d)** | 5.566 | **8.765** | +57% | 真の文化差はより大きかった |
| **Exclamation p** | 0.0004 | **0.0272** | 依然有意 | 文化差はスポーツに依存しない |

### 統計的有意性 (Football-Only)

| メトリクス | Welch's F | p値 | 判定 |
|-----------|-----------|-----|------|
| Emoji rate | 2.771 | 0.1504 | n.s. |
| **Exclamation rate** | **7.443** | **0.0272** | **✅ 有意!** |
| Laugh rate | 5.515 | 0.0532 | marginally |
| Comment length | 2.926 | 0.1378 | n.s. |
| CPM | 0.892 | 0.483 | n.s. |

### 効果量 (Cohen's d) - 主要ペア

**Spain vs Japan**:
- Emoji rate: **d=8.765** (Huge effect)
- Exclamation rate: **d=2.847** (Large effect)
- 文化差が極めて大きい

**Japan vs UK**:
- Exclamation rate: **d=-4.183** (Large effect)
- Laugh rate: **d=6.136** (Large effect)
- Comment length: **d=-2.135** (Large effect)

---

## 🎓 論文執筆進捗

### 完成度: 80% (2025年11月16日現在)

#### ✅ 完了
- データ収集・前処理
- 5軸すべての定量化
- スポーツ交絡の発見と除去
- Football-Only分析の完成
- 統計分析 (Bootstrap CI, ANOVA, Cohen's d)
- 47枚の図表生成
- 論文用図6-8枚の選定
- Results Section 4.1 初稿 (850語)

#### 🔄 進行中
- Results Section 4.2-4.4 (Emotional Expression, Engagement, Cultural Distance)

#### ⏳ 未着手
- Methods Section
- Introduction & Related Work
- Discussion
- Abstract

### 提出スケジュール
- **2025年11月17日**: 85% (Results完成)
- **2025年11月19日**: 90% (Methods完成)
- **2025年12月1日**: 95% (Introduction + Discussion)
- **2025年12月14日**: 100% (全体完成)
- **2026年1月20日**: **論文提出!** 🎉

---

## 🔬 技術スタック

- **Python 3.8+**
- **pandas, numpy**: データ処理
- **scipy, scikit-learn**: 統計分析、機械学習
- **matplotlib, seaborn**: 可視化
- **Bootstrap法**: 信頼区間推定
- **Welch's ANOVA**: 不等分散対応ANOVA

---

## 📚 主要ドキュメント

| ファイル | 内容 | 語数/行数 |
|---------|------|----------|
| [80_PERCENT_ACHIEVEMENT_REPORT.md](docs/80_PERCENT_ACHIEVEMENT_REPORT.md) | 80%達成報告 | 5,000+語 |
| [SPORT_CONFOUNDING_ANALYSIS_REPORT.md](docs/SPORT_CONFOUNDING_ANALYSIS_REPORT.md) | スポーツ交絡分析 | 400+行 |
| [RESULTS_SECTION_4_1_DRAFT.md](docs/RESULTS_SECTION_4_1_DRAFT.md) | Results初稿 | 850語 |
| [FIGURE_SELECTION_REPORT.md](docs/FIGURE_SELECTION_REPORT.md) | 図選定レポート | - |
| [PAPER_SUBMISSION_SCHEDULE.md](docs/PAPER_SUBMISSION_SCHEDULE.md) | 65日スケジュール | 1,200+行 |

---

## 🌟 主要な貢献

1. **スポーツ交絡の発見**: Baseball vs Footballで2×のCPM差 → 学術的厳密性向上
2. **Football-Only分析**: 純粋な文化差の抽出 → 妥当性向上
3. **Bootstrap法の適用**: 小サンプル(n=1, n=2)でも信頼区間推定 → 現代的統計手法
4. **効果量の報告**: p値だけでなくCohen's d → 実質的差の明確化
5. **5軸包括分析**: 感情・エンゲージメント・テキスト特性を統合

---

## 📧 連絡先

**研究者**: [あなたの名前]  
**所属**: [大学名]  
**Email**: [メールアドレス]

---

## 📜 ライセンス

[ライセンス情報を追加]

---

## 🙏 謝辞

El Clásico配信のチャット参加者の皆様、データ収集にご協力いただいた全ての方々に感謝いたします。

---

**Last Updated**: 2025年11月16日  
**Version**: 0.8.0 (80% Complete)