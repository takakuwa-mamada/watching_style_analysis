# Phase 1実行後の自動比較スクリプト
# Baselineと Phase 1の結果を比較

import pandas as pd
import json
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np

# 日本語フォント設定
plt.rcParams['font.sans-serif'] = ['Meiryo', 'MS Gothic', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

def compare_phase1_with_baseline():
    """Phase 1の結果をBaselineと比較"""
    
    print("="*70)
    print("Phase 1 Results Comparison")
    print("="*70)
    
    # Baselineを読み込み
    baseline_file = Path('output/snapshots/baseline_2025-11-10.json')
    if not baseline_file.exists():
        print("❌ Baseline snapshot not found")
        return None
    
    with open(baseline_file, 'r', encoding='utf-8') as f:
        baseline = json.load(f)
    
    print("✅ Baseline loaded")
    
    # Phase 1結果を読み込み
    phase1_file = Path('output/event_to_event_pairs.csv')
    if not phase1_file.exists():
        print("❌ Phase 1 results not found")
        print("   Waiting for event_comparison.py to complete...")
        return None
    
    df_phase1 = pd.read_csv(phase1_file)
    print(f"✅ Phase 1 results loaded ({len(df_phase1)} pairs)")
    
    # Phase 1の統計を計算
    phase1_stats = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "version": "phase1_max_features_3000",
        "changes": ["max_features: 2000 → 3000 (line 686)"],
        "data": {
            "total_pairs": len(df_phase1),
            "avg_similarity": float(df_phase1['combined_score'].mean()),
            "max_similarity": float(df_phase1['combined_score'].max()),
            "std_similarity": float(df_phase1['combined_score'].std()),
            "median_similarity": float(df_phase1['combined_score'].median()),
            "topic_coverage": float(len(df_phase1[df_phase1['topic_jaccard'] > 0]) / len(df_phase1)),
            "perfect_matches": int(len(df_phase1[df_phase1['topic_jaccard'] == 1.0])),
            "avg_topic_jaccard": float(df_phase1['topic_jaccard'].mean()),
            "high_quality_pairs": int(len(df_phase1[df_phase1['combined_score'] > 0.7])),
            "medium_quality_pairs": int(len(df_phase1[(df_phase1['combined_score'] > 0.4) & (df_phase1['combined_score'] <= 0.7)])),
            "low_quality_pairs": int(len(df_phase1[df_phase1['combined_score'] <= 0.4])),
        }
    }
    
    # コンポーネント別統計
    for comp in ['embedding_similarity', 'lexical_similarity', 'topic_jaccard', 'temporal_correlation']:
        if comp in df_phase1.columns:
            phase1_stats['data'][f'{comp}_mean'] = float(df_phase1[comp].mean())
            phase1_stats['data'][f'{comp}_max'] = float(df_phase1[comp].max())
    
    # Baselineからデータ取得
    baseline_stats = {
        "avg_similarity": baseline['data']['basic_stats']['avg_similarity'],
        "topic_coverage": baseline['data']['topic_stats']['coverage'],
        "perfect_matches": baseline['data']['topic_stats']['perfect_matches'],
        "avg_topic_jaccard": baseline['data']['topic_stats']['avg_jaccard'],
        "high_quality_pairs": baseline['data']['quality_distribution']['very_high'],
    }
    
    # 比較表示
    print("\n" + "="*70)
    print("Detailed Comparison")
    print("="*70)
    
    print(f"\n{'Metric':<35} | {'Baseline':>12} | {'Phase 1':>12} | {'Change':>15}")
    print("-"*80)
    
    # 平均類似度
    b_avg = baseline_stats['avg_similarity']
    p1_avg = phase1_stats['data']['avg_similarity']
    change = p1_avg - b_avg
    change_pct = (change / b_avg * 100) if b_avg != 0 else 0
    print(f"{'Average Similarity':<35} | {b_avg:>12.4f} | {p1_avg:>12.4f} | {change:>+7.4f} ({change_pct:>+5.1f}%)")
    
    # トピックカバレッジ
    b_cov = baseline_stats['topic_coverage']
    p1_cov = phase1_stats['data']['topic_coverage']
    change = p1_cov - b_cov
    change_pct = (change / b_cov * 100) if b_cov != 0 else 0
    print(f"{'Topic Coverage':<35} | {b_cov:>12.1%} | {p1_cov:>12.1%} | {change:>+7.1%} ({change_pct:>+5.1f}%)")
    
    # 完全一致
    b_perfect = baseline_stats['perfect_matches']
    p1_perfect = phase1_stats['data']['perfect_matches']
    change = p1_perfect - b_perfect
    print(f"{'Perfect Matches':<35} | {b_perfect:>12d} | {p1_perfect:>12d} | {change:>+7d}")
    
    # 平均トピックJaccard
    b_jaccard = baseline_stats['avg_topic_jaccard']
    p1_jaccard = phase1_stats['data']['avg_topic_jaccard']
    change = p1_jaccard - b_jaccard
    change_pct = (change / b_jaccard * 100) if b_jaccard != 0 else 0
    print(f"{'Average Topic Jaccard':<35} | {b_jaccard:>12.4f} | {p1_jaccard:>12.4f} | {change:>+7.4f} ({change_pct:>+5.1f}%)")
    
    # 高品質ペア
    b_high = baseline_stats['high_quality_pairs']
    p1_high = phase1_stats['data']['high_quality_pairs']
    change = p1_high - b_high
    print(f"{'High-Quality Pairs (>0.7)':<35} | {b_high:>12d} | {p1_high:>12d} | {change:>+7d}")
    
    # 中品質ペア
    p1_medium = phase1_stats['data']['medium_quality_pairs']
    print(f"{'Medium-Quality Pairs (0.4-0.7)':<35} | {' ':>12s} | {p1_medium:>12d} |")
    
    # コンポーネント別比較
    print("\n" + "-"*80)
    print("Component-wise Statistics")
    print("-"*80)
    
    for comp in ['embedding_similarity', 'lexical_similarity', 'topic_jaccard', 'temporal_correlation']:
        if f'{comp}_mean' in phase1_stats['data']:
            comp_name = comp.replace('_', ' ').title()
            p1_mean = phase1_stats['data'][f'{comp}_mean']
            p1_max = phase1_stats['data'][f'{comp}_max']
            print(f"  {comp_name:<30}: mean={p1_mean:.3f}, max={p1_max:.3f}")
    
    # 評価
    print("\n" + "="*70)
    print("📊 Phase 1 Evaluation")
    print("="*70)
    
    improvements = []
    concerns = []
    
    # 平均類似度
    if p1_avg > b_avg:
        improvements.append(f"✅ Average similarity improved by {(p1_avg - b_avg):.4f} ({change_pct:+.1f}%)")
    elif p1_avg < b_avg:
        concerns.append(f"⚠️  Average similarity decreased by {(b_avg - p1_avg):.4f}")
    else:
        print("➖ Average similarity unchanged")
    
    # トピックカバレッジ
    if p1_cov > b_cov:
        improvement_rate = (p1_cov - b_cov) / b_cov * 100
        improvements.append(f"✅ Topic coverage improved by {improvement_rate:.1f}% (absolute: {(p1_cov - b_cov)*100:.1f}%)")
    else:
        concerns.append(f"⚠️  Topic coverage did not improve")
    
    # 完全一致
    if p1_perfect > b_perfect:
        improvements.append(f"✅ Perfect matches increased: {b_perfect} → {p1_perfect}")
    elif p1_perfect == b_perfect:
        print(f"➖ Perfect matches maintained at {p1_perfect}")
    else:
        concerns.append(f"⚠️  Perfect matches decreased: {b_perfect} → {p1_perfect}")
    
    # 高品質ペア
    if p1_high > b_high:
        improvements.append(f"✅ High-quality pairs increased: {b_high} → {p1_high}")
    elif p1_high == b_high:
        print(f"➖ High-quality pairs maintained at {p1_high}")
    else:
        concerns.append(f"⚠️  High-quality pairs decreased")
    
    # 結果表示
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
    print("\n" + "="*70)
    success_rate = len(improvements) / (len(improvements) + len(concerns)) if (len(improvements) + len(concerns)) > 0 else 0
    
    if success_rate >= 0.75:
        print("🎉 Phase 1 SUCCESS! Significant improvement achieved.")
        recommendation = "proceed_to_phase2"
    elif success_rate >= 0.5:
        print("✅ Phase 1 PARTIAL SUCCESS. Some improvements observed.")
        recommendation = "analyze_further"
    else:
        print("⚠️  Phase 1 LIMITED SUCCESS. Consider alternative approaches.")
        recommendation = "review_strategy"
    
    print(f"   Success rate: {success_rate:.1%}")
    
    # スナップショット保存
    output_dir = Path('output/snapshots')
    output_dir.mkdir(exist_ok=True)
    
    json_file = output_dir / 'phase1_results.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump({
            'phase1_stats': phase1_stats,
            'comparison': {
                'improvements': improvements,
                'concerns': concerns,
                'success_rate': success_rate,
                'recommendation': recommendation
            }
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Phase 1 snapshot saved: {json_file}")
    
    # 可視化
    create_comparison_visualization(baseline_stats, phase1_stats['data'])
    
    # 次のステップの提案
    print("\n" + "="*70)
    print("📋 Next Steps")
    print("="*70)
    
    if recommendation == "proceed_to_phase2":
        print("\n✅ Proceed to Phase 2: Weight Optimization")
        print("   Action: Apply optimized weights (Emb=0.30, Lex=0.15, Topic=0.45, Temp=0.10)")
        print("   File: event_comparison.py (combined_score calculation)")
        print("   Expected: Better separation of high-quality pairs")
    elif recommendation == "analyze_further":
        print("\n⚠️  Further analysis recommended")
        print("   1. Review which pairs improved")
        print("   2. Check if new topics were captured")
        print("   3. Consider adjusting max_features further (3000 → 4000?)")
    else:
        print("\n⚠️  Strategy review recommended")
        print("   1. Check if data changed")
        print("   2. Verify code changes were applied correctly")
        print("   3. Consider alternative parameters")
    
    return phase1_stats, recommendation

