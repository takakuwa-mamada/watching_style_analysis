"""Noise Filter動作確認テスト"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.noise_filter import NoiseFilter

# Noise Filterインスタンス作成
nf = NoiseFilter()
print("✅ Noise Filter loaded successfully\n")

# テストケース
test_cases = [
    ("kkkkkk", True, "Noise (repetition)"),
    ("wwwwww", True, "Noise (repetition)"),
    ("laugh laugh laugh", True, "Noise (repetition)"),
    ("!!!!", True, "Noise (symbols only)"),
    ("123456", True, "Noise (numbers only)"),
    ("goal", False, "Meaningful word"),
    ("penalty kick", False, "Meaningful phrase"),
    ("Real Madrid", False, "Team name"),
    ("brasil", False, "Country name"),
    ("en sus playeras", False, "Spanish phrase"),  # 実際のデータから
]

print("=" * 60)
print("Noise Detection Test Results")
print("=" * 60)

correct = 0
total = len(test_cases)

for text, expected_noise, description in test_cases:
    result = nf.is_noise(text)
    status = "✅ PASS" if result == expected_noise else "❌ FAIL"
    correct += (result == expected_noise)
    print(f"{status} | '{text}' → {result} | {description}")

print("=" * 60)
print(f"Accuracy: {correct}/{total} ({correct/total*100:.1f}%)\n")

# N-gram filtering test
print("=" * 60)
print("N-gram Filtering Test")
print("=" * 60)

ngrams_before = [
    "kkkkkk",
    "wwww", 
    "laugh laugh",
    "goal",
    "penalty kick",
    "Real Madrid",
    "brasil",
    "!!!"
]

print(f"Before: {ngrams_before}")
ngrams_after = nf.filter_ngrams(ngrams_before)
print(f"After: {ngrams_after}")
print(f"Removed: {len(ngrams_before) - len(ngrams_after)}/{len(ngrams_before)}")

# Quality scoring test
print("\n" + "=" * 60)
print("Topic Quality Scoring Test")
print("=" * 60)

topics = [
    ["kkkkkk", "wwww", "laugh", "!!!"],
    ["goal", "penalty", "brasil", "japan"],
    ["Real Madrid", "Barcelona", "kickoff", "referee"],
]

for i, words in enumerate(topics, 1):
    quality = nf.score_topic_quality(words)
    print(f"Topic {i}: {words}")
    print(f"  Quality Score: {quality:.3f}")
    print(f"  Status: {'❌ Low' if quality < 0.3 else '⚠️ Medium' if quality < 0.6 else '✅ High'}\n")
