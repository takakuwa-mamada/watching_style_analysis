"""
言語別比較の簡易版 - サンプリングで高速化
Quick Language-based Comparison with Sampling

目的:
- 全コメントではなくサンプリングで高速に言語分布を把握
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
import io

# Windows PowerShellの文字化け対策
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# langdetectをインポート
try:
    from langdetect import detect, DetectorFactory
    DetectorFactory.seed = 0
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False
    print("⚠️ langdetectがインストールされていません")

# データディレクトリ
DATA_DIR = Path(r"G:\マイドライブ\大学\4年\ゼミ\watching_style_analysis\data\football")
OUTPUT_DIR = Path(r"G:\マイドライブ\大学\4年\ゼミ\watching_style_analysis\output\language_quick_check")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 試合フォルダ（日本語名）
MATCHES = {
    "Real_Madrid_vs_Barcelona": "レアルマドリードvsバルセロナ",
    "Brazil_vs_Japan": "ブラジルvs日本",
    "Brighton_vs_Man_City": "ブライトンvsマンチェスターシティ",
    "Leeds_vs_Spurs": "リーズユナイテッドvsスパーズ",
    "Real_Sociedad_vs_Real_Madrid": "レアルソシエダvsレアルマドリード",
    "PSG_vs_Inter_Miami": "パリサンジェルマンvsインテルマイアミ"
}

def detect_language(text):
    """言語検出"""
    if not LANGDETECT_AVAILABLE or pd.isna(text) or len(str(text).strip()) < 3:
        return 'unknown'
    try:
        detected = detect(str(text))
        lang_map = {
            'ja': '日本語', 'en': '英語', 'es': 'スペイン語',
            'pt': 'ポルトガル語', 'hi': 'ヒンディー語', 
            'ar': 'アラビア語', 'fr': 'フランス語'
        }
        return lang_map.get(detected, detected)
    except:
        return 'unknown'

def quick_language_check(match_jp, sample_size=1000):
    """高速言語チェック（サンプリング）"""
    folder_path = DATA_DIR / match_jp
    
    csv_files = list(folder_path.glob("*.csv"))
    if not csv_files:
        return None
    
    results = []
    
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file, encoding='utf-8')
            
            if 'message' in df.columns:
                df.rename(columns={'message': 'comment'}, inplace=True)
            
            if 'comment' not in df.columns or len(df) == 0:
                continue
            
            # サンプリング
            n_sample = min(sample_size, len(df))
            sampled = df.sample(n=n_sample, random_state=42)
            
            # 言語検出
            print(f"  🔍 {csv_file.stem}: {len(df):,}件中{n_sample}件をサンプリング")
            sampled['language'] = sampled['comment'].apply(detect_language)
            
            # 言語分布
            lang_dist = sampled['language'].value_counts()
            
            for lang, count in lang_dist.items():
                pct = count / n_sample * 100
                total_est = int(count / n_sample * len(df))
                results.append({
                    'match': match_jp,
                    'stream': csv_file.stem,
                    'language': lang,
                    'sample_count': count,
                    'sample_percentage': pct,
                    'estimated_total': total_est,
                    'total_comments': len(df)
                })
        except Exception as e:
            print(f"  ⚠️ {csv_file.name}: {e}")
            continue
    
    return pd.DataFrame(results) if results else None

def main():
    """メイン処理"""
    print("="*80)
    print("言語別比較 簡易版 - Quick Language Check")
    print("="*80)
    
    if not LANGDETECT_AVAILABLE:
        print("\n❌ langdetectが必要です: pip install langdetect")
        return
    
    print("\n🚀 サンプリングによる高速言語検出開始\n")
    
    all_results = []
    
    for match_en, match_jp in MATCHES.items():
        print(f"\n{'='*80}")
        print(f"📂 {match_en} ({match_jp})")
        print(f"{'='*80}")
        
        result_df = quick_language_check(match_jp, sample_size=1000)
        
        if result_df is not None:
            all_results.append(result_df)
            
            # 試合ごとのサマリー
            print(f"\n  📊 言語分布:")
            for lang in result_df['language'].unique():
                lang_data = result_df[result_df['language'] == lang]
                total_est = lang_data['estimated_total'].sum()
                total_comments = result_df['total_comments'].sum()
                pct = total_est / total_comments * 100
                print(f"    {lang}: 推定{total_est:,}件 ({pct:.1f}%)")
    
    if not all_results:
        print("\n❌ データが読み込めませんでした")
        return
    
    # 全結果を結合
    combined_df = pd.concat(all_results, ignore_index=True)
    
    # 保存
    output_csv = OUTPUT_DIR / "quick_language_check_results.csv"
    combined_df.to_csv(output_csv, index=False, encoding='utf-8-sig')
    print(f"\n✓ 結果保存: {output_csv}")
    
    # 全体サマリー
    print("\n" + "="*80)
    print("全体サマリー")
    print("="*80)
    
    total_comments = combined_df['total_comments'].sum()
    print(f"\n総コメント数: {total_comments:,}件\n")
    
    for lang in combined_df['language'].unique():
        lang_data = combined_df[combined_df['language'] == lang]
        total_est = lang_data['estimated_total'].sum()
        pct = total_est / total_comments * 100
        print(f"{lang}: 推定{total_est:,}件 ({pct:.1f}%)")
    
    print("\n" + "="*80)
    print("✅ 簡易言語チェック完了")
    print("="*80)
    print("\n💡 詳細分析は analyze_language_refined.py で実行してください")

if __name__ == "__main__":
    main()
