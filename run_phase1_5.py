"""
Phase 1.5 実行スクリプト
max_df=0.95 → 1.0 に変更してTopic抽出を改善
"""

import subprocess
import sys
from datetime import datetime

print("=" * 70)
print("Phase 1.5: max_df調整による小規模イベントTopic抽出改善")
print("=" * 70)

print("\n【変更内容】")
print("  ファイル: event_comparison.py")
print("  変更1: TfidfVectorizer (line 687)")
print("    max_df=0.95 → max_df=1.0")
print("  変更2: TfidfVectorizer (line 734)")
print("    max_df=0.95 → max_df=1.0")

print("\n【期待される効果】")
print("  1. 小規模イベント（10-20コメント）でのTopic抽出成功率向上")
print("  2. 'After pruning, no terms remain' 警告の減少")
print("  3. Topic coverage: 17.9% → 30-40% (目標)")
print("  4. Combined score: 0.237 → 0.28-0.32 (目標)")

print("\n【実行時間】")
print("  予想: 30-60分")

print("\n【実行開始時刻】")
start_time = datetime.now()
print(f"  {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

print("\n" + "=" * 70)
print("event_comparison.py を実行中...")
print("=" * 70)

# event_comparison.pyを実行
result = subprocess.run([
    sys.executable,
    "event_comparison.py",
    "--folder", r"data\football\game4",
    "--pattern", "*.csv",
    "--peak-pad", "3",
    "--embedding-match-th", "0.70"
], capture_output=False, text=True)

print("\n" + "=" * 70)
print("実行完了")
print("=" * 70)

end_time = datetime.now()
duration = end_time - start_time

print(f"\n【実行終了時刻】")
print(f"  {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"\n【実行時間】")
print(f"  {duration}")

print(f"\n【Exit Code】")
print(f"  {result.returncode}")

if result.returncode == 0:
    print("\n✅ Phase 1.5実行成功！")
    print("\n次のステップ:")
    print("  1. python diagnose_phase1_failure.py を再実行して結果を確認")
    print("  2. Topic coverageが30%以上なら成功")
    print("  3. 成功ならPhase 2（重み最適化）へ進む")
else:
    print("\n❌ Phase 1.5実行失敗")
    print(f"  Exit code: {result.returncode}")
