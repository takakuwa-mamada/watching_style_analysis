import pandas as pd

df = pd.read_csv('output/event_to_event_pairs.csv')

print("="*60)
print("現在の結果サマリー")
print("="*60)
print(f"総ペア数: {len(df)}")
print(f"平均類似度: {df['combined_score'].mean():.3f}")
print(f"最高類似度: {df['combined_score'].max():.3f}")
print(f"topic_jaccard > 0: {(df['topic_jaccard'] > 0).sum()} ペア")
print(f"topic_jaccard = 1.0: {(df['topic_jaccard'] == 1.0).sum()} ペア")
print("="*60)

# Top 3表示
print("\nTop 3 類似ペア:")
top3 = df.nlargest(3, 'combined_score')
for i, row in top3.iterrows():
    print(f"\n{i+1}. Event {row['event_A_id']} ↔ {row['event_B_id']}")
    print(f"   類似度: {row['combined_score']:.3f}")
    print(f"   topic_jaccard: {row['topic_jaccard']:.3f}")
