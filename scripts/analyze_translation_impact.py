# -*- coding: utf-8 -*-
"""
Translation Impact Analysis

Translation Bridge適用前後の結果を比較し、改善効果を定量評価

使い方:
    python scripts/analyze_translation_impact.py
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path


def load_results(before_path='output/event_to_event_pairs_before_translation.csv',
                 after_path='output/event_to_event_pairs.csv'):
    """Before/After結果をロード"""
    
    print("="*70)
    print("Translation Impact Analysis")
    print("="*70)
    
    # Load CSVs
    try:
        df_before = pd.read_csv(before_path)
        print(f"\n✓ Loaded BEFORE: {before_path}")
        print(f"  Rows: {len(df_before)}")
    except FileNotFoundError:
        print(f"\n✗ BEFORE file not found: {before_path}")
        return None, None
    
    try:
        df_after = pd.read_csv(after_path)
        print(f"✓ Loaded AFTER:  {after_path}")
        print(f"  Rows: {len(df_after)}")
    except FileNotFoundError:
        print(f"\n✗ AFTER file not found: {after_path}")
        return None, None
    
    return df_before, df_after


def compare_metrics(df_before, df_after):
    """主要メトリクスを比較"""
    
    print("\n" + "="*70)
    print("METRIC COMPARISON")
    print("="*70)
    
    metrics = []
    
    # 1. Topic Jaccard > 0の割合
    before_jaccard_positive = (df_before['topic_jaccard'] > 0).mean() * 100
    after_jaccard_positive = (df_after['topic_jaccard'] > 0).mean() * 100
    improvement_jaccard = after_jaccard_positive - before_jaccard_positive
    
    metrics.append({
        'Metric': 'Topic Jaccard > 0',
        'Before': f"{before_jaccard_positive:.1f}%",
        'After': f"{after_jaccard_positive:.1f}%",
        'Change': f"{improvement_jaccard:+.1f}%",
        'Improvement': improvement_jaccard > 0
    })
    
    # 2. Average Similarity
    before_avg_sim = df_before['combined_score'].mean()
    after_avg_sim = df_after['combined_score'].mean()
    improvement_sim = after_avg_sim - before_avg_sim
    
    metrics.append({
        'Metric': 'Average Similarity',
        'Before': f"{before_avg_sim:.3f}",
        'After': f"{after_avg_sim:.3f}",
        'Change': f"{improvement_sim:+.3f}",
        'Improvement': improvement_sim > 0
    })
    
    # 3. Max Similarity
    before_max_sim = df_before['combined_score'].max()
    after_max_sim = df_after['combined_score'].max()
    improvement_max = after_max_sim - before_max_sim
    
    metrics.append({
        'Metric': 'Max Similarity',
        'Before': f"{before_max_sim:.3f}",
        'After': f"{after_max_sim:.3f}",
        'Change': f"{improvement_max:+.3f}",
        'Improvement': improvement_max > 0
    })
    
    # 4. Confidence > 0.7
    before_high_conf = (df_before['combined_score'] > 0.7).mean() * 100
    after_high_conf = (df_after['combined_score'] > 0.7).mean() * 100
    improvement_conf = after_high_conf - before_high_conf
    
    metrics.append({
        'Metric': 'Confidence > 0.7',
        'Before': f"{before_high_conf:.1f}%",
        'After': f"{after_high_conf:.1f}%",
        'Change': f"{improvement_conf:+.1f}%",
        'Improvement': improvement_conf > 0
    })
    
    # 5. Average Topic Jaccard (非ゼロのみ)
    before_avg_jaccard = df_before[df_before['topic_jaccard'] > 0]['topic_jaccard'].mean()
    after_avg_jaccard = df_after[df_after['topic_jaccard'] > 0]['topic_jaccard'].mean()
    improvement_avg_jaccard = after_avg_jaccard - before_avg_jaccard
    
    metrics.append({
        'Metric': 'Avg Topic Jaccard (>0)',
        'Before': f"{before_avg_jaccard:.3f}",
        'After': f"{after_avg_jaccard:.3f}",
        'Change': f"{improvement_avg_jaccard:+.3f}",
        'Improvement': improvement_avg_jaccard > 0
    })
    
    # Display table
    df_metrics = pd.DataFrame(metrics)
    print("\n" + df_metrics.to_string(index=False))
    
    # Summary
    improved_count = sum(m['Improvement'] for m in metrics)
    print(f"\n{'='*70}")
    print(f"Summary: {improved_count}/{len(metrics)} metrics improved")
    
    if improved_count >= len(metrics) * 0.8:
        print("✓ SIGNIFICANT IMPROVEMENT - Translation Bridge is effective!")
    elif improved_count >= len(metrics) * 0.5:
        print("⚠ MODERATE IMPROVEMENT - Translation Bridge has some effect")
    else:
        print("✗ LIMITED IMPROVEMENT - Translation Bridge may need tuning")
    
    return df_metrics


def plot_comparison(df_before, df_after, output_dir='output'):
    """比較グラフを作成"""
    
    Path(output_dir).mkdir(exist_ok=True)
    
    # Set style
    sns.set_style("whitegrid")
    plt.rcParams['font.sans-serif'] = ['Meiryo', 'Yu Gothic', 'MS Gothic']
    
    # Figure with 2x2 subplots
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Translation Bridge Impact Analysis', fontsize=16, fontweight='bold')
    
    # 1. Topic Jaccard Distribution
    ax = axes[0, 0]
    bins = np.linspace(0, 1, 21)
    ax.hist(df_before['topic_jaccard'], bins=bins, alpha=0.5, label='Before', color='red', edgecolor='black')
    ax.hist(df_after['topic_jaccard'], bins=bins, alpha=0.5, label='After (Translation)', color='green', edgecolor='black')
    ax.set_xlabel('Topic Jaccard Similarity')
    ax.set_ylabel('Frequency')
    ax.set_title('Topic Jaccard Distribution')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 2. Combined Score Distribution
    ax = axes[0, 1]
    bins = np.linspace(0, 1, 21)
    ax.hist(df_before['combined_score'], bins=bins, alpha=0.5, label='Before', color='red', edgecolor='black')
    ax.hist(df_after['combined_score'], bins=bins, alpha=0.5, label='After (Translation)', color='green', edgecolor='black')
    ax.set_xlabel('Combined Similarity Score')
    ax.set_ylabel('Frequency')
    ax.set_title('Overall Similarity Distribution')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 3. Bar chart comparison
    ax = axes[1, 0]
    metrics = ['Topic Jaccard>0', 'Avg Similarity', 'Confidence>0.7']
    before_values = [
        (df_before['topic_jaccard'] > 0).mean() * 100,
        df_before['combined_score'].mean() * 100,
        (df_before['combined_score'] > 0.7).mean() * 100
    ]
    after_values = [
        (df_after['topic_jaccard'] > 0).mean() * 100,
        df_after['combined_score'].mean() * 100,
        (df_after['combined_score'] > 0.7).mean() * 100
    ]
    
    x = np.arange(len(metrics))
    width = 0.35
    
    ax.bar(x - width/2, before_values, width, label='Before', color='red', alpha=0.7)
    ax.bar(x + width/2, after_values, width, label='After (Translation)', color='green', alpha=0.7)
    ax.set_ylabel('Percentage (%)')
    ax.set_title('Key Metrics Comparison')
    ax.set_xticks(x)
    ax.set_xticklabels(metrics, rotation=15, ha='right')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    # Add value labels
    for i, (b, a) in enumerate(zip(before_values, after_values)):
        ax.text(i - width/2, b + 1, f'{b:.1f}', ha='center', va='bottom', fontsize=9)
        ax.text(i + width/2, a + 1, f'{a:.1f}', ha='center', va='bottom', fontsize=9)
    
    # 4. Scatter plot: Before vs After
    ax = axes[1, 1]
    ax.scatter(df_before['combined_score'], df_after['combined_score'], alpha=0.6, s=100)
    ax.plot([0, 1], [0, 1], 'r--', label='No change', linewidth=2)
    ax.set_xlabel('Similarity Score (Before)')
    ax.set_ylabel('Similarity Score (After)')
    ax.set_title('Pair-wise Comparison')
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    
    # Annotate improved/degraded
    improved = (df_after['combined_score'] > df_before['combined_score']).sum()
    degraded = (df_after['combined_score'] < df_before['combined_score']).sum()
    ax.text(0.05, 0.95, f'Improved: {improved}\nDegraded: {degraded}', 
            transform=ax.transAxes, va='top', fontsize=10,
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    
    output_path = Path(output_dir) / 'translation_impact_analysis.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\n✓ Saved comparison plot: {output_path}")
    
    plt.close()


def analyze_cross_lingual_pairs(df_after):
    """言語横断マッチングを分析"""
    
    print("\n" + "="*70)
    print("CROSS-LINGUAL MATCHING ANALYSIS")
    print("="*70)
    
    # Detect cross-lingual pairs (heuristic: different stream names with different languages)
    # This is a simplified analysis - real implementation would need language metadata
    
    print("\nNote: Full cross-lingual analysis requires language metadata.")
    print("Checking for improved Topic Jaccard scores...")
    
    # Find pairs with high similarity but previously low Jaccard
    # (These are likely cross-lingual matches improved by translation)
    
    improved_pairs = df_after[
        (df_after['combined_score'] > 0.7) & 
        (df_after['topic_jaccard'] > 0.3)
    ].sort_values('combined_score', ascending=False)
    
    print(f"\nHigh-quality matches (similarity>0.7, jaccard>0.3): {len(improved_pairs)}")
    
    if len(improved_pairs) > 0:
        print("\nTop 5 matches:")
        for idx, row in improved_pairs.head(5).iterrows():
            print(f"  {idx+1}. {row['event_A_id']} <-> {row['event_B_id']}")
            print(f"     Similarity: {row['combined_score']:.3f}, Jaccard: {row['topic_jaccard']:.3f}")


def main():
    """メイン処理"""
    
    # Load data
    df_before, df_after = load_results()
    
    if df_before is None or df_after is None:
        print("\n✗ Cannot proceed without both BEFORE and AFTER data")
        return
    
    # Compare metrics
    df_metrics = compare_metrics(df_before, df_after)
    
    # Plot comparison
    plot_comparison(df_before, df_after)
    
    # Analyze cross-lingual pairs
    analyze_cross_lingual_pairs(df_after)
    
    # Save metrics to CSV
    output_path = 'output/translation_impact_metrics.csv'
    df_metrics.to_csv(output_path, index=False)
    print(f"\n✓ Saved metrics to: {output_path}")
    
    print("\n" + "="*70)
    print("Analysis complete!")
    print("="*70)


if __name__ == '__main__':
    main()
