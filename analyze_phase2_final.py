import pandas as pd

# Load results
df = pd.read_csv(r'output\event_to_event_pairs.csv')

print('='*80)
print('Phase 2 Complete Analysis')
print('='*80)

# 1. Overall statistics
print('\n【1. Overall Statistics】')
print(f'Total pairs: {len(df)}')
print(f'Average combined_score: {df["combined_score"].mean():.3f}')
print(f'Max combined_score: {df["combined_score"].max():.3f}')
print(f'Min combined_score: {df["combined_score"].min():.3f}')

# 2. Event 56<->59 special case
print('\n【2. Event 56 <-> 59 Analysis (Perfect Topic Match)】')
pair_56_59 = df[((df['event_A_id']==56) & (df['event_B_id']==59)) | 
                ((df['event_A_id']==59) & (df['event_B_id']==56))]

if len(pair_56_59) > 0:
    row = pair_56_59.iloc[0]
    
    # Base calculation (without temporal bonus)
    base_calc = row['embedding_similarity'] * 0.30 + row['topic_jaccard'] * 0.55 + row['lexical_similarity'] * 0.15
    
    # Check temporal correlation
    temporal_corr = row['temporal_correlation']
    
    # Calculate with temporal bonus
    if temporal_corr > 0.7:
        bonus_factor = 1.0 + temporal_corr * 0.25
        with_bonus = min(1.0, base_calc * bonus_factor)
    elif temporal_corr > 0.5:
        bonus_factor = 1.0 + temporal_corr * 0.15
        with_bonus = min(1.0, base_calc * bonus_factor)
    else:
        with_bonus = base_calc
    
    print(f'  Embedding: {row["embedding_similarity"]:.3f}')
    print(f'  Topic: {row["topic_jaccard"]:.3f} (PERFECT)')
    print(f'  Lexical: {row["lexical_similarity"]:.3f}')
    print(f'  Temporal correlation: {temporal_corr:.3f}')
    print(f'  Base combined_score: {base_calc:.3f}')
    print(f'  With temporal bonus: {with_bonus:.3f}')
    print(f'  CSV combined_score: {row["combined_score"]:.3f}')
    print(f'  Match: {"✅" if abs(row["combined_score"] - with_bonus) < 0.001 else "❌"}')

# 3. Weight effectiveness check
print('\n【3. Weight Change Effectiveness】')
print('Checking if Phase 2 weights (Topic 55%) made an impact...\n')

# Compare pairs with high topic_jaccard
high_topic = df[df['topic_jaccard'] > 0.5].sort_values('topic_jaccard', ascending=False)

if len(high_topic) > 0:
    print(f'Found {len(high_topic)} pairs with topic_jaccard > 0.5:')
    for i, (idx, row) in enumerate(high_topic.iterrows()):
        base_calc = row['embedding_similarity'] * 0.30 + row['topic_jaccard'] * 0.55 + row['lexical_similarity'] * 0.15
        
        # OLD weights for comparison
        old_calc = row['embedding_similarity'] * 0.40 + row['topic_jaccard'] * 0.40 + row['lexical_similarity'] * 0.20
        
        print(f'\n  {i+1}. Event {int(row["event_A_id"])} <-> {int(row["event_B_id"])}')
        print(f'     Topic jaccard: {row["topic_jaccard"]:.3f}')
        print(f'     OLD formula (40% topic): {old_calc:.3f}')
        print(f'     NEW formula (55% topic): {base_calc:.3f}')
        print(f'     Improvement: +{base_calc - old_calc:.3f}')
else:
    print('  No pairs with topic_jaccard > 0.5')

# 4. Success assessment
print('\n【4. Success Assessment】')
avg_score = df['combined_score'].mean()
print(f'  Average combined_score: {avg_score:.3f}')
print(f'  November goal: 0.350')
print(f'  Status: {"✅ EXCEEDED" if avg_score >= 0.35 else "⚠️ CLOSE" if avg_score >= 0.30 else "❌ BELOW TARGET"}')
print(f'  Achievement rate: {(avg_score/0.35)*100:.1f}%')

# 5. Baseline comparison
baseline_avg = 0.237
print('\n【5. Baseline Comparison】')
print(f'  Phase 1.6 (40% topic): {baseline_avg:.3f}')
print(f'  Phase 2 (55% topic):   {avg_score:.3f}')
print(f'  Improvement: +{avg_score - baseline_avg:.3f} ({((avg_score/baseline_avg - 1) * 100):.1f}%)')

print('\n' + '='*80)
