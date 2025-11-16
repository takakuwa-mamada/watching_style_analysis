import pandas as pd

# Load results
df = pd.read_csv(r'output\event_to_event_pairs.csv')

print('='*80)
print('Phase 2 Failure Diagnosis')
print('='*80)

# 1. Why did average go DOWN?
print('\n【1. Why Did Average Score Decrease?】')
print('Comparing OLD (40% topic) vs NEW (55% topic) formulas:\n')

# Calculate what scores WOULD have been with old weights
old_scores = []
new_scores = []

for idx, row in df.iterrows():
    # OLD: embedding 0.4, lexical 0.2, topic 0.4
    old_base = row['embedding_similarity'] * 0.40 + row['topic_jaccard'] * 0.40 + row['lexical_similarity'] * 0.20
    
    # NEW: embedding 0.3, lexical 0.15, topic 0.55
    new_base = row['embedding_similarity'] * 0.30 + row['topic_jaccard'] * 0.55 + row['lexical_similarity'] * 0.15
    
    old_scores.append(old_base)
    new_scores.append(new_base)

df['old_score'] = old_scores
df['new_score'] = new_scores
df['score_change'] = df['new_score'] - df['old_score']

print(f'Average OLD score (40% topic): {sum(old_scores)/len(old_scores):.3f}')
print(f'Average NEW score (55% topic): {sum(new_scores)/len(new_scores):.3f}')
print(f'Average change: {(sum(new_scores)/len(new_scores)) - (sum(old_scores)/len(old_scores)):.3f}')

# 2. Which pairs got worse?
print('\n【2. Pairs That Got WORSE (NEW < OLD)】')
worse = df[df['score_change'] < 0].sort_values('score_change')
print(f'Count: {len(worse)}/{len(df)} ({len(worse)/len(df)*100:.1f}%)\n')

for i, (idx, row) in enumerate(worse.head(10).iterrows()):
    print(f'{i+1}. Event {int(row["event_A_id"])} <-> {int(row["event_B_id"])}')
    print(f'   Embedding: {row["embedding_similarity"]:.3f}')
    print(f'   Topic: {row["topic_jaccard"]:.3f}')
    print(f'   Lexical: {row["lexical_similarity"]:.3f}')
    print(f'   OLD score: {row["old_score"]:.3f}')
    print(f'   NEW score: {row["new_score"]:.3f}')
    print(f'   Change: {row["score_change"]:.3f} ⬇️')
    print()

# 3. Which pairs got better?
print('【3. Pairs That Got BETTER (NEW > OLD)】')
better = df[df['score_change'] > 0].sort_values('score_change', ascending=False)
print(f'Count: {len(better)}/{len(df)} ({len(better)/len(df)*100:.1f}%)\n')

for i, (idx, row) in enumerate(better.head(10).iterrows()):
    print(f'{i+1}. Event {int(row["event_A_id"])} <-> {int(row["event_B_id"])}')
    print(f'   Embedding: {row["embedding_similarity"]:.3f}')
    print(f'   Topic: {row["topic_jaccard"]:.3f}')
    print(f'   Lexical: {row["lexical_similarity"]:.3f}')
    print(f'   OLD score: {row["old_score"]:.3f}')
    print(f'   NEW score: {row["new_score"]:.3f}')
    print(f'   Change: +{row["score_change"]:.3f} ⬆️')
    print()

# 4. Key insight
print('【4. Key Insight】')
print('\nThe problem:')
print(f'  - Pairs with topic_jaccard=0: {len(df[df["topic_jaccard"]==0])}/28 ({len(df[df["topic_jaccard"]==0])/28*100:.1f}%)')
print(f'  - Pairs with high embedding: {len(df[df["embedding_similarity"]>0.7])}/28')
print(f'  - Pairs with high topic: {len(df[df["topic_jaccard"]>0.5])}/28')

print('\nWhen you DECREASE embedding weight (40%->30%):')
print('  - High embedding pairs LOSE score')
print('  - Only pairs with topic>0 can compensate')
print('  - But 82.1% have topic=0!')

print('\nResult:')
print('  - Most pairs have high embedding, zero topic')
print('  - Reducing embedding weight hurt them')
print('  - Increasing topic weight cant help (topic=0)')
print('  - Net effect: Average goes DOWN')

print('\n' + '='*80)
