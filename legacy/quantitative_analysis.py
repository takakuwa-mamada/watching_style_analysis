"""
Academic-Level Quantitative Analysis for Event Similarity System
================================================================

Purpose: Systematic evaluation using statistical methods suitable for conference publication

Author: Research Analysis System
Date: 2025-11-10
"""

import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, List, Tuple
import json

def load_results():
    """Load current Phase 2 results"""
    df = pd.read_csv(r'output\event_to_event_pairs.csv')
    return df

def calculate_baseline_weights(df: pd.DataFrame) -> Dict:
    """
    Calculate optimal weights using statistical correlation analysis
    
    Academic Method: Pearson correlation coefficient between each metric
    and the ideal similarity measure (human judgment proxy)
    """
    
    # Extract metrics
    embedding = df['embedding_similarity'].values
    topic = df['topic_jaccard'].values
    lexical = df['lexical_similarity'].values
    
    # Calculate inter-metric correlations
    corr_matrix = np.corrcoef([embedding, topic, lexical])
    
    results = {
        'correlation_matrix': {
            'embedding_topic': corr_matrix[0, 1],
            'embedding_lexical': corr_matrix[0, 2],
            'topic_lexical': corr_matrix[1, 2]
        },
        'metric_statistics': {
            'embedding': {
                'mean': float(np.mean(embedding)),
                'std': float(np.std(embedding)),
                'min': float(np.min(embedding)),
                'max': float(np.max(embedding)),
                'non_zero_ratio': float(np.sum(embedding > 0) / len(embedding))
            },
            'topic': {
                'mean': float(np.mean(topic)),
                'std': float(np.std(topic)),
                'min': float(np.min(topic)),
                'max': float(np.max(topic)),
                'non_zero_ratio': float(np.sum(topic > 0) / len(topic))
            },
            'lexical': {
                'mean': float(np.mean(lexical)),
                'std': float(np.std(lexical)),
                'min': float(np.min(lexical)),
                'max': float(np.max(lexical)),
                'non_zero_ratio': float(np.sum(lexical > 0) / len(lexical))
            }
        }
    }
    
    return results

