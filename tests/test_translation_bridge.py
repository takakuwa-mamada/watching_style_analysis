# -*- coding: utf-8 -*-
"""
Translation Bridge Test Script

utils/translation_bridge.py の動作確認テスト
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.translation_bridge import TranslationBridge


def test_language_detection():
    """言語検出テスト"""
    print("\n" + "="*70)
    print("Test 1: Language Detection")
    print("="*70)
    
    bridge = TranslationBridge()
    
    test_cases = [
        ("This is English", "en"),
        ("これは日本語です", "ja"),
        ("Esto es español", "es"),
        ("C'est français", "fr"),
        ("Das ist Deutsch", "de"),
        ("久保すごい", "ja"),
        ("visca barca", "es"),
    ]
    
    print("\n[Language Detection Results]")
    correct = 0
    for text, expected in test_cases:
        detected = bridge.detect_language(text)
        match = "✓" if detected == expected else "✗"
        print(f"  {match} '{text}' → {detected} (expected: {expected})")
        if detected == expected:
            correct += 1
    
    accuracy = correct / len(test_cases) * 100
    print(f"\nAccuracy: {correct}/{len(test_cases)} ({accuracy:.1f}%)")
    
    return accuracy > 70  # 70%以上で合格


def test_basic_translation():
    """基本的な翻訳テスト"""
    print("\n" + "="*70)
    print("Test 2: Basic Translation")
    print("="*70)
    
    bridge = TranslationBridge()
    
    # テストケース (原文, 言語, 期待される翻訳のキーワード)
    test_cases = [
        ("久保すごい", "ja", ["kubo", "great", "amazing", "awesome"]),
        ("すごいゴール", "ja", ["goal", "great", "amazing", "incredible"]),
        ("これは素晴らしい", "ja", ["wonderful", "great", "amazing", "fantastic"]),
        ("visca barca", "es", ["barca", "long", "live"]),
        ("allez les bleus", "fr", ["blues", "go", "come"]),
        ("great goal", "en", ["great", "goal"]),  # English (no translation)
    ]
    
    print("\n[Translation Results]")
    success = 0
    
    for text, lang, keywords in test_cases:
        translated = bridge.translate_to_english([text], lang)
        translated_text = translated[0].lower()
        
        # キーワードが含まれているかチェック
        match = any(kw.lower() in translated_text for kw in keywords)
        status = "✓" if match else "✗"
        
        print(f"  {status} {lang}: '{text}'")
        print(f"      → '{translated[0]}'")
        print(f"      (Expected keywords: {keywords})")
        
        if match:
            success += 1
    
    success_rate = success / len(test_cases) * 100
    print(f"\nSuccess Rate: {success}/{len(test_cases)} ({success_rate:.1f}%)")
    
    return success_rate > 60  # 60%以上で合格


def test_batch_translation():
    """バッチ翻訳テスト"""
    print("\n" + "="*70)
    print("Test 3: Batch Translation")
    print("="*70)
    
    bridge = TranslationBridge()
    
    # 複数のコメント
    ja_comments = [
        "久保すごい",
        "すごいゴール",
        "これは素晴らしい",
        "やった！",
        "最高のプレー"
    ]
    
    print(f"\n[Batch Translation] {len(ja_comments)} comments (ja → en)")
    print("\nOriginal:")
    for i, c in enumerate(ja_comments, 1):
        print(f"  {i}. {c}")
    
    # 一括翻訳
    translated = bridge.translate_to_english(ja_comments, 'ja')
    
    print("\nTranslated:")
    for i, c in enumerate(translated, 1):
        print(f"  {i}. {c}")
    
    # 全て翻訳されたかチェック
    all_translated = len(translated) == len(ja_comments)
    print(f"\n{'✓' if all_translated else '✗'} All comments translated: {len(translated)}/{len(ja_comments)}")
    
    return all_translated


def test_event_translation():
    """イベント翻訳テスト"""
    print("\n" + "="*70)
    print("Test 4: Event Translation")
    print("="*70)
    
    bridge = TranslationBridge()
    
    # サンプルイベント
    event = {
        'comments': [
            "久保すごい",
            "すごいゴール",
            "これは素晴らしい"
        ],
        'topics': [
            "久保",
            "ゴール",
            "素晴らしいプレー"
        ]
    }
    
    print("\n[Original Event]")
    print("Comments:", event['comments'])
    print("Topics:", event['topics'])
    
    # 翻訳
    translated_event = bridge.translate_event(event)
    
    print("\n[Translated Event]")
    print("Comments:", translated_event['comments'])
    print("Topics:", translated_event['topics'])
    print("Language:", translated_event['original_language'])
    print("Was Translated:", translated_event['translated'])
    
    # 翻訳されたかチェック
    success = (
        len(translated_event['comments']) == len(event['comments']) and
        len(translated_event['topics']) == len(event['topics']) and
        translated_event['original_language'] == 'ja' and
        translated_event['translated'] == True
    )
    
    print(f"\n{'✓' if success else '✗'} Event translation successful")
    
    return success


def test_cross_lingual_similarity():
    """多言語間類似度テスト"""
    print("\n" + "="*70)
    print("Test 5: Cross-Lingual Similarity")
    print("="*70)
    
    try:
        from sentence_transformers import SentenceTransformer
        
        bridge = TranslationBridge()
        bert_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        
        # 同じ内容の異なる言語イベント
        event_ja = {
            'comments': ["久保すごい", "すごいゴール"],
            'topics': ["久保", "ゴール"]
        }
        
        event_en = {
            'comments': ["Kubo is amazing", "great goal"],
            'topics': ["Kubo", "goal"]
        }
        
        print("\n[Event A - Japanese]")
        print("Comments:", event_ja['comments'])
        
        print("\n[Event B - English]")
        print("Comments:", event_en['comments'])
        
        # 類似度計算
        similarity, details = bridge.get_cross_lingual_similarity(
            event_ja, event_en, bert_model
        )
        
        print(f"\n[Similarity Score]")
        print(f"  Score: {similarity:.3f}")
        print(f"  Language A: {details['lang_A']}")
        print(f"  Language B: {details['lang_B']}")
        print(f"  Cross-lingual: {details['cross_lingual']}")
        
        # 高い類似度が期待される (同じ内容なので)
        success = similarity > 0.7
        print(f"\n{'✓' if success else '✗'} High similarity detected (>0.7)")
        
        return success
        
    except ImportError:
        print("\n[Skip] sentence_transformers not installed")
        return True  # Skip test


def run_all_tests():
    """全テストを実行"""
    print("\n" + "="*80)
    print("TRANSLATION BRIDGE - COMPREHENSIVE TEST SUITE")
    print("="*80)
    
    tests = [
        ("Language Detection", test_language_detection),
        ("Basic Translation", test_basic_translation),
        ("Batch Translation", test_batch_translation),
        ("Event Translation", test_event_translation),
        ("Cross-Lingual Similarity", test_cross_lingual_similarity),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ Error in {test_name}: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = 0
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {test_name}")
        if result:
            passed += 1
    
    total = len(results)
    pass_rate = passed / total * 100
    
    print(f"\nTotal: {passed}/{total} tests passed ({pass_rate:.1f}%)")
    
    if passed == total:
        print("\n🎉 All tests passed! Translation Bridge is ready to use.")
    elif passed >= total * 0.7:
        print("\n⚠️  Most tests passed. Translation Bridge is functional but may have issues.")
    else:
        print("\n❌ Multiple tests failed. Please check the implementation.")
    
    return passed == total


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
