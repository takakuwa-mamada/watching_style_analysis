import pandas as pd
import numpy as np

# Load current results
df = pd.read_csv('output/event_to_event_pairs.csv')

print('='*80)
print('Current System Status')
print('='*80)

# Overall statistics
print('\n【1. Overall Statistics】')
print(f'Total pairs: {len(df)}')
print(f'Average combined_score: {df["combined_score"].mean():.3f}')
print(f'Median combined_score: {df["combined_score"].median():.3f}')
print(f'Std deviation: {df["combined_score"].std():.3f}')
print(f'Max score: {df["combined_score"].max():.3f}')
print(f'Min score: {df["combined_score"].min():.3f}')

# Check which weights are currently applied
print('\n【2. Weight Detection】')
print('Analyzing top pair to detect current weights...\n')

# Use top pair to reverse-engineer weights
top_row = df.iloc[0]
emb = top_row['embedding_similarity']
top = top_row['topic_jaccard']
lex = top_row['lexical_similarity']
score = top_row['combined_score']

print(f'Top pair: Event {int(top_row["event_A_id"])} <-> {int(top_row["event_B_id"])}')
print(f'  Embedding: {emb:.3f}')
print(f'  Topic: {top:.3f}')
print(f'  Lexical: {lex:.3f}')
print(f'  Combined score: {score:.3f}')

# Test different weight combinations
weights_to_test = [
    (0.40, 0.40, 0.20, 'Phase 1.6 (Original)'),
    (0.30, 0.55, 0.15, 'Phase 2 (Topic-focused)'),
    (0.50, 0.30, 0.20, 'Phase 3 (Embedding-focused)'),
    (0.45, 0.35, 0.20, 'Balanced')
]

print('\nTesting weight combinations:')
for w_emb, w_top, w_lex, label in weights_to_test:
    calc = emb * w_emb + top * w_top + lex * w_lex
    match = '✅' if abs(score - calc) < 0.001 else ''
    print(f'  {label:30s}: {calc:.3f} {match}')

# Distribution analysis
print('\n【3. Score Distribution】')
print(f'High (>=0.7): {len(df[df["combined_score"]>=0.7])}/28 ({len(df[df["combined_score"]>=0.7])/28*100:.1f}%)')
print(f'Mid (0.5-0.7): {len(df[(df["combined_score"]>=0.5) & (df["combined_score"]<0.7)])}/28 ({len(df[(df["combined_score"]>=0.5) & (df["combined_score"]<0.7)])/28*100:.1f}%)')
print(f'Low (<0.5): {len(df[df["combined_score"]<0.5])}/28 ({len(df[df["combined_score"]<0.5])/28*100:.1f}%)')

# Topic coverage
print('\n【4. Topic Coverage】')
print(f'topic_jaccard = 0: {len(df[df["topic_jaccard"]==0])}/28 ({len(df[df["topic_jaccard"]==0])/28*100:.1f}%)')
print(f'topic_jaccard > 0: {len(df[df["topic_jaccard"]>0])}/28 ({len(df[df["topic_jaccard"]>0])/28*100:.1f}%)')
print(f'topic_jaccard > 0.5: {len(df[df["topic_jaccard"]>0.5])}/28 ({len(df[df["topic_jaccard"]>0.5])/28*100:.1f}%)')

# Component averages
print('\n【5. Component Averages】')
print(f'Embedding similarity: {df["embedding_similarity"].mean():.3f}')
print(f'Topic Jaccard: {df["topic_jaccard"].mean():.3f}')
print(f'Lexical similarity: {df["lexical_similarity"].mean():.3f}')

# Goal assessment
print('\n【6. November Goal Assessment】')
print(f'Current average: {df["combined_score"].mean():.3f}')
print(f'November goal: 0.350')
print(f'Gap: {0.350 - df["combined_score"].mean():.3f}')
print(f'Achievement: {(df["combined_score"].mean()/0.350)*100:.1f}%')

print('\n' + '='*80)