def create_comparison_visualization(baseline_stats, phase1_stats):
    """Baseline vs Phase 1の可視化"""
    
    print("\n📊 Creating comparison visualization...")
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Phase 1 vs Baseline Comparison', fontsize=16, fontweight='bold')
    
    # 1. 平均類似度の比較
    ax = axes[0, 0]
    metrics = ['Avg Similarity', 'Topic Coverage', 'Avg Topic\nJaccard']
    baseline_vals = [
        baseline_stats['avg_similarity'],
        baseline_stats['topic_coverage'],
        baseline_stats['avg_topic_jaccard']
    ]
    phase1_vals = [
        phase1_stats['avg_similarity'],
        phase1_stats['topic_coverage'],
        phase1_stats['avg_topic_jaccard']
    ]
    
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
    
    # 2. Perfect matchesと高品質ペアの比較
    ax = axes[0, 1]
    categories = ['Perfect\nMatches', 'High-Quality\nPairs (>0.7)']
    baseline_counts = [
        baseline_stats['perfect_matches'],
        baseline_stats['high_quality_pairs']
    ]
    phase1_counts = [
        phase1_stats['perfect_matches'],
        phase1_stats['high_quality_pairs']
    ]
    
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
        (phase1_stats['avg_similarity'] - baseline_stats['avg_similarity']) / baseline_stats['avg_similarity'] * 100,
        (phase1_stats['topic_coverage'] - baseline_stats['topic_coverage']) / baseline_stats['topic_coverage'] * 100,
        phase1_stats['perfect_matches'] - baseline_stats['perfect_matches'],
        phase1_stats['high_quality_pairs'] - baseline_stats['high_quality_pairs']
    ]
    improvement_labels = ['Avg Sim\n(%)', 'Topic Cov\n(%)', 'Perfect\n(count)', 'High-Q\n(count)']
    colors = ['green' if x > 0 else 'red' if x < 0 else 'gray' for x in improvements]
    
    ax.barh(improvement_labels, improvements, color=colors, edgecolor='black')
    ax.axvline(0, color='black', linewidth=0.8)
    ax.set_xlabel('Improvement')
    ax.set_title('Phase 1 Improvements')
    ax.grid(axis='x', alpha=0.3)
    
    # 4. コンポーネント別比較
    ax = axes[1, 1]
    components = ['Embedding', 'Lexical', 'Topic', 'Temporal']
    phase1_component_vals = [
        phase1_stats.get('embedding_similarity_mean', 0),
        phase1_stats.get('lexical_similarity_mean', 0),
        phase1_stats.get('topic_jaccard_mean', 0),
        phase1_stats.get('temporal_correlation_mean', 0)
    ]
    
    ax.bar(components, phase1_component_vals, color='lightcoral', edgecolor='black')
    ax.set_ylabel('Mean Score')
    ax.set_title('Component Statistics (Phase 1)')
    ax.set_ylim(0, 1.0)
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    
    output_file = Path('output/phase1_vs_baseline_comparison.png')
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"✅ Visualization saved: {output_file}")
    plt.close()

if __name__ == '__main__':
    results = compare_phase1_with_baseline()
    
    if results:
        print("\n" + "="*70)
        print("✅ Phase 1 comparison completed!")
        print("="*70)
    else:
        print("\n⏸️  Waiting for Phase 1 execution to complete...")
        print("   Run this script again after event_comparison.py finishes.")
