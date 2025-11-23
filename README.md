# SNS上のスポーツファンエンゲージメントの異文化分析

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Research](https://img.shields.io/badge/Status-Research%20Complete-success)](https://github.com/takakuwa-mamada/watching_style_analysis)

自然言語処理とBERTopicモデリングを用いて、ライブ配信プラットフォームにおけるスポーツファンのエンゲージメントスタイルの異文化間差異を分析する包括的な研究プロジェクトです。

## 📊 研究概要

本プロジェクトでは、エル・クラシコ（レアル・マドリード vs バルセロナ）の試合中に**4カ国**（スペイン、日本、イギリス、フランス）の**9つのライブ配信**から収集した**42,556件の多言語コメント**を分析し、オンラインスポーツ観戦における独特な文化的エンゲージメントパターンを特定しました。

### 主要な発見

**4つの異なる文化的エンゲージメントスタイル**を特定しました：

- 🇯🇵 **日本**: ソーシャル・カジュアルスタイル（挨拶トピックに32.95%、持続的なエンゲージメント）
- 🇪🇸 **スペイン**: 伝統的チャントスタイル（チームチャントに18.28%、前半重視）
- 🇬🇧 **イギリス**: 分析的・論争重視スタイル（ペナルティ/オフサイド議論で最高値）
- 🇫🇷 **フランス**: 感情的・絵文字多用スタイル（絵文字反応10.99%、序盤スパイクパターン）

## 🏗️ プロジェクト構造

```
watching_style_analysis/
├── README.md                 # このファイル
├── LICENSE                   # MITライセンス
├── requirements.txt          # Python依存パッケージ
├── .gitignore               # Git除外ルール
│
├── data/                    # 生データ（リポジトリには含まれていません）
│   ├── chat/               # ライブ配信チャットデータ
│   └── football/           # サッカー専用データセット
│
├── scripts/                # 分析スクリプト
│   ├── analyze_topics_bertopic_football_only.py     # BERTopicトピック抽出
│   ├── analyze_temporal_patterns_football_only.py   # 時系列バースト検出
│   ├── analyze_translation_impact.py                # 翻訳分析
│   └── event_comparison.py                          # イベント比較
│
├── output/                 # 分析結果
│   ├── bertopic_analysis/  # BERTopic結果（263トピック）
│   │   ├── topic_details.csv
│   │   ├── country_topic_distribution.csv
│   │   └── *.png           # 可視化ファイル
│   │
│   └── temporal_analysis/  # 時系列パターン結果
│       ├── burst_details.csv
│       ├── emotion_timeline.csv
│       └── *.png           # 可視化ファイル
│
├── docs/                   # ドキュメント
│   └── INTEGRATED_ANALYSIS_REPORT.md  # 包括的な分析レポート
│
├── utils/                  # ユーティリティモジュール
│   ├── noise_filter.py
│   └── translation_bridge.py
│
├── tests/                  # ユニットテスト
│   └── test_translation_bridge.py
│
├── archived/               # アーカイブされた実験スクリプト
└── legacy/                 # レガシーコード（参考用）
```

## 🚀 クイックスタート

### 必要環境

- Python 3.8以上
- 8GB以上のRAM（BERTopic分析用）
- GPU（オプション、埋め込み生成を高速化）

### インストール

```bash
# リポジトリをクローン
git clone https://github.com/takakuwa-mamada/watching_style_analysis.git
cd watching_style_analysis

# 依存パッケージをインストール
pip install -r requirements.txt
```

### 分析の実行

#### 1. BERTopic分析（トピック抽出）

```bash
python scripts/analyze_topics_bertopic_football_only.py
```

**出力ファイル**: 
- `output/bertopic_analysis/topic_details.csv` - キーワード付き263トピック
- `output/bertopic_analysis/country_topic_distribution.csv` - 国×トピック行列
- 可視化ファイル（.png）

**予想実行時間**: 約15分（CPU）、約5分（GPU）

#### 2. 時系列パターン分析

```bash
python scripts/analyze_temporal_patterns_football_only.py
```

**出力ファイル**:
- `output/temporal_analysis/burst_details.csv` - 4つの主要なエンゲージメントバースト
- `output/temporal_analysis/emotion_timeline.csv` - 経時的な感情マーカー
- 可視化ファイル（.png）

**予想実行時間**: 約2〜3分

## 📈 主要な結果

### トピック分析（BERTopic）

- 多言語コメントから**263トピック**を抽出
- **74.9%のカバレッジ**（31,892/42,556コメント）
- **上位5トピック**が全コメントの32.8%を占める

**国別トピック分布:**

| トピックカテゴリ | 上位国 | % | キーワード例 |
|----------------|--------|---|--------------|
| ソーシャル/カジュアル | 日本 | 32.95% | "こんばんは"、挨拶 |
| チームチャント | スペイン | 18.28% | "HALA MADRID"、"Visca Barça" |
| 絵文字リアクション | フランス | 10.99% | 😜、💖、🔥 |
| ペナルティ議論 | イギリス | 3.73% | "clear pen"、"offside"、"robbed" |
| 選手分析 | イギリス | 3.69% | "Lamine"、"age 17"、"too young" |

### 時系列分析

**4つの主要エンゲージメントバーストを検出:**

| バースト | 時間 | ピーク高 | サンプルコメント | 解釈 |
|---------|------|---------|-----------------|------|
| #1 | 19%（約80分） | 1,158 | "HALA MADRID"、"vamos" | ゴール/重要イベント |
| #2 | 24%（約101分） | 1,282 | "😜💖"、"madrid push hard" | 感情的反応 |
| #3 | 28%（約118分） | 1,257 | "Barcelona 💩"、"HALA MADRID" | チーム批判 |
| **#4** | **31%（約131分）** | **1,363** ⭐ | "vuhuuuu"、"🤍🔥🔥" | **試合終了/勝利** |

### 文化的時系列パターン

| 国 | パターンタイプ | ピーク期 | 特徴 |
|----|--------------|---------|------|
| **フランス** | 序盤スパイク | 0-9% | 序盤に集中、その後離脱 |
| **日本** | 持続型 | 10-19% | 最も一貫したエンゲージメント |
| **スペイン** | 前半集中 | 0-9% | プレーに集中、ハーフタイムで減少 |
| **イギリス** | 漸増型 | 4-9% | 試合全体を通じた分析的注目 |

## 🛠️ 使用技術

### コアライブラリ

- **BERTopic**（v0.16+）- トピックモデリング
- **sentence-transformers** - 多言語埋め込み
  - モデル: `paraphrase-multilingual-MiniLM-L12-v2`
- **UMAP** - 次元削減（384→5次元）
- **HDBSCAN** - クラスタリング（min_cluster_size=30）
- **pandas**、**numpy** - データ処理
- **matplotlib**、**seaborn** - 可視化
- **scipy** - 統計分析

### 分析パイプライン

```
生コメント（42,556件）
    ↓
前処理・フィルタリング
    ↓
埋め込み生成（sentence-transformers）
    ↓
次元削減（UMAP: 384→5次元）
    ↓
クラスタリング（HDBSCAN）
    ↓
トピック表現（c-TF-IDF）
    ↓
BERTopicトピック（263トピック）
    +
時系列分析（バースト検出、感情タイムライン）
    ↓
文化的パターン分析
```

## 📊 データセット説明

**ソース**: エル・クラシコ ライブ配信コメント  
**イベント**: レアル・マドリード vs FCバルセロナ  
**総コメント数**: 42,556件  
**言語**: スペイン語、英語、日本語、ヒンディー語/ウルドゥー語、フランス語

**国別分布:**
- **スペイン**: 9,715コメント（2配信）
- **日本**: 9,276コメント（2配信）
- **イギリス**: 19,651コメント（4配信）
- **フランス**: 3,914コメント（1配信）

**時間範囲**: 約7時間の録画時間

**データ形式**（CSV）:
```csv
timestamp,comment,country,stream_id
2024-10-26 21:00:05,HALA MADRID,Spain,Spain_1
2024-10-26 21:00:12,こんばんは,Japan,Japan_1
2024-10-26 21:00:18,Clear pen!,UK,UK_1
...
```

> **注意**: プライバシー上の考慮とプラットフォームの利用規約により、生データはこのリポジトリには含まれていません。研究協力やデータアクセスのリクエストについては、著者にお問い合わせください。

## 📖 ドキュメント

### メインドキュメント

- **[統合分析レポート](docs/INTEGRATED_ANALYSIS_REPORT.md)** 
  - 包括的な発見（6,500語以上）
  - 詳細なトピック解釈
  - 時系列パターン分析
  - 学術的意義
  - 統計概要

### 主要セクション

1. **第1部**: トピックベースの文化分析
   - 4つの異なる文化的スタイル
   - 上位20トピックの解釈
   - 国別パターン

2. **第2部**: 時系列パターン分析
   - 4つの主要エンゲージメントバースト
   - 感情タイムラインパターン
   - 国別時系列ヒートマップ

3. **第3部**: 統合的文化-時系列発見
   - スタイル-タイミング相関
   - ピーク時の文化的収束

4. **第4部**: 研究計画の達成度
   - すべての要件達成（100%）
   - 多言語トピック抽出の検証

5. **第5部**: 学術的意義
   - 理論的貢献
   - 方法論的革新
   - 引用機会

## 🔬 学術的文脈

### 理論的貢献

1. **文化的技術採用理論**
   - 文化的価値観がプラットフォームのアフォーダンスよりもデジタル行動を形成
   - 同じ技術→異なる使用パターン

2. **スポーツファンアイデンティティ理論**
   - スタジアム文化がオンラインに転送（スペインのチャント）
   - 新しいデジタルネイティブスタイルの出現（日本のソーシャル、フランスの絵文字）

3. **時間的エンゲージメント理論**
   - 文化的注意パターンの違い（忍耐型 vs 衝動型）
   - プラットフォーム設計は多様な時間的スタイルに対応すべき

### 方法論的貢献

1. **多言語トピックモデリング**
   - コードスイッチング環境にsentence-transformersを適用成功
   - 263トピックが5言語にわたる詳細な意味的差異を捉える

2. **統合的時間-トピック分析**
   - BERTopic（内容）+ バースト検出（タイミング）+ 感情タイムライン（感情）を組み合わせ
   - 文化的エンゲージメントの全体的な視点を提供

## 🧪 テスト

```bash
# ユニットテストを実行
python -m pytest tests/

# 特定のテストを実行
python -m pytest tests/test_translation_bridge.py -v
```

## 🤝 貢献

貢献を歓迎します！以下の手順に従ってください：

1. リポジトリをフォーク
2. フィーチャーブランチを作成（`git checkout -b feature/AmazingFeature`）
3. 変更をコミット（`git commit -m 'Add some AmazingFeature'`）
4. ブランチにプッシュ（`git push origin feature/AmazingFeature`）
5. プルリクエストを開く

### 開発ガイドライン

- PEP 8コードスタイルに従う
- すべての関数にdocstringを追加
- 該当する場合は型ヒントを含める
- 新機能のユニットテストを作成
- API変更のドキュメントを更新

## 📜 ライセンス

このプロジェクトはMITライセンスの下でライセンスされています - 詳細は[LICENSE](LICENSE)ファイルを参照してください。

## 👥 著者

- **Takakuwa Mamada** - *初期作成* - [takakuwa-mamada](https://github.com/takakuwa-mamada)

## 🙏 謝辞

- 公開コメントデータを提供してくれたYouTubeライブ配信ホスト
- OPUS-MT翻訳モデルのHelsinki-NLP
- 優れたトピックモデリングフレームワークを提供するBERTopicコミュニティ
- 多言語埋め込みモデルを提供するsentence-transformersチーム

## 📧 お問い合わせ

質問、共同研究のお問い合わせ、データアクセスのリクエストについて：

- **GitHub Issues**: [issueを作成](https://github.com/takakuwa-mamada/watching_style_analysis/issues)
- **GitHub**: [@takakuwa-mamada](https://github.com/takakuwa-mamada)
- **Email**: [GitHubプロフィール経由でお問い合わせ]

## 📚 引用

この研究を使用する場合は、以下のように引用してください：

```bibtex
@misc{mamada2024crosscultural,
  author = {Mamada, Takakuwa},
  title = {Cross-Cultural Sports Fan Engagement Analysis on SNS: 
           A BERTopic-Based Study of El Clásico Live Stream Comments},
  year = {2024},
  publisher = {GitHub},
  journal = {GitHub repository},
  howpublished = {\url{https://github.com/takakuwa-mamada/watching_style_analysis}},
  note = {Research in Progress}
}
```

## 🔮 今後の展望

### 短期計画
- [ ] 統計的有意性検定（カイ二乗検定、ANOVA）
- [ ] 論文執筆（結果セクション4.4-4.5）
- [ ] 学会投稿準備

### 長期的拡張
- [ ] 他のスポーツへの拡張（MLB、NBA、NFL）
- [ ] リアルタイムバースト検出システム
- [ ] より深い感情分析（皮肉、アイロニー検出）
- [ ] ユーザーインタラクションのネットワーク分析
- [ ] オフラインスタジアムエンゲージメントパターンとの比較
- [ ] 配信者の影響分析

## ⚠️ 制限事項と考慮事項

### データの制限
1. **単一試合**: 1つのエル・クラシコ試合に基づく分析（ハイステークスライバルリー）
2. **配信の交絡**: 各配信が1つの国を代表（国と配信者の効果を分離できない）
3. **言語プロキシ**: 配信言語が視聴者の国籍を近似すると仮定
4. **時間的整列**: 正確な試合イベントのタイムスタンプが利用不可

### 方法論的制限
1. **トピック粒度**: 263トピックは過度に細かい可能性（多くが50コメント未満）
2. **外れ値率**: HDBSCANによって25.1%のコメントが外れ値として分類
3. **コードスイッチング**: 混合言語トピック（例：トピック0）の解釈が困難

### 一般化可能性
- 以下の文脈に特定の結果：
  - サッカー（フットボール）文脈
  - ハイステークスライバルリー試合
  - 2020-2023年の期間
  - YouTube/Twitchプラットフォームの規範

## 📊 リポジトリ統計

- **分析したコメント総数**: 42,556件
- **抽出したトピック**: 263個
- **国**: 4カ国
- **配信**: 9配信
- **言語**: 5言語（スペイン語、英語、日本語、ヒンディー語/ウルドゥー語、フランス語）
- **コードファイル**: 15以上の分析スクリプト
- **出力可視化**: 13図（時系列8+トピック5）
- **ドキュメント**: 6,500語以上

---

**最終更新**: 2025年11月23日  
**プロジェクトステータス**: ✅ 分析完了 | 📝 論文執筆中  
**投稿目標**: 2026年1月20日

---

<p align="center">
  <i>本研究は、文化的価値観が同じデジタルプラットフォームでの人々のエンゲージメント方法を根本的に形成することを実証し、グローバルなライブ配信サービスにおける文化特有の設計考慮の実証的証拠を提供します。</i>
</p>
