# Phase 1 結果の即時分析
# Baselineと比較（Baselineは既知の値を使用）

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# 日本語フォント設定
plt.rcParams['font.sans-serif'] = ['Meiryo', 'MS Gothic', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

def quick_analysis():
    """Phase 1の結果を即座に分析"""
    
    print("="*70)
    print("Phase 1 Quick Analysis")
    print("="*70)
    
    # Baseline（既知の値）
    baseline = {
        "total_pairs": 28,
        "avg_similarity": 0.237,
        "max_similarity": 0.885,
        "topic_coverage": 0.179,  # 17.9%
        "perfect_matches": 1,
        "avg_topic_jaccard": 0.048,
        "high_quality_pairs": 1,
    }
    
    # Phase 1結果を読み込み
    pairs_file = Path('output/event_to_event_pairs.csv')
    if not pairs_file.exists():
        print("❌ Phase 1 results not found")
        return
    
    df = pd.read_csv(pairs_file)
    print(f"\n✅ Phase 1 results loaded: {len(df)} pairs")
    
    # Phase 1統計
    phase1 = {
        "total_pairs": len(df),
        "avg_similarity": df['combined_score'].mean(),
        "max_similarity": df['combined_score'].max(),
        "topic_coverage": len(df[df['topic_jaccard'] > 0]) / len(df),
        "perfect_matches": len(df[df['topic_jaccard'] == 1.0]),
        "avg_topic_jaccard": df['topic_jaccard'].mean(),
        "high_quality_pairs": len(df[df['combined_score'] > 0.7]),
        "medium_quality_pairs": len(df[(df['combined_score'] > 0.4) & (df['combined_score'] <= 0.7)]),
        "low_quality_pairs": len(df[df['combined_score'] <= 0.4]),
    }
    
    # コンポーネント統計
    components = {
        "embedding": df['embedding_similarity'].mean(),
        "lexical": df['lexical_similarity'].mean(),
        "topic": df['topic_jaccard'].mean(),
        "temporal": df['temporal_correlation'].mean(),
    }
    
    # 比較表示
    print("\n" + "="*70)
    print("BASELINE vs PHASE 1 COMPARISON")
    print("="*70)
    
    print(f"\n{'Metric':<35} | {'Baseline':>12} | {'Phase 1':>12} | {'Change':>15}")
    print("-"*80)
    
    # 1. 平均類似度
    change = phase1['avg_similarity'] - baseline['avg_similarity']
    change_pct = (change / baseline['avg_similarity'] * 100)
    print(f"{'Average Similarity':<35} | {baseline['avg_similarity']:>12.4f} | {phase1['avg_similarity']:>12.4f} | {change:>+7.4f} ({change_pct:>+5.1f}%)")
    
    # 2. トピックカバレッジ ★★★最重要★★★
    change = phase1['topic_coverage'] - baseline['topic_coverage']
    change_pct = (change / baseline['topic_coverage'] * 100)
    print(f"{'Topic Coverage':<35} | {baseline['topic_coverage']:>12.1%} | {phase1['topic_coverage']:>12.1%} | {change:>+7.1%} ({change_pct:>+5.1f}%)")
    
    # 3. 完全一致
    change = phase1['perfect_matches'] - baseline['perfect_matches']
    print(f"{'Perfect Matches':<35} | {baseline['perfect_matches']:>12d} | {phase1['perfect_matches']:>12d} | {change:>+7d}")
    
    # 4. 平均トピックJaccard
    change = phase1['avg_topic_jaccard'] - baseline['avg_topic_jaccard']
    change_pct = (change / baseline['avg_topic_jaccard'] * 100) if baseline['avg_topic_jaccard'] > 0 else 0
    print(f"{'Average Topic Jaccard':<35} | {baseline['avg_topic_jaccard']:>12.4f} | {phase1['avg_topic_jaccard']:>12.4f} | {change:>+7.4f} ({change_pct:>+5.1f}%)")
    
    # 5. 高品質ペア
    change = phase1['high_quality_pairs'] - baseline['high_quality_pairs']
    print(f"{'High-Quality Pairs (>0.7)':<35} | {baseline['high_quality_pairs']:>12d} | {phase1['high_quality_pairs']:>12d} | {change:>+7d}")
    
    # 品質分布
    print(f"\n{'Quality Distribution (Phase 1):':<35}")
    print(f"  {'High (>0.7)':<30}: {phase1['high_quality_pairs']:2d} ({phase1['high_quality_pairs']/len(df)*100:5.1f}%)")
    print(f"  {'Medium (0.4-0.7)':<30}: {phase1['medium_quality_pairs']:2d} ({phase1['medium_quality_pairs']/len(df)*100:5.1f}%)")
    print(f"  {'Low (<0.4)':<30}: {phase1['low_quality_pairs']:2d} ({phase1['low_quality_pairs']/len(df)*100:5.1f}%)")
    
    # コンポーネント統計
    print(f"\n{'Component Statistics (Phase 1):':<35}")
    for name, value in components.items():
        print(f"  {name.capitalize():<30}: {value:.4f}")
    
    # 評価
    print("\n" + "="*70)
    print("📊 EVALUATION")
    print("="*70)
    
    improvements = []
    concerns = []
    
    # 平均類似度
    if phase1['avg_similarity'] > baseline['avg_similarity']:
        improvement = phase1['avg_similarity'] - baseline['avg_similarity']
        improvements.append(f"✅ Average similarity: +{improvement:.4f} ({(improvement/baseline['avg_similarity']*100):+.1f}%)")
    else:
        decline = baseline['avg_similarity'] - phase1['avg_similarity']
        concerns.append(f"⚠️  Average similarity: -{decline:.4f}")
    
    # トピックカバレッジ（最重要）
    if phase1['topic_coverage'] > baseline['topic_coverage']:
        improvement = (phase1['topic_coverage'] - baseline['topic_coverage']) * 100
        improvement_pct = (phase1['topic_coverage'] - baseline['topic_coverage']) / baseline['topic_coverage'] * 100
        improvements.append(f"✅ Topic coverage: +{improvement:.1f}% (relative: +{improvement_pct:.1f}%)")
    else:
        concerns.append(f"⚠️  Topic coverage did not improve")
    
    # 完全一致
    if phase1['perfect_matches'] > baseline['perfect_matches']:
        improvements.append(f"✅ Perfect matches: {baseline['perfect_matches']} → {phase1['perfect_matches']}")
    elif phase1['perfect_matches'] == baseline['perfect_matches']:
        print(f"➖ Perfect matches maintained: {phase1['perfect_matches']}")
    else:
        concerns.append(f"⚠️  Perfect matches decreased")
    
    # 高品質ペア
    if phase1['high_quality_pairs'] > baseline['high_quality_pairs']:
        improvements.append(f"✅ High-quality pairs: {baseline['high_quality_pairs']} → {phase1['high_quality_pairs']}")
    elif phase1['high_quality_pairs'] == baseline['high_quality_pairs']:
        print(f"➖ High-quality pairs maintained: {phase1['high_quality_pairs']}")
    else:
        concerns.append(f"⚠️  High-quality pairs decreased")
    
    print("\n[Improvements]")
    if improvements:
        for imp in improvements:
            print(f"  {imp}")
    else:
        print("  None")
    
    print("\n[Concerns]")
    if concerns:
        for con in concerns:
            print(f"  {con}")
    else:
        print("  None")
    
    # 総合評価
    success_rate = len(improvements) / (len(improvements) + len(concerns)) if (len(improvements) + len(concerns)) > 0 else 0
    
    print("\n" + "="*70)
    print("🎯 FINAL VERDICT")
    print("="*70)
    
    if success_rate >= 0.75:
        verdict = "🎉 SUCCESS"
        message = "Phase 1 achieved significant improvements!"
        recommendation = "Proceed to Phase 2: Weight Optimization"
    elif success_rate >= 0.5:
        verdict = "✅ PARTIAL SUCCESS"
        message = "Phase 1 showed some improvements."
        recommendation = "Analyze further before Phase 2"
    else:
        verdict = "⚠️  LIMITED SUCCESS"
        message = "Phase 1 did not meet expectations."
        recommendation = "Review strategy and consider alternatives"
    
    print(f"\n  {verdict}")
    print(f"  Success Rate: {success_rate:.1%}")
    print(f"  {message}")
    print(f"\n  📋 Recommendation: {recommendation}")
    
    # 目標達成度
    print("\n" + "="*70)
    print("🎯 Progress Toward November Goal")
    print("="*70)
    
    target = {
        "avg_similarity": 0.35,
        "topic_coverage": 0.35,
        "perfect_matches": 3,
    }
    
    print(f"\n{'Metric':<30} | {'Current':>10} | {'Target':>10} | {'Progress':>10}")
    print("-"*70)
    
    # 平均類似度の進捗
    progress = (phase1['avg_similarity'] / target['avg_similarity']) * 100
    print(f"{'Average Similarity':<30} | {phase1['avg_similarity']:>10.3f} | {target['avg_similarity']:>10.3f} | {progress:>9.1f}%")
    
    # トピックカバレッジの進捗
    progress = (phase1['topic_coverage'] / target['topic_coverage']) * 100
    print(f"{'Topic Coverage':<30} | {phase1['topic_coverage']:>10.1%} | {target['topic_coverage']:>10.1%} | {progress:>9.1f}%")
    
    # 完全一致の進捗
    progress = (phase1['perfect_matches'] / target['perfect_matches']) * 100
    print(f"{'Perfect Matches':<30} | {phase1['perfect_matches']:>10d} | {target['perfect_matches']:>10d} | {progress:>9.1f}%")
    
    # 可視化
    create_visualization(baseline, phase1, components)
    
    return {
        'baseline': baseline,
        'phase1': phase1,
        'components': components,
        'improvements': improvements,
        'concerns': concerns,
        'success_rate': success_rate,
        'verdict': verdict
    }

def create_visualization(baseline, phase1, components):
    """結果の可視化"""
    
    print("\n📊 Creating visualization...")
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Phase 1 Results Analysis', fontsize=16, fontweight='bold')
    
    # 1. メインメトリクスの比較
    ax = axes[0, 0]
    metrics = ['Avg\nSimilarity', 'Topic\nCoverage', 'Avg Topic\nJaccard']
    baseline_vals = [baseline['avg_similarity'], baseline['topic_coverage'], baseline['avg_topic_jaccard']]
    phase1_vals = [phase1['avg_similarity'], phase1['topic_coverage'], phase1['avg_topic_jaccard']]
    
    x = np.arange(len(metrics))
    width = 0.35
    
    ax.bar(x - width/2, baseline_vals, width, label='Baseline', color='lightblue', edgecolor='black')
    ax.bar(x + width/2, phase1_vals, width, label='Phase 1', color='lightgreen', edgecolor='black')
    
    ax.set_ylabel('Score')
    ax.set_title('Performance Metrics Comparison')
    ax.set_xticks(x)
    ax.set_xticklabels(metrics)
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    
    # 2. 品質ペア数の比較
    ax = axes[0, 1]
    categories = ['Perfect\nMatches', 'High-Quality\n(>0.7)']
    baseline_counts = [baseline['perfect_matches'], baseline['high_quality_pairs']]
    phase1_counts = [phase1['perfect_matches'], phase1['high_quality_pairs']]
    
    x = np.arange(len(categories))
    ax.bar(x - width/2, baseline_counts, width, label='Baseline', color='lightblue', edgecolor='black')
    ax.bar(x + width/2, phase1_counts, width, label='Phase 1', color='lightgreen', edgecolor='black')
    
    ax.set_ylabel('Count')
    ax.set_title('Quality Pair Counts')
    ax.set_xticks(x)
    ax.set_xticklabels(categories)
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    
    # 3. 改善率
    ax = axes[1, 0]
    improvements = [
        (phase1['avg_similarity'] - baseline['avg_similarity']) / baseline['avg_similarity'] * 100,
        (phase1['topic_coverage'] - baseline['topic_coverage']) / baseline['topic_coverage'] * 100,
        phase1['perfect_matches'] - baseline['perfect_matches'],
        phase1['high_quality_pairs'] - baseline['high_quality_pairs']
    ]
    improvement_labels = ['Avg Sim\n(%)', 'Topic Cov\n(%)', 'Perfect\n(count)', 'High-Q\n(count)']
    colors = ['green' if x > 0 else 'red' if x < 0 else 'gray' for x in improvements]
    
    ax.barh(improvement_labels, improvements, color=colors, edgecolor='black')
    ax.axvline(0, color='black', linewidth=0.8)
    ax.set_xlabel('Improvement')
    ax.set_title('Phase 1 Improvements')
    ax.grid(axis='x', alpha=0.3)
    
    # 4. コンポーネント統計
    ax = axes[1, 1]
    comp_names = list(components.keys())
    comp_values = list(components.values())
    colors_comp = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99']
    
    ax.bar(comp_names, comp_values, color=colors_comp, edgecolor='black')
    ax.set_ylabel('Mean Score')
    ax.set_title('Component Statistics (Phase 1)')
    ax.set_ylim(0, 1.0)
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    
    output_file = Path('output/phase1_analysis.png')
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"✅ Visualization saved: {output_file}")
    plt.close()

if __name__ == '__main__':
    results = quick_analysis()
    
    if results:
        print("\n" + "="*70)
        print("✅ Phase 1 analysis completed!")
        print("="*70)
        
        if results['verdict'] == "🎉 SUCCESS":
            print("\n🚀 Ready to proceed to Phase 2!")
            print("\nNext action:")
            print("  Apply optimized weights to event_comparison.py:")
            print("    W_EMBEDDING = 0.30")
            print("    W_LEXICAL   = 0.15")
            print("    W_TOPIC     = 0.45  ← Topic重視")
            print("    W_TEMPORAL  = 0.10")
