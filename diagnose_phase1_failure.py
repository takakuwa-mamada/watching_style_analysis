"""
Phase 1失敗の詳細診断スクリプト
max_features=3000に増やしても改善しなかった原因を特定
"""

import pandas as pd
import numpy as np

# Phase 1結果を読み込み
df = pd.read_csv('output/event_to_event_pairs.csv')

print("=" * 70)
print("Phase 1 失敗診断レポート")
print("=" * 70)

print(f"\n総ペア数: {len(df)}")

# 各成分の統計
print("\n【各成分の統計】")
components = {
    'embedding_similarity': 'Embedding類似度',
    'topic_jaccard': 'Topic Jaccard',
    'lexical_similarity': 'Lexical類似度',
    'temporal_correlation': 'Temporal相関',
    'combined_score': '最終スコア'
}

for col, name in components.items():
    mean_val = df[col].mean()
    std_val = df[col].std()
    print(f"  {name:20s}: 平均={mean_val:.4f}, 標準偏差={std_val:.4f}")

# Topic分析（最重要）
print("\n【Topic Jaccard 分析】")
topic_zero = (df['topic_jaccard'] == 0).sum()
topic_positive = (df['topic_jaccard'] > 0).sum()
topic_perfect = (df['topic_jaccard'] == 1.0).sum()

print(f"  topic_jaccard = 0   : {topic_zero:2d} ペア ({topic_zero/len(df)*100:.1f}%)")
print(f"  topic_jaccard > 0   : {topic_positive:2d} ペア ({topic_positive/len(df)*100:.1f}%)")
print(f"  topic_jaccard = 1.0 : {topic_perfect:2d} ペア ({topic_perfect/len(df)*100:.1f}%)")

# Topic > 0のペアを詳細表示
print("\n【Topic Jaccard > 0 のペア詳細】")
topic_positive_pairs = df[df['topic_jaccard'] > 0].sort_values('topic_jaccard', ascending=False)
for idx, row in topic_positive_pairs.iterrows():
    print(f"  Event {row['event_A_id']:2.0f} ↔ {row['event_B_id']:2.0f}: "
          f"topic_jaccard={row['topic_jaccard']:.3f}, "
          f"combined={row['combined_score']:.3f}")

# Combined scoreの分布
print("\n【Combined Score 分布】")
low = (df['combined_score'] < 0.3).sum()
mid = ((df['combined_score'] >= 0.3) & (df['combined_score'] < 0.5)).sum()
high = (df['combined_score'] >= 0.5).sum()

print(f"  Low (<0.3)      : {low:2d} ペア ({low/len(df)*100:.1f}%)")
print(f"  Mid (0.3-0.5)   : {mid:2d} ペア ({mid/len(df)*100:.1f}%)")
print(f"  High (>=0.5)    : {high:2d} ペア ({high/len(df)*100:.1f}%)")

# Baseline比較（hard-coded）
print("\n【Baseline比較】")
baseline_avg = 0.237
baseline_topic_coverage = 17.9
current_avg = df['combined_score'].mean()
current_topic_coverage = (df['topic_jaccard'] > 0).sum() / len(df) * 100

print(f"  Combined Score平均: {baseline_avg:.3f} → {current_avg:.3f} ({current_avg-baseline_avg:+.3f})")
print(f"  Topic Coverage    : {baseline_topic_coverage:.1f}% → {current_topic_coverage:.1f}% ({current_topic_coverage-baseline_topic_coverage:+.1f}%)")

# 問題点の特定
print("\n【問題点の特定】")
print(f"  ❌ max_features=3000に増やしてもTopic coverageが改善せず")
print(f"  ❌ {topic_zero}/{len(df)} ペア ({topic_zero/len(df)*100:.1f}%) でトピックが全く一致していない")
print(f"  ❌ Combined scoreが改善していない（{current_avg:.3f} ≈ {baseline_avg:.3f}）")

# 原因の推測
print("\n【原因の推測】")
print("  1. min_df/max_df パラメータが厳しすぎる")
print("     → 小規模イベント（10-20コメント）でトピックが抽出できない")
print("     → 'After pruning, no terms remain' 警告が多数")
print("  2. max_features増加はEmbedding類似度に影響しない")
print("     → SentenceTransformerベースなのでTfidfVectorizerと独立")
print("  3. Topic重みが低い（現在の重み設定を確認する必要がある）")

print("\n【推奨される次のアクション】")
print("  優先度1: min_df/max_df を調整")
print("    現在: min_df=1, max_df=0.95")
print("    提案: min_df=1, max_df=1.0 または min_df=0")
print("  優先度2: Phase 2（重み最適化）を実行")
print("    Topic重みを45%に増やす")
print("  優先度3: N-gram抽出ロジックを見直す")
print("    小規模イベントに対応した閾値調整")

print("\n" + "=" * 70)
print("診断完了")
print("=" * 70)
