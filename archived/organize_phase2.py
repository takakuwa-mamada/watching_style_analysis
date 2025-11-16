"""
リポジトリ整理 Phase 2: 残りのファイルを整理
"""

import os
import shutil
from pathlib import Path

def organize_remaining_files():
    """残りのファイルを整理"""
    
    print("="*80)
    print("Phase 2: 残りのファイル整理")
    print("="*80)
    print()
    
    moves = []
    
    # ===== scripts/ に移動: 現在使用中の分析スクリプト =====
    active_scripts = [
        'analyze_emotional_expression.py',
        'analyze_engagement_patterns.py',
        'analyze_cultural_similarity.py',
        'generate_comprehensive_report.py',
        'improve_statistical_analysis.py',
        'create_paper_figures.py',
    ]
    
    for script in active_scripts:
        if os.path.exists(script):
            moves.append((script, f'scripts/{script}', 'Active Script'))
    
    # ===== docs/ に移動: 現在有効なドキュメント =====
    current_docs = [
        'NEW_FEATURES_SUMMARY.md',
        'FINAL_RESULTS_REPORT.md',
        'FINAL_ANALYSIS.md',
        'FINAL_SUMMARY.md',
        'FIGURE_EXPLANATIONS.md',
    ]
    
    for doc in current_docs:
        if os.path.exists(doc):
            moves.append((doc, f'docs/{doc}', 'Documentation'))
    
    # ===== legacy/ に移動: 古いプラン・レポート =====
    old_reports = [
        'NEXT_ACTIONS.md',
        'PROBLEM_RESOLVED.md',
        'NEXT_IMPROVEMENTS.md',
        'IMPROVEMENTS_IMPLEMENTED.md',
        'PAPER_LEVEL_ROADMAP.md',
        'STEP_BY_STEP_IMPROVEMENT.md',
        'OPTIMAL_EXECUTION_PLAN.md',
        'IMPROVEMENTS_PLAN_NOVEMBER.md',
        'PHASE1_FAILURE_ANALYSIS.md',
        'PHASE1_6_PLAN.md',
        'PHASE2_FAILURE_ANALYSIS.md',
        'PAPER_LEVEL_PLAN.md',
    ]
    
    for report in old_reports:
        if os.path.exists(report):
            moves.append((report, f'legacy/{report}', 'Legacy Report'))
    
    # ===== legacy/ に移動: 古いスクリプト =====
    old_scripts = [
        'quick_summary.py',
        'phase1_diagnosis.py',
        'phase2_optimize.py',
        'step1_increase_max_features.py',
        'phase2_optimize_weights.py',
        'phase3_temporal_improvement.py',
        'generate_comprehensive_strategy.py',
        'quick_phase1_analysis.py',
    ]
    
    for script in old_scripts:
        if os.path.exists(script):
            moves.append((script, f'legacy/{script}', 'Legacy Script'))
    
    # ===== archived/ に移動: 整理スクリプト自体 =====
    if os.path.exists('organize_repository.py'):
        moves.append(('organize_repository.py', 'archived/organize_repository.py', 'Cleanup Script'))
    
    # 移動実行
    print("📦 Phase 2 移動計画:")
    print("-"*80)
    
    moved_count = {'Active Script': 0, 'Documentation': 0, 'Legacy Report': 0, 'Legacy Script': 0, 'Cleanup Script': 0}
    
    for src, dst, category in moves:
        try:
            if os.path.exists(src):
                if os.path.exists(dst):
                    print(f"⚠️  SKIP: {src} (already exists)")
                else:
                    shutil.move(src, dst)
                    print(f"✅ {category}: {src} -> {dst}")
                    moved_count[category] += 1
        except Exception as e:
            print(f"❌ ERROR: {src}: {e}")
    
    print()
    print("="*80)
    print("Phase 2 完了!")
    print("="*80)
    print()
    
    print("📊 Phase 2 移動統計:")
    for category, count in moved_count.items():
        if count > 0:
            print(f"  {category}: {count} files")
    print(f"\n  Total: {sum(moved_count.values())} files moved")
    print()
    
    # 現在のルート確認
    print("📁 現在のルートディレクトリ:")
    print("-"*80)
    root_files = []
    for item in os.listdir('.'):
        if os.path.isfile(item):
            root_files.append(item)
    
    if root_files:
        for f in sorted(root_files):
            print(f"  {f}")
    else:
        print("  (ファイルなし - フォルダのみ)")
    
    print()
    print("✅ ルートディレクトリが非常にスッキリしました!")

if __name__ == '__main__':
    organize_remaining_files()
