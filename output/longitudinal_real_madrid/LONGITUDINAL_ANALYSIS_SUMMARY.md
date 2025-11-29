# 縦断的比較分析 - Longitudinal Comparison Report
**分析日時**: 2025年11月23日 22:35
**対象**: レアルマドリード関連3試合
---

## 📊 データ概要

### Real Madrid vs Barcelona
- 配信数: 1
- 総コメント数: 47,414
- 重要度: Ultra-High

### Real Sociedad vs Real Madrid
- 配信数: 1
- 総コメント数: 3,045
- 重要度: Medium

### PSG vs Inter Miami
- 配信数: 1
- 総コメント数: 16,453
- 重要度: Low

## 🎯 試合別エンゲージメント指標

| 試合 | CPM | コメント長 | 絵文字率(%) | エントロピー | バースト頻度 | CPM変動係数 |
|------|-----|-----------|------------|-------------|-------------|-------------|
| Real Madrid vs Barcelona | 25.1±5.3 | 32.0±11.9 | 29.9±36.8 | 9.90±0.78 | 0.132±0.064 | 0.59±0.19 |
| Real Sociedad vs Real Madrid | 39.0±38.4 | 30.3±3.2 | 8.3±3.6 | 8.95±0.81 | 0.128±0.038 | 0.52±0.05 |
| PSG vs Inter Miami | 60.1±8.0 | 40.9±4.8 | 13.7±4.6 | 9.34±0.80 | 0.134±0.016 | 0.61±0.14 |

## 📈 統計的検定結果

### cpm

- 検定: Kruskal-Wallis
- 統計量: 3.537
- p値: 0.1706
- 結果: ❌ 非有意

### avg_comment_length

- 検定: Kruskal-Wallis
- 統計量: 2.417
- p値: 0.2987
- 結果: ❌ 非有意

### emoji_rate

- 検定: Kruskal-Wallis
- 統計量: 2.562
- p値: 0.2778
- 結果: ❌ 非有意

### entropy

- 検定: Kruskal-Wallis
- 統計量: 2.737
- p値: 0.2545
- 結果: ❌ 非有意

### burst_frequency

- 検定: Kruskal-Wallis
- 統計量: 0.555
- p値: 0.7577
- 結果: ❌ 非有意

### cpm_cv

- 検定: Kruskal-Wallis
- 統計量: 0.375
- p値: 0.8290
- 結果: ❌ 非有意

## 👥 配信者の出現パターン

⚠️ 複数試合に出現する配信者なし
→ 試合間の直接比較には限界あり（配信者効果が混交）

## 🔍 主要な発見

### CPM（コメント密度）の変化

- **PSG vs Inter Miami** (Tier 4): 60.1 CPM
- **Real Sociedad vs Real Madrid** (Tier 3): 39.0 CPM
- **Real Madrid vs Barcelona** (Tier 1): 25.1 CPM

### 時系列パターンの特徴

- **PSG vs Inter Miami**: バースト頻度 0.134
- **Real Madrid vs Barcelona**: バースト頻度 0.132
- **Real Sociedad vs Real Madrid**: バースト頻度 0.128

## 🚀 今後の展開

1. **同一配信者での試合間比較**
   - 複数試合に出現する配信者に絞った分析
   - 配信者効果を制御した純粋な試合効果の抽出

2. **試合展開との対応**
   - 得点シーンとコメントバーストの対応分析
   - 試合の緊迫度とエンゲージメントの関係

3. **他チームとの比較**
   - レアルマドリードと他チームの縦断的パターン比較
   - チーム特性（攻撃的 vs 守備的）の影響

