# Phase 1: 最小変更での効果測定
# Step 1: max_features を2000から3000に増やす

import shutil
from pathlib import Path
import subprocess
import json
import pandas as pd
from datetime import datetime

def step1_increase_max_features():
    """Step 1: max_features を3000に増やす"""
    
    print("="*70)
    print("Phase 1, Step 1: Increase max_features from 2000 to 3000")
    print("="*70)
    print("\n目的: N-gram抽出の特徴量を増やして、トピックカバレッジを改善")
    print("予想される改善: トピック一致率 17.9% → 25-30%")
    print("="*70)
    
    # 1. バックアップ
    print("\n[1/6] Creating backup...")
    backup_file = 'event_comparison_backup_before_step1.py'
    
    try:
        shutil.copy('event_comparison.py', backup_file)
        print(f"✅ Backup created: {backup_file}")
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return False
    
    # 2. パラメータ変更
    print("\n[2/6] Modifying max_features parameter...")
    
    try:
        with open('event_comparison.py', 'r', encoding='utf-8') as f:
            code = f.read()
        
        # max_features=2000 を max_features=3000 に変更
        # line 686付近の最初の出現のみを変更
        modified_code = code.replace(
            'max_features=2000,         # 最大2000個の特徴',
            'max_features=3000,         # 最大3000個の特徴（Step 1で拡張）'
        )
        
        # 変更箇所を確認
        if modified_code != code:
            print("✅ Found target line:")
            print("   Before: max_features=2000,         # 最大2000個の特徴")
            print("   After:  max_features=3000,         # 最大3000個の特徴（Step 1で拡張）")
            
            with open('event_comparison.py', 'w', encoding='utf-8') as f:
                f.write(modified_code)
            
            print("✅ File updated successfully")
        else:
            print("⚠️  Target string not found in code")
            print("   Manual check required")
            return False
            
    except Exception as e:
        print(f"❌ Modification failed: {e}")
        return False
    
    # 3. 変更の確認
    print("\n[3/6] Verifying modification...")
    with open('event_comparison.py', 'r', encoding='utf-8') as f:
        modified_lines = f.readlines()
    
    found_modification = False
    for i, line in enumerate(modified_lines[680:700], start=681):
        if 'max_features=3000' in line:
            print(f"✅ Verified at line {i}:")
            print(f"   {line.strip()}")
            found_modification = True
            break
    
    if not found_modification:
        print("⚠️  Modification not verified")
        return False
    
    # 4. 実行準備
    print("\n[4/6] Ready to re-run event_comparison.py")
    print("\n⏱️  推定実行時間: 30-60分")
    print("\nCommand to execute:")
    print('  python event_comparison.py --folder "data\\football\\game4" --pattern "*.csv" --peak-pad 3 --embedding-match-th 0.70')
    
    # 実行するかどうか確認
    print("\n" + "="*70)
    response = input("Execute now? (y/n): ")
    
    if response.lower() != 'y':
        print("\n⏸️  Execution postponed.")
        print("   Run manually when ready.")
        return False
    
    # 5. 実行
    print("\n[5/6] Executing event_comparison.py...")
    print("⏱️  This will take 30-60 minutes. Please wait...\n")
    
    try:
        result = subprocess.run(
            [
                'python', 'event_comparison.py',
                '--folder', 'data\\football\\game4',
                '--pattern', '*.csv',
                '--peak-pad', '3',
                '--embedding-match-th', '0.70'
            ],
            capture_output=False,  # リアルタイムで出力を表示
            text=True
        )
        
        if result.returncode == 0:
            print("\n✅ Execution completed successfully")
        else:
            print(f"\n⚠️  Execution failed with code {result.returncode}")
            return False
            
    except KeyboardInterrupt:
        print("\n⚠️  Execution interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False
    
    # 6. 結果比較
    print("\n[6/6] Comparing results with baseline...")
    compare_results_step1()
    
    return True

def compare_results_step1():
    """Step 1の結果をベースラインと比較"""
    
    print("\n" + "="*70)
    print("Results Comparison: Baseline vs Step 1")
    print("="*70)
    
    # Baselineを読み込み
    baseline_file = Path('output/snapshots/baseline_2025-11-10.json')
    if not baseline_file.exists():
        print("⚠️  Baseline snapshot not found.")
        print("   Please run create_current_snapshot.py first.")
        return
    
    with open(baseline_file, 'r', encoding='utf-8') as f:
        baseline = json.load(f)
    
    # Step 1結果を読み込み
    pairs_file = Path('output/event_to_event_pairs.csv')
    if not pairs_file.exists():
        print(f"❌ Result file not found: {pairs_file}")
        return
    
    df_new = pd.read_csv(pairs_file)
    
    # Step 1の統計を計算
    step1_stats = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "version": "step1_max_features_3000",
        "changes": ["max_features: 2000 → 3000 (line 686)"],
        "data": {
            "total_pairs": len(df_new),
            "avg_similarity": float(df_new['combined_score'].mean()),
            "max_similarity": float(df_new['combined_score'].max()),
            "std_similarity": float(df_new['combined_score'].std()),
            "topic_coverage": float(len(df_new[df_new['topic_jaccard'] > 0]) / len(df_new)),
            "perfect_matches": int(len(df_new[df_new['topic_jaccard'] == 1.0])),
            "avg_topic_jaccard": float(df_new['topic_jaccard'].mean()),
            "high_quality_pairs": int(len(df_new[df_new['combined_score'] > 0.7])),
        }
    }
    
    # 比較表を表示
    print(f"\n{'Metric':<35} | {'Baseline':>10} | {'Step 1':>10} | {'Change':>10}")
    print("-"*75)
    
    # 平均類似度
    baseline_avg = baseline['data']['basic_stats']['avg_similarity']
    step1_avg = step1_stats['data']['avg_similarity']
    change = step1_avg - baseline_avg
    change_pct = (change / baseline_avg * 100) if baseline_avg != 0 else 0
    print(f"{'Average Similarity':<35} | {baseline_avg:>10.3f} | {step1_avg:>10.3f} | {change:+10.3f} ({change_pct:+.1f}%)")
    
    # トピックカバレッジ
    baseline_cov = baseline['data']['topic_stats']['coverage']
    step1_cov = step1_stats['data']['topic_coverage']
    change = step1_cov - baseline_cov
    change_pct = (change / baseline_cov * 100) if baseline_cov != 0 else 0
    print(f"{'Topic Coverage':<35} | {baseline_cov:>10.1%} | {step1_cov:>10.1%} | {change:+10.1%} ({change_pct:+.1f}%)")
    
    # 完全一致
    baseline_perfect = baseline['data']['topic_stats']['perfect_matches']
    step1_perfect = step1_stats['data']['perfect_matches']
    change = step1_perfect - baseline_perfect
    print(f"{'Perfect Matches':<35} | {baseline_perfect:>10d} | {step1_perfect:>10d} | {change:+10d}")
    
    # 平均トピックJaccard
    baseline_jaccard = baseline['data']['topic_stats']['avg_jaccard']
    step1_jaccard = step1_stats['data']['avg_topic_jaccard']
    change = step1_jaccard - baseline_jaccard
    change_pct = (change / baseline_jaccard * 100) if baseline_jaccard != 0 else 0
    print(f"{'Average Topic Jaccard':<35} | {baseline_jaccard:>10.3f} | {step1_jaccard:>10.3f} | {change:+10.3f} ({change_pct:+.1f}%)")
    
    # 高品質ペア数
    baseline_high = baseline['data']['quality_distribution']['very_high']
    step1_high = step1_stats['data']['high_quality_pairs']
    change = step1_high - baseline_high
    print(f"{'High-Quality Pairs (>0.7)':<35} | {baseline_high:>10d} | {step1_high:>10d} | {change:+10d}")
    
    # 評価
    print("\n" + "="*70)
    print("📊 Step 1 Evaluation:")
    print("="*70)
    
    improvements = 0
    
    if step1_avg > baseline_avg:
        print("✅ Average similarity improved")
        improvements += 1
    else:
        print("⚠️  Average similarity decreased or unchanged")
    
    if step1_cov > baseline_cov:
        improvement_rate = (step1_cov - baseline_cov) / baseline_cov * 100
        print(f"✅ Topic coverage improved by {improvement_rate:.1f}%")
        improvements += 1
    else:
        print("⚠️  Topic coverage decreased or unchanged")
    
    if step1_perfect >= baseline_perfect:
        print(f"✅ Perfect matches: {step1_perfect} (maintained or improved)")
        improvements += 1
    else:
        print(f"⚠️  Perfect matches decreased: {baseline_perfect} → {step1_perfect}")
    
    if step1_high > baseline_high:
        print(f"✅ High-quality pairs increased: {baseline_high} → {step1_high}")
        improvements += 1
    else:
        print(f"⚠️  High-quality pairs: {step1_high} (unchanged or decreased)")
    
    print(f"\n🎯 Overall: {improvements}/4 metrics improved")
    
    # スナップショット保存
    output_dir = Path('output/snapshots')
    output_dir.mkdir(exist_ok=True)
    
    json_file = output_dir / 'step1_max_features_3000.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(step1_stats, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Step 1 snapshot saved: {json_file}")
    
    # テキストレポート
    txt_file = output_dir / 'step1_max_features_3000.txt'
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write("="*70 + "\n")
        f.write("Step 1 Results: max_features increased to 3000\n")
        f.write("="*70 + "\n\n")
        
        f.write(f"Date: {step1_stats['date']}\n")
        f.write(f"Changes: {', '.join(step1_stats['changes'])}\n\n")
        
        f.write("[Comparison with Baseline]\n")
        f.write(f"  Average Similarity:    {baseline_avg:.3f} → {step1_avg:.3f} ({change:+.3f})\n")
        f.write(f"  Topic Coverage:        {baseline_cov:.1%} → {step1_cov:.1%}\n")
        f.write(f"  Perfect Matches:       {baseline_perfect} → {step1_perfect}\n")
        f.write(f"  High-Quality Pairs:    {baseline_high} → {step1_high}\n\n")
        
        f.write(f"[Evaluation]\n")
        f.write(f"  Improvements: {improvements}/4 metrics\n")
    
    print(f"✅ Step 1 report saved: {txt_file}")
    
    print("\n" + "="*70)
    print("✅ Step 1 completed!")
    print("="*70)
    
    if improvements >= 2:
        print("\n🎉 Step 1 was successful! Ready for Step 2.")
    else:
        print("\n⚠️  Step 1 showed limited improvement. Consider alternative approaches.")

if __name__ == '__main__':
    success = step1_increase_max_features()
    
    if success:
        print("\n✅ All operations completed successfully!")
        print("\n次のステップ:")
        print("  1. 結果を確認: output/snapshots/step1_max_features_3000.txt")
        print("  2. 改善が確認できたら、Phase 2に進む")
        print("  3. 改善が不十分なら、パラメータを再調整")
    else:
        print("\n⏸️  Process incomplete. Please review and retry.")
