"""
Phase 1 & 1.5 失敗の根本原因分析
ターミナル出力から重要な発見
"""

print("=" * 80)
print("Phase 1 & 1.5 失敗の根本原因分析")
print("=" * 80)

print("\n【Phase 1.5 実行確認】")
print("  max_df: 0.95 → 1.0 に変更済み（2箇所）")
print("  実行時間: 正常完了")
print("  結果: Combined score 0.237（変化なし）")

print("\n【ターミナル出力から発見した重要な事実】")
print("\n1. **N-gram抽出は成功している**")
print("   例:")
print("   - [N-gram抽出] Top 5: ['韓国発狂', '韓国涙目', '韓国', ...]")
print("   - [N-gram抽出] Top 5: ['ヘンリー', 'ヘンリーこえー', ...]")
print("   - [N-gram抽出] Top 5: ['森保', '森保の名将狩り', ...]")
print("   → N-gram抽出自体は正常に動作")

print("\n2. **Topic数が異常**")
print("   小規模イベント（10-20コメント）のTopic数:")
print("   - Event: 21 comments, 30 topics ← 異常に多い")
print("   - Event: 22 comments, 30 topics")
print("   - Event: 15 comments, 30 topics")
print("   - Event: 12 comments, 30 topics")
print("   → 30 topicsは上限値（max_features=3000の影響ではない）")

print("\n3. **正常なTopic数のイベントも存在**")
print("   大規模イベント:")
print("   - Event: 42 comments, 6 topics ← 正常")
print("   - Event: 41 comments, 7 topics")
print("   - Event: 31 comments, 3 topics")
print("   - Event: 30 comments, 1 topics")
print("   → コメント数が多いと適切なTopic数に収束")

print("\n4. **Topic抽出の問題点**")
print("   - 'After pruning, no terms remain' 警告は見られない（Phase 1.5で解決）")
print("   - しかし、小規模イベントで30 topicsという上限値が出ている")
print("   - これは「Topic抽出できない」のではなく「Topic数を制限している」")

print("\n【根本原因の特定】")
print("\n❌ **原因は max_df ではなかった！**")
print("\n✅ **真の原因: Topic数の上限設定（30）が小規模イベントに不適切**")
print("\n詳細:")
print("  - コードのどこかで 'n_topics = min(実際のtopic数, 30)' のような制限がある")
print("  - 小規模イベント（10-20コメント）では本来1-5 topicsが適切")
print("  - しかし強制的に30 topicsまで抽出しようとする")
print("  - 結果: 無意味なノイズがtopicとして含まれる")
print("  - Topic Jaccard計算時に一致しない（82.1%がtopic_jaccard=0）")

print("\n【コード内の問題箇所を特定する必要がある】")
print("  検索キーワード:")
print("    - 'n_topics'")
print("    - '30'（ハードコードされた上限値）")
print("    - 'min(', 'max('（制限ロジック）")
print("    - Topic抽出関連の関数")

print("\n【次のステップ】")
print("  1. event_comparison.py内でTopic数制限のコードを検索")
print("  2. 上限30を削除、または動的に調整（コメント数の1/4など）")
print("  3. Phase 1.6として再実行")
print("  4. 期待: Topic coverage 17.9% → 35-45%")

print("\n" + "=" * 80)
print("診断完了 - 真の原因を特定")
print("=" * 80)
