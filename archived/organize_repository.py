"""
リポジトリ整理スクリプト

目的:
1. 機能ごとにフォルダ分け
2. 使っていないファイル(バックアップ、診断用)を archived/ へ移動
3. 重要なファイルのみルートに残す
4. 見通しの良い構造に再編成
"""

import os
import shutil
from pathlib import Path

def organize_repository():
    """リポジトリを整理"""
    
    base_dir = Path('.')
    
    # 新しいフォルダ構造
    folders = {
        'scripts': '分析スクリプト(現在使用中)',
        'docs': '論文関連ドキュメント',
        'archived': '過去のバックアップ・診断ファイル',
        'legacy': '旧バージョンの分析',
    }
    
    # フォルダ作成
    for folder in folders.keys():
        os.makedirs(folder, exist_ok=True)
    
    print("="*80)
    print("リポジトリ整理開始")
    print("="*80)
    print()
    
    # 移動計画
    moves = []
    
    # ===== 現在使用中のスクリプト (scripts/) =====
    active_scripts = [
        'analyze_football_only.py',
        'improve_statistical_analysis_football_only.py',
        'create_sport_confounding_comparison.py',
        'select_paper_figures.py',
        'event_comparison.py',
    ]
    
    for script in active_scripts:
        if os.path.exists(script):
            moves.append((script, f'scripts/{script}', 'Active'))
    
    # ===== 論文関連ドキュメント (docs/) =====
    paper_docs = [
        'PAPER_SUBMISSION_SCHEDULE.md',
        'RESULTS_SECTION_4_1_DRAFT.md',
        'FIGURE_SELECTION_REPORT.md',
        '80_PERCENT_ACHIEVEMENT_REPORT.md',
        'SPORT_CONFOUNDING_ANALYSIS_REPORT.md',
        'FINAL_ACADEMIC_REPORT.md',
        'CONFERENCE_STRATEGY.md',
    ]
    
    for doc in paper_docs:
        if os.path.exists(doc):
            moves.append((doc, f'docs/{doc}', 'Paper'))
    
    # ===== アーカイブ: バックアップファイル (archived/) =====
    backup_files = [
        'event_comparison_backup_before_step1.py',
        'event_comparison_backup_phase1.py',
        'event_comparison_backup_phase2.py',
        'event_comparison_backup_phase3.py',
        'create_current_snapshot.py',
        'check_current_status.py',
    ]
    
    for backup in backup_files:
        if os.path.exists(backup):
            moves.append((backup, f'archived/{backup}', 'Backup'))
    
    # ===== アーカイブ: 診断ファイル (archived/) =====
    diagnostic_files = [
        'diagnose_phase1_failure.py',
        'diagnose_phase2_failure.py',
        'analyze_current_status.py',
        'analyze_code_parameters.py',
        'verify_phase2.py',
    ]
    
    for diag in diagnostic_files:
        if os.path.exists(diag):
            moves.append((diag, f'archived/{diag}', 'Diagnostic'))
    
    # ===== Legacy: 古い分析バージョン (legacy/) =====
    legacy_scripts = [
        'academic_analysis.py',
        'quantitative_analysis.py',
        'analyze_results.py',
        'reverse_engineer_weights.py',
        'report_optimal_weights.py',
        'compute_auto_metrics.py',
        'compare_phase1_with_baseline.py',
        'create_case_study.py',
        'create_ground_truth.py',
    ]
    
    for legacy in legacy_scripts:
        if os.path.exists(legacy):
            moves.append((legacy, f'legacy/{legacy}', 'Legacy'))
    
    # ===== Legacy: 古いレポート (legacy/) =====
    legacy_reports = [
        'SOTA_IMPLEMENTATION_PLAN.md',
        'RESULTS_ANALYSIS_FINAL.md',
        'MAJOR_IMPROVEMENTS.md',
        'IMPLEMENTATION_COMPLETE.md',
        'RESULTS_REPORT.md',
        'ACCURACY_ENHANCEMENTS.md',
        'ACCURACY_AND_NEW_FEATURES.md',
        'IMPLEMENTATION_SUMMARY.md',
        'COMPREHENSIVE_IMPROVEMENTS_PLAN.md',
        'EVENT_TO_EVENT_PLAN.md',
        'SOLUTION_SUMMARY.md',
        'CHECKLIST.md',
        'RUN_COMMANDS.md',
        'TODAY_WORK_SUMMARY.md',
        'REFACTORING_PLAN.md',
        'MODIFICATION_PLAN.md',
        'FIVE_AXIS_IMPLEMENTATION_COMPLETE.md',
        'ACCURACY_IMPROVEMENTS.md',
        'ACCURACY_IMPROVEMENT_PROPOSALS.md',
        'ALTERNATIVE_APPROACHES.md',
        'CULTURAL_ANALYSIS_PROPOSAL.md',
        'ACADEMIC_REPORT_WEIGHT_OPTIMIZATION.md',
    ]
    
    for report in legacy_reports:
        if os.path.exists(report):
            moves.append((report, f'legacy/{report}', 'Legacy Report'))
    
    # ===== Phase関連の古いスクリプト (legacy/) =====
    phase_scripts = []
    for f in os.listdir('.'):
        if f.startswith('run_phase') or f.startswith('analyze_phase'):
            if os.path.isfile(f) and f.endswith('.py'):
                phase_scripts.append(f)
    
    for phase in phase_scripts:
        moves.append((phase, f'legacy/{phase}', 'Phase Script'))
    
    # 移動実行
    print("📦 ファイル移動計画:")
    print("-"*80)
    
    moved_count = {'Active': 0, 'Paper': 0, 'Backup': 0, 'Diagnostic': 0, 'Legacy': 0, 'Legacy Report': 0, 'Phase Script': 0}
    
    for src, dst, category in moves:
        try:
            if os.path.exists(src):
                # 既に同名ファイルがある場合は上書きしない
                if os.path.exists(dst):
                    print(f"⚠️  SKIP (already exists): {src} -> {dst}")
                else:
                    shutil.move(src, dst)
                    print(f"✅ MOVED ({category}): {src} -> {dst}")
                    moved_count[category] += 1
        except Exception as e:
            print(f"❌ ERROR: {src} -> {dst}: {e}")
    
    print()
    print("="*80)
    print("整理完了!")
    print("="*80)
    print()
    print("📊 移動ファイル統計:")
    for category, count in moved_count.items():
        if count > 0:
            print(f"  {category}: {count} files")
    print()
    print(f"  Total: {sum(moved_count.values())} files moved")
    print()
    
    # 新しい構造の説明
    print("📁 新しいフォルダ構造:")
    print("-"*80)
    print("""
watching_style_analysis/
├── scripts/                    # 現在使用中の分析スクリプト
│   ├── analyze_football_only.py
│   ├── improve_statistical_analysis_football_only.py
│   ├── create_sport_confounding_comparison.py
│   ├── select_paper_figures.py
│   └── event_comparison.py
│
├── docs/                       # 論文関連ドキュメント
│   ├── PAPER_SUBMISSION_SCHEDULE.md
│   ├── RESULTS_SECTION_4_1_DRAFT.md
│   ├── FIGURE_SELECTION_REPORT.md
│   ├── 80_PERCENT_ACHIEVEMENT_REPORT.md
│   ├── SPORT_CONFOUNDING_ANALYSIS_REPORT.md
│   └── CONFERENCE_STRATEGY.md
│
├── legacy/                     # 旧バージョンの分析・レポート
│   ├── (古い分析スクリプト)
│   └── (古いレポート)
│
├── archived/                   # バックアップ・診断ファイル
│   ├── (バックアップファイル)
│   └── (診断ファイル)
│
├── output/                     # 分析結果・図表 (既存)
├── input/                      # 入力データ (既存)
├── chat_sort.py               # ユーティリティ (ルートに残す)
└── README.md                  # プロジェクト説明 (作成推奨)
    """)
    print()
    print("✅ ルートディレクトリがスッキリしました!")
    print("💡 次のステップ: README.md を作成して、プロジェクト全体を説明しましょう")

def main():
    organize_repository()

if __name__ == '__main__':
    main()
