import pandas as pd

# Load results
df = pd.read_csv(r'output\event_to_event_pairs.csv')

print('='*80)
print('Phase 2 Weight Verification')
print('='*80)

# Display key columns for top 5 pairs
cols = ['event_A_id', 'event_B_id', 'combined_score', 'embedding_similarity', 'topic_jaccard', 'lexical_similarity']
print('\n【Top 5 Pairs - CSV Data】')
print(df[cols].head(5).to_string(index=False))

# Manual calculation verification
print('\n【Manual Calculation Verification】')
print('Formula: embedding*0.30 + topic*0.55 + lexical*0.15\n')

for i in range(5):
    row = df.iloc[i]
    manual_calc = row['embedding_similarity'] * 0.30 + row['topic_jaccard'] * 0.55 + row['lexical_similarity'] * 0.15
    match = '✅' if abs(row['combined_score'] - manual_calc) < 0.001 else '❌'
    
    print(f'{i+1}. Event {int(row["event_A_id"])} <-> {int(row["event_B_id"])}')
    print(f'   CSV combined_score: {row["combined_score"]:.3f}')
    print(f'   Manual calculation: {manual_calc:.3f}')
    print(f'   Match: {match}')
    print()

# Check Event 56<->59
print('【Event 56 <-> 59 (Perfect Topic Match)】')
pair_56_59 = df[((df['event_A_id']==56) & (df['event_B_id']==59)) | 
                ((df['event_A_id']==59) & (df['event_B_id']==56))]

if len(pair_56_59) > 0:
    row = pair_56_59.iloc[0]
    manual_calc = row['embedding_similarity'] * 0.30 + row['topic_jaccard'] * 0.55 + row['lexical_similarity'] * 0.15
    
    print(f'Event {int(row["event_A_id"])} <-> {int(row["event_B_id"])}')
    print(f'  combined_score:      {row["combined_score"]:.3f}')
    print(f'  embedding_similarity: {row["embedding_similarity"]:.3f}')
    print(f'  topic_jaccard:        {row["topic_jaccard"]:.3f} (PERFECT MATCH)')
    print(f'  lexical_similarity:   {row["lexical_similarity"]:.3f}')
    print(f'  Manual calculation:   {manual_calc:.3f}')
    print(f'  Match: {"✅" if abs(row["combined_score"] - manual_calc) < 0.001 else "❌"}')
else:
    print('  Not found in top pairs')

print('\n' + '='*80)