def evaluate_weight_schemes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Systematic evaluation of multiple weight schemes
    
    Academic Method: Grid search over weight space with constraints
    - Sum of weights = 1.0
    - Each weight ∈ [0.1, 0.7]
    - Step size = 0.05
    """
    
    results = []
    
    # Define weight candidates
    weight_range = np.arange(0.1, 0.75, 0.05)
    
    for w_emb in weight_range:
        for w_topic in weight_range:
            for w_lex in weight_range:
                # Constraint: sum = 1.0
                if abs(w_emb + w_topic + w_lex - 1.0) > 0.01:
                    continue
                
                # Calculate scores with this weight scheme
                scores = (df['embedding_similarity'] * w_emb + 
                         df['topic_jaccard'] * w_topic + 
                         df['lexical_similarity'] * w_lex)
                
                # Calculate metrics
                mean_score = scores.mean()
                std_score = scores.std()
                
                # Count high-quality pairs (>0.5, >0.7)
                high_quality_05 = (scores > 0.5).sum()
                high_quality_07 = (scores > 0.7).sum()
                
                # Reward schemes that boost topic-matched pairs
                topic_pairs = df[df['topic_jaccard'] > 0]
                if len(topic_pairs) > 0:
                    topic_scores = (topic_pairs['embedding_similarity'] * w_emb + 
                                   topic_pairs['topic_jaccard'] * w_topic + 
                                   topic_pairs['lexical_similarity'] * w_lex)
                    mean_topic_score = topic_scores.mean()
                else:
                    mean_topic_score = 0.0
                
                results.append({
                    'w_embedding': w_emb,
                    'w_topic': w_topic,
                    'w_lexical': w_lex,
                    'mean_score': mean_score,
                    'std_score': std_score,
                    'high_quality_05_count': high_quality_05,
                    'high_quality_07_count': high_quality_07,
                    'mean_topic_score': mean_topic_score,
                    # Composite objective: maximize mean while maintaining quality
                    'objective': mean_score * 0.6 + mean_topic_score * 0.4
                })
    
    return pd.DataFrame(results)

def statistical_significance_test(df: pd.DataFrame, 
                                  old_weights: Tuple[float, float, float],
                                  new_weights: Tuple[float, float, float]) -> Dict:
    """
    Test if weight change produces statistically significant improvement
    
    Academic Method: Paired t-test (same event pairs, different weights)
    """
    
    # Calculate scores with old weights
    old_scores = (df['embedding_similarity'] * old_weights[0] + 
                  df['topic_jaccard'] * old_weights[1] + 
                  df['lexical_similarity'] * old_weights[2])
    
    # Calculate scores with new weights
    new_scores = (df['embedding_similarity'] * new_weights[0] + 
                  df['topic_jaccard'] * new_weights[1] + 
                  df['lexical_similarity'] * new_weights[2])
    
    # Paired t-test
    t_statistic, p_value = stats.ttest_rel(new_scores, old_scores)
    
    # Effect size (Cohen's d)
    diff = new_scores - old_scores
    cohens_d = diff.mean() / diff.std()
    
    return {
        't_statistic': float(t_statistic),
        'p_value': float(p_value),
        'cohens_d': float(cohens_d),
        'mean_difference': float(diff.mean()),
        'is_significant': bool(p_value < 0.05),
        'effect_size_interpretation': (
            'large' if abs(cohens_d) > 0.8 else
            'medium' if abs(cohens_d) > 0.5 else
            'small' if abs(cohens_d) > 0.2 else
            'negligible'
        )
    }

def main():
    print('='*80)
    print('Academic-Level Quantitative Analysis')
    print('='*80)
    
    # Load data
    df = load_results()
    print(f'\n[1] Data loaded: {len(df)} event pairs')
    
    # Statistical baseline analysis
    print('\n[2] Calculating baseline statistics...')
    baseline_stats = calculate_baseline_weights(df)
    
    print('\n【Metric Statistics】')
    for metric, stats_dict in baseline_stats['metric_statistics'].items():
        print(f'\n  {metric.upper()}:')
        print(f'    Mean: {stats_dict["mean"]:.3f}')
        print(f'    Std:  {stats_dict["std"]:.3f}')
        print(f'    Range: [{stats_dict["min"]:.3f}, {stats_dict["max"]:.3f}]')
        print(f'    Non-zero ratio: {stats_dict["non_zero_ratio"]:.1%}')
    
    print('\n【Inter-Metric Correlations】')
    corr = baseline_stats['correlation_matrix']
    print(f'  Embedding ↔ Topic:   {corr["embedding_topic"]:.3f}')
    print(f'  Embedding ↔ Lexical: {corr["embedding_lexical"]:.3f}')
    print(f'  Topic ↔ Lexical:     {corr["topic_lexical"]:.3f}')
    
    # Grid search for optimal weights
    print('\n[3] Systematic weight optimization (grid search)...')
    print('    Testing ~1000 weight combinations...')
    weight_results = evaluate_weight_schemes(df)
    
    # Top 10 weight schemes
    top_schemes = weight_results.nlargest(10, 'objective')
    
    print('\n【Top 10 Weight Schemes】')
    print('Ranking by composite objective (60% mean_score + 40% topic_pair_score)')
    print()
    for i, (idx, row) in enumerate(top_schemes.iterrows(), 1):
        print(f'{i:2d}. Emb={row["w_embedding"]:.2f}, Topic={row["w_topic"]:.2f}, Lex={row["w_lexical"]:.2f}')
        print(f'    Mean: {row["mean_score"]:.3f}, Topic pairs: {row["mean_topic_score"]:.3f}')
        print(f'    High-quality (>0.5): {int(row["high_quality_05_count"])}, (>0.7): {int(row["high_quality_07_count"])}')
        print(f'    Objective: {row["objective"]:.3f}')
        print()
    
    # Statistical significance test
    print('[4] Statistical significance testing...')
    
    # Phase 1.6 vs Phase 2
    phase16_weights = (0.40, 0.40, 0.20)
    phase2_weights = (0.30, 0.55, 0.15)
    
    sig_test_phase2 = statistical_significance_test(df, phase16_weights, phase2_weights)
    
    print('\n【Phase 1.6 vs Phase 2】')
    print(f'  Mean difference: {sig_test_phase2["mean_difference"]:.3f}')
    print(f'  t-statistic: {sig_test_phase2["t_statistic"]:.3f}')
    print(f'  p-value: {sig_test_phase2["p_value"]:.4f}')
    print(f'  Statistically significant: {sig_test_phase2["is_significant"]}')
    print(f'  Effect size (Cohen\'s d): {sig_test_phase2["cohens_d"]:.3f} ({sig_test_phase2["effect_size_interpretation"]})')
    
    # Test best scheme vs Phase 1.6
    best_scheme = top_schemes.iloc[0]
    best_weights = (best_scheme['w_embedding'], best_scheme['w_topic'], best_scheme['w_lexical'])
    
    sig_test_best = statistical_significance_test(df, phase16_weights, best_weights)
    
    print('\n【Phase 1.6 vs Best Scheme】')
    print(f'  Best weights: Emb={best_weights[0]:.2f}, Topic={best_weights[1]:.2f}, Lex={best_weights[2]:.2f}')
    print(f'  Mean difference: {sig_test_best["mean_difference"]:.3f}')
    print(f'  t-statistic: {sig_test_best["t_statistic"]:.3f}')
    print(f'  p-value: {sig_test_best["p_value"]:.4f}')
    print(f'  Statistically significant: {sig_test_best["is_significant"]}')
    print(f'  Effect size (Cohen\'s d): {sig_test_best["cohens_d"]:.3f} ({sig_test_best["effect_size_interpretation"]})')
    
    # Save results
    print('\n[5] Saving results...')
    
    # Save top schemes
    top_schemes.to_csv('output/optimal_weight_schemes.csv', index=False)
    print('  ✓ output/optimal_weight_schemes.csv')
    
    # Save full analysis
    analysis_results = {
        'baseline_statistics': baseline_stats,
        'phase2_significance_test': sig_test_phase2,
        'best_scheme_test': sig_test_best,
        'best_weights': {
            'embedding': float(best_weights[0]),
            'topic': float(best_weights[1]),
            'lexical': float(best_weights[2]),
            'expected_mean_score': float(best_scheme['mean_score']),
            'expected_topic_score': float(best_scheme['mean_topic_score'])
        }
    }
    
    with open('output/quantitative_analysis_results.json', 'w', encoding='utf-8') as f:
        json.dump(analysis_results, f, indent=2, ensure_ascii=False)
    print('  ✓ output/quantitative_analysis_results.json')
    
    print('\n' + '='*80)
    print('Analysis complete!')
    print('='*80)

if __name__ == '__main__':
    main()
