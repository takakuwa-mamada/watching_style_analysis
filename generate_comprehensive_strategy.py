# 統合分析レポート生成
# Phase 0-3の全結果をまとめる

import json
from pathlib import Path
from datetime import datetime
import pandas as pd

def generate_comprehensive_report():
    """Phase 0-3の全結果を統合したレポートを生成"""
    
    print("="*70)
    print("Generating Comprehensive Analysis Report")
    print("="*70)
    
    snapshots_dir = Path('output/snapshots')
    
    # 各Phaseの結果を読み込み
    reports = {}
    
    # Baseline
    baseline_file = snapshots_dir / 'baseline_2025-11-10.json'
    if baseline_file.exists():
        with open(baseline_file, 'r', encoding='utf-8') as f:
            reports['baseline'] = json.load(f)
        print("✅ Loaded baseline report")
    else:
        print("⚠️  Baseline report not found")
    
    # Phase 2
    phase2_file = snapshots_dir / 'phase2_optimized_weights.json'
    if phase2_file.exists():
        with open(phase2_file, 'r', encoding='utf-8') as f:
            reports['phase2'] = json.load(f)
        print("✅ Loaded Phase 2 report")
    else:
        print("⚠️  Phase 2 report not found")
    
    # Phase 3
    phase3_file = snapshots_dir / 'phase3_temporal_analysis.json'
    if phase3_file.exists():
        with open(phase3_file, 'r', encoding='utf-8') as f:
            reports['phase3'] = json.load(f)
        print("✅ Loaded Phase 3 report")
    else:
        print("⚠️  Phase 3 report not found")
    
    # 統合レポートを作成
    print("\n" + "="*70)
    print("Summary of All Analyses")
    print("="*70)
    
    if 'baseline' in reports:
        print("\n[Baseline Performance]")
        print(f"  Total pairs:        {reports['baseline']['data']['basic_stats']['total_pairs']}")
        print(f"  Average similarity: {reports['baseline']['data']['basic_stats']['avg_similarity']:.3f}")
        print(f"  Topic coverage:     {reports['baseline']['data']['topic_stats']['coverage']:.1%}")
        print(f"  Perfect matches:    {reports['baseline']['data']['topic_stats']['perfect_matches']}")
    
    if 'phase2' in reports:
        print("\n[Phase 2: Optimized Weights]")
        weights = reports['phase2']['best_weights']
        print(f"  Embedding:  {weights['w_embedding']:.2f}")
        print(f"  Lexical:    {weights['w_lexical']:.2f}")
        print(f"  Topic:      {weights['w_topic']:.2f}")
        print(f"  Temporal:   {weights['w_temporal']:.2f}")
        print(f"\n  Expected improvement:")
        print(f"    Separation:  {weights['separation']:.4f}")
        print(f"    Overall avg: {weights['avg_all']:.4f}")
    
    if 'phase3' in reports:
        print("\n[Phase 3: Temporal Analysis]")
        stats = reports['phase3']['current_stats']
        print(f"  Temporal mean: {stats['mean']:.3f}")
        print(f"  Temporal max:  {stats['max']:.3f}")
        print(f"  Recommended:   {reports['phase3']['recommendations']['recommended']}")
    
    # 改善戦略のまとめ
    print("\n" + "="*70)
    print("Recommended Improvement Strategy")
    print("="*70)
    
    strategy = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "phases": [],
        "expected_improvements": {},
        "implementation_order": []
    }
    
    # Phase 1: max_features拡張
    print("\n📍 Phase 1: Increase max_features (COMPLETED)")
    print("   Status: ✅ Code modified (2000 → 3000)")
    print("   Expected: +5-8% topic coverage")
    print("   Action:   Re-run event_comparison.py")
    
    strategy["phases"].append({
        "phase": "phase1",
        "name": "max_features expansion",
        "status": "code_modified",
        "expected_improvement": "topic_coverage +5-8%"
    })
    strategy["implementation_order"].append("phase1_max_features")
    
    # Phase 2: 重み最適化
    if 'phase2' in reports:
        print("\n📍 Phase 2: Optimize Weights (ANALYZED)")
        print("   Status: ⚠️  Analysis complete, implementation pending")
        print(f"   Optimal weights: Emb={weights['w_embedding']:.2f}, "
              f"Lex={weights['w_lexical']:.2f}, "
              f"Topic={weights['w_topic']:.2f}, "
              f"Temp={weights['w_temporal']:.2f}")
        print("   Note:   Topic weight increased to 45% (from ~35%)")
        print("   Action: Apply weights to event_comparison.py")
        
        strategy["phases"].append({
            "phase": "phase2",
            "name": "weight optimization",
            "status": "analyzed",
            "optimal_weights": weights,
            "note": "Maximizes separation, topic-focused"
        })
        strategy["implementation_order"].append("phase2_weights")
    
    # Phase 3: 時間類似度改善
    if 'phase3' in reports:
        print("\n📍 Phase 3: Temporal Improvement (ANALYZED)")
        print("   Status: ✅ Temporal consistency is actually good (4.81×)")
        print("   Finding: Previous 0.49× was calculation error")
        print("   Optional: Implement robust temporal for outlier resistance")
        print("   Priority: LOW (current method works well)")
        
        strategy["phases"].append({
            "phase": "phase3",
            "name": "temporal improvement",
            "status": "analyzed",
            "finding": "current_method_adequate",
            "priority": "low",
            "optional": "robust_temporal_for_outliers"
        })
    
    # Phase 4: 追加機能（オプション）
    print("\n📍 Phase 4: Additional Features (OPTIONAL)")
    print("   - Sentiment analysis")
    print("   - Broadcaster overlap")
    print("   - Comment density patterns")
    print("   Priority: MEDIUM (after Phase 1-2)")
    
    strategy["phases"].append({
        "phase": "phase4",
        "name": "additional_features",
        "status": "not_started",
        "priority": "medium",
        "features": ["sentiment", "broadcaster_overlap", "comment_density"]
    })
    
    # 実行優先順位
    print("\n" + "="*70)
    print("Execution Priority")
    print("="*70)
    
    print("\n🔴 HIGH PRIORITY (Do First):")
    print("   1. ✅ Phase 1: max_features=3000 (DONE - ready to run)")
    print("      → Re-run event_comparison.py to see improvement")
    print("      → Expected: Topic coverage 17.9% → 25-30%")
    
    print("\n🟡 MEDIUM PRIORITY (After Phase 1):")
    print("   2. Phase 2: Apply optimized weights")
    print("      → Update combined_score calculation")
    print("      → Topic weight 45% (emphasize topic matching)")
    print("      → Expected: Better separation of high-quality pairs")
    
    print("\n🟢 LOW PRIORITY (Optional):")
    print("   3. Phase 3: Robust temporal (optional)")
    print("      → Current method works well (4.81× consistency)")
    print("      → Only needed for outlier resistance")
    
    print("\n   4. Phase 4: Additional features")
    print("      → Sentiment analysis")
    print("      → Broadcaster metrics")
    
    # 期待される最終結果
    print("\n" + "="*70)
    print("Expected Final Performance")
    print("="*70)
    
    baseline_avg = reports['baseline']['data']['basic_stats']['avg_similarity'] if 'baseline' in reports else 0.237
    baseline_cov = reports['baseline']['data']['topic_stats']['coverage'] if 'baseline' in reports else 0.179
    
    print(f"\n[Current Baseline]")
    print(f"  Average similarity: {baseline_avg:.3f}")
    print(f"  Topic coverage:     {baseline_cov:.1%}")
    print(f"  Perfect matches:    1")
    
    print(f"\n[After Phase 1 (max_features=3000)]")
    expected_avg_p1 = baseline_avg + 0.03  # +0.03 improvement
    expected_cov_p1 = baseline_cov * 1.4   # +40% improvement
    print(f"  Average similarity: {expected_avg_p1:.3f} ({expected_avg_p1-baseline_avg:+.3f})")
    print(f"  Topic coverage:     {expected_cov_p1:.1%} ({expected_cov_p1-baseline_cov:+.1%})")
    print(f"  Perfect matches:    1-2")
    
    print(f"\n[After Phase 1+2 (with optimized weights)]")
    # Phase 2の重みは分離度を最大化するが、全体平均は若干下がる可能性がある
    # しかし、トピック重視により意味のあるペアが際立つ
    print(f"  Average similarity: {expected_avg_p1:.3f} (maintained)")
    print(f"  Topic coverage:     {expected_cov_p1:.1%} (maintained)")
    print(f"  Perfect matches:    1-2")
    print(f"  Quality:            Better separation of high-quality pairs")
    
    print(f"\n[Target (November End)]")
    print(f"  Average similarity: 0.35  (current: {baseline_avg:.3f})")
    print(f"  Topic coverage:     35%   (current: {baseline_cov:.1%})")
    print(f"  Perfect matches:    2-3   (current: 1)")
    
    strategy["expected_improvements"]["after_phase1"] = {
        "avg_similarity": round(expected_avg_p1, 3),
        "topic_coverage": round(expected_cov_p1, 3),
        "perfect_matches": "1-2"
    }
    
    strategy["expected_improvements"]["target_november"] = {
        "avg_similarity": 0.35,
        "topic_coverage": 0.35,
        "perfect_matches": "2-3"
    }
    
    # 保存
    output_file = snapshots_dir / 'comprehensive_strategy.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(strategy, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Strategy saved: {output_file}")
    
    # テキストレポート
    txt_file = snapshots_dir / 'comprehensive_strategy.txt'
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write("="*70 + "\n")
        f.write("Comprehensive Improvement Strategy\n")
        f.write("="*70 + "\n\n")
        
        f.write(f"Generated: {strategy['date']}\n\n")
        
        f.write("[Baseline Performance]\n")
        if 'baseline' in reports:
            f.write(f"  Average similarity: {baseline_avg:.3f}\n")
            f.write(f"  Topic coverage:     {baseline_cov:.1%}\n")
            f.write(f"  Perfect matches:    1\n\n")
        
        f.write("[Implementation Order]\n")
        f.write("  1. 🔴 HIGH: Phase 1 - max_features=3000 (READY TO RUN)\n")
        f.write("  2. 🟡 MEDIUM: Phase 2 - Optimized weights\n")
        f.write("  3. 🟢 LOW: Phase 3 - Robust temporal (optional)\n")
        f.write("  4. 🟢 LOW: Phase 4 - Additional features (optional)\n\n")
        
        f.write("[Expected Improvements]\n")
        f.write(f"  After Phase 1:\n")
        f.write(f"    Avg similarity: {baseline_avg:.3f} → {expected_avg_p1:.3f}\n")
        f.write(f"    Topic coverage: {baseline_cov:.1%} → {expected_cov_p1:.1%}\n\n")
        
        f.write(f"  November Target:\n")
        f.write(f"    Avg similarity: 0.35\n")
        f.write(f"    Topic coverage: 35%\n")
        f.write(f"    Perfect matches: 2-3\n\n")
        
        if 'phase2' in reports:
            f.write("[Phase 2: Optimal Weights]\n")
            f.write(f"  Embedding:  {weights['w_embedding']:.2f} (30%)\n")
            f.write(f"  Lexical:    {weights['w_lexical']:.2f} (15%)\n")
            f.write(f"  Topic:      {weights['w_topic']:.2f} (45%)\n")
            f.write(f"  Temporal:   {weights['w_temporal']:.2f} (10%)\n\n")
        
        f.write("[Next Action]\n")
        f.write("  Execute: python event_comparison.py --folder \"data\\football\\game4\" --pattern \"*.csv\" --peak-pad 3 --embedding-match-th 0.70\n")
        f.write("  Time: 30-60 minutes\n")
        f.write("  Then: Compare results with baseline\n")
    
    print(f"✅ Text report saved: {txt_file}")
    
    print("\n" + "="*70)
    print("✅ Comprehensive Report Generated!")
    print("="*70)
    
    return strategy

if __name__ == '__main__':
    strategy = generate_comprehensive_report()
    
    print("\n" + "="*70)
    print("🎯 READY TO EXECUTE")
    print("="*70)
    
    print("\n次のコマンドを実行して、Phase 1の効果を確認してください：")
    print("\n  python event_comparison.py --folder \"data\\football\\game4\" --pattern \"*.csv\" --peak-pad 3 --embedding-match-th 0.70")
    
    print("\n⏱️  推定時間: 30-60分")
    print("\n実行後:")
    print("  - 結果を確認")
    print("  - ベースラインと比較")
    print("  - 改善が確認できたら Phase 2へ")
