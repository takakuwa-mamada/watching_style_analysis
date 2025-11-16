import pandas as pd
import numpy as np
from scipy.optimize import minimize

# Load current results
df = pd.read_csv('output/event_to_event_pairs.csv')

print('='*80)
print('Reverse Engineering Current Weights')
print('='*80)

# Extract components for all pairs
embeddings = df['embedding_similarity'].values
topics = df['topic_jaccard'].values
lexicals = df['lexical_similarity'].values
scores = df['combined_score'].values

# Method 1: Test known weight combinations
print('\n【Method 1: Testing Known Combinations】\n')

known_weights = [
    (0.40, 0.40, 0.20, 'Phase 1.6'),
    (0.30, 0.55, 0.15, 'Phase 2'),
    (0.50, 0.30, 0.20, 'Phase 3'),
    (0.45, 0.35, 0.20, 'Balanced'),
    (0.60, 0.20, 0.20, 'Embedding-heavy'),
    (0.70, 0.15, 0.15, 'Very Embedding-heavy'),
]

best_match = None
best_error = float('inf')

for w_emb, w_top, w_lex, label in known_weights:
    predicted = embeddings * w_emb + topics * w_top + lexicals * w_lex
    mse = np.mean((predicted - scores) ** 2)
    mae = np.mean(np.abs(predicted - scores))
    
    print(f'{label:25s}: MSE={mse:.6f}, MAE={mae:.6f}')
    
    if mse < best_error:
        best_error = mse
        best_match = (w_emb, w_top, w_lex, label)

print(f'\nBest match: {best_match[3]} (MSE={best_error:.6f})')

# Method 2: Optimize weights to fit observed scores
print('\n【Method 2: Optimized Weight Recovery】\n')

def objective(weights):
    w_emb, w_top, w_lex = weights
    predicted = embeddings * w_emb + topics * w_top + lexicals * w_lex
    return np.mean((predicted - scores) ** 2)

# Constraint: weights sum to 1.0
constraints = {'type': 'eq', 'fun': lambda w: w[0] + w[1] + w[2] - 1.0}
bounds = [(0, 1), (0, 1), (0, 1)]
initial_guess = [0.5, 0.3, 0.2]

result = minimize(objective, initial_guess, method='SLSQP', bounds=bounds, constraints=constraints)

if result.success:
    opt_emb, opt_top, opt_lex = result.x
    print(f'Optimized weights:')
    print(f'  Embedding: {opt_emb:.3f} ({opt_emb*100:.1f}%)')
    print(f'  Topic:     {opt_top:.3f} ({opt_top*100:.1f}%)')
    print(f'  Lexical:   {opt_lex:.3f} ({opt_lex*100:.1f}%)')
    print(f'  Sum:       {opt_emb + opt_top + opt_lex:.3f}')
    print(f'  MSE:       {result.fun:.6f}')
    
    # Check if temporal bonus might be applied
    predicted_base = embeddings * opt_emb + topics * opt_top + lexicals * opt_lex
    residuals = scores - predicted_base
    
    print(f'\n【Residual Analysis】')
    print(f'Mean residual: {residuals.mean():.3f}')
    print(f'Max positive residual: {residuals.max():.3f}')
    print(f'Max negative residual: {residuals.min():.3f}')
    
    if residuals.max() > 0.1:
        print('\n⚠️  Large positive residuals detected!')
        print('This suggests temporal bonus or other adjustments are applied.')
        
        # Find pairs with large positive residuals
        large_residuals = df[residuals > 0.1].copy()
        large_residuals['residual'] = residuals[residuals > 0.1]
        
        if len(large_residuals) > 0:
            print(f'\nPairs with large positive residuals (n={len(large_residuals)}):')
            for idx, row in large_residuals.iterrows():
                print(f'  Event {int(row["event_A_id"])} <-> {int(row["event_B_id"])}')
                print(f'    Observed score: {row["combined_score"]:.3f}')
                print(f'    Base prediction: {predicted_base[idx]:.3f}')
                print(f'    Residual: {residuals[idx]:.3f}')
                print(f'    Temporal corr: {row["temporal_correlation"]:.3f}')
                print()

# Method 3: Check specific pairs
print('【Method 3: Manual Verification of Key Pairs】\n')

key_pairs = [
    (5, 6, 'Highest score'),
    (56, 59, 'Perfect topic match'),
]

for ev_a, ev_b, desc in key_pairs:
    pair = df[((df['event_A_id']==ev_a) & (df['event_B_id']==ev_b)) | 
              ((df['event_A_id']==ev_b) & (df['event_B_id']==ev_a))]
    
    if len(pair) > 0:
        row = pair.iloc[0]
        print(f'{desc}: Event {ev_a} <-> {ev_b}')
        print(f'  Embedding: {row["embedding_similarity"]:.3f}')
        print(f'  Topic: {row["topic_jaccard"]:.3f}')
        print(f'  Lexical: {row["lexical_similarity"]:.3f}')
        print(f'  Temporal: {row["temporal_correlation"]:.3f}')
        print(f'  Observed score: {row["combined_score"]:.3f}')
        
        # Test calculations
        if result.success:
            base = row['embedding_similarity'] * opt_emb + row['topic_jaccard'] * opt_top + row['lexical_similarity'] * opt_lex
            print(f'  Predicted (optimized weights): {base:.3f}')
        print()

print('='*80)
