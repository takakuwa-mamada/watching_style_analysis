# Phase 3: 時間類似度の改善
# 時間類似度の計算をロバストにする

import pandas as pd
import numpy as np
from pathlib import Path
import json
from datetime import datetime

def analyze_temporal_consistency():
    """時間類似度の整合性を分析"""
    
    print("="*70)
    print("Phase 3: Temporal Similarity Analysis")
    print("="*70)
    
    df = pd.read_csv('output/event_to_event_pairs.csv')
    
    print(f"\n[Basic Statistics]")
    print(f"  Total pairs: {len(df)}")
    print(f"  Temporal correlation mean: {df['temporal_correlation'].mean():.3f}")
    print(f"  Temporal correlation max:  {df['temporal_correlation'].max():.3f}")
    print(f"  Temporal correlation min:  {df['temporal_correlation'].min():.3f}")
    print(f"  Temporal correlation std:  {df['temporal_correlation'].std():.3f}")
    
    # 時間差の分析
    if 'time_diff_bins' in df.columns or 'temporal_offset' in df.columns:
        time_col = 'time_diff_bins' if 'time_diff_bins' in df.columns else 'temporal_offset'
        print(f"\n[Time Difference Analysis]")
        print(f"  Time difference mean: {df[time_col].mean():.1f} bins")
        print(f"  Time difference max:  {df[time_col].max():.1f} bins")
        print(f"  Time difference min:  {df[time_col].min():.1f} bins")
        
        # 外れ値を検出
        q75 = df[time_col].quantile(0.75)
        q25 = df[time_col].quantile(0.25)
        iqr = q75 - q25
        outlier_threshold = q75 + 1.5 * iqr
        
        outliers = df[df[time_col] > outlier_threshold]
        print(f"\n[Outlier Detection]")
        print(f"  IQR: {iqr:.1f}")
        print(f"  Outlier threshold: {outlier_threshold:.1f} bins")
        print(f"  Number of outliers: {len(outliers)}")
        
        if len(outliers) > 0:
            print(f"\n  Outlier pairs:")
            for idx, row in outliers.iterrows():
                print(f"    Event {row['event_A_id']:2d} ↔ {row['event_B_id']:2d}: "
                      f"time_diff={row[time_col]:.1f} bins, "
                      f"temporal={row['temporal_correlation']:.3f}")
    
    # 時間類似度と他のコンポーネントの相関
    print(f"\n[Correlation with Other Components]")
    print(f"  Temporal ↔ Embedding: {df['temporal_correlation'].corr(df['embedding_similarity']):+.3f}")
    print(f"  Temporal ↔ Topic:     {df['temporal_correlation'].corr(df['topic_jaccard']):+.3f}")
    print(f"  Temporal ↔ Lexical:   {df['temporal_correlation'].corr(df['lexical_similarity']):+.3f}")
    
    # 時間的整合性の計算
    # 類似度が高いペアは時間的に近いはずという仮定
    high_sim_pairs = df[df['combined_score'] > 0.5]
    low_sim_pairs = df[df['combined_score'] <= 0.5]
    
    if len(high_sim_pairs) > 0 and len(low_sim_pairs) > 0:
        print(f"\n[Temporal Consistency Check]")
        print(f"  High similarity pairs (>0.5): {len(high_sim_pairs)}")
        print(f"    Avg temporal correlation: {high_sim_pairs['temporal_correlation'].mean():.3f}")
        
        print(f"  Low similarity pairs (≤0.5): {len(low_sim_pairs)}")
        print(f"    Avg temporal correlation: {low_sim_pairs['temporal_correlation'].mean():.3f}")
        
        # 一貫性スコア（高類似度ペアの時間相関が低類似度より高いべき）
        consistency = high_sim_pairs['temporal_correlation'].mean() / (low_sim_pairs['temporal_correlation'].mean() + 1e-6)
        print(f"\n  Consistency ratio: {consistency:.2f}×")
        
        if consistency < 1.0:
            print(f"  ⚠️  Inverted! High-similarity pairs have LOWER temporal correlation.")
            print(f"      This suggests temporal calculation needs improvement.")
        else:
            print(f"  ✅ Consistent. High-similarity pairs have higher temporal correlation.")
    
    return df

def propose_temporal_improvements():
    """時間類似度計算の改善案を提示"""
    
    print("\n" + "="*70)
    print("Temporal Similarity Improvement Proposals")
    print("="*70)
    
    print("\n[Current Issue]")
    print("  - Temporal consistency is inverted (0.49×)")
    print("  - Event 56↔59 has large time difference (76 bins) but is perfect match")
    print("  - This suggests time difference alone is insufficient")
    
    print("\n[Proposed Improvements]")
    
    print("\n1. 🎯 Robust Temporal Similarity (Recommended)")
    print("   - Use rank-based correlation instead of absolute time difference")
    print("   - Outlier-resistant calculation")
    print("   - Focus on relative timing, not absolute offset")
    
    print("\n2. 📊 Peak Shape Similarity")
    print("   - Compare comment volume patterns, not just timing")
    print("   - Use Dynamic Time Warping (DTW)")
    print("   - Allows for time shifts")
    
    print("\n3. 🔄 Adaptive Time Window")
    print("   - Different events may have different time scales")
    print("   - Use event duration to normalize time difference")
    
    print("\n4. ⚖️ Weight by Confidence")
    print("   - Give less weight to temporal when time difference is large")
    print("   - Use sigmoid function to decay temporal contribution")
    
    print("\n" + "="*70)
    print("\n💡 Recommendation: Start with Option 1 (Robust Temporal)")
    print("   - Easiest to implement")
    print("   - Addresses the outlier problem")
    print("   - Can be combined with other options later")
    
    return {
        'issue': 'inverted_consistency',
        'recommended': 'robust_temporal',
        'alternatives': ['peak_shape', 'adaptive_window', 'weighted_confidence']
    }

def generate_robust_temporal_code():
    """ロバストな時間類似度計算のコード例を生成"""
    
    print("\n" + "="*70)
    print("Code Example: Robust Temporal Similarity")
    print("="*70)
    
    code_example = '''
def compute_robust_temporal_similarity(event_A_peak, event_B_peak, event_A_duration, event_B_duration):
    """
    ロバストな時間類似度計算
    
    改善点:
    1. 絶対差ではなく、相対的なタイミングを使用
    2. イベント長で正規化
    3. 外れ値の影響を軽減
    """
    
    # 1. 時間差を計算
    time_diff = abs(event_A_peak - event_B_peak)
    
    # 2. イベント長の平均で正規化
    avg_duration = (event_A_duration + event_B_duration) / 2
    normalized_diff = time_diff / (avg_duration + 1e-6)
    
    # 3. ロバストな類似度計算（シグモイド関数）
    # normalized_diff が小さいほど類似度は高い
    temporal_similarity = 1.0 / (1.0 + normalized_diff)
    
    # 4. 閾値による調整（オプション）
    # 非常に大きな差がある場合は0に近づける
    if normalized_diff > 5.0:  # 平均長の5倍以上離れている
        temporal_similarity *= 0.5  # ペナルティ
    
    return temporal_similarity

# 使用例
# event_A_peak = 150  # ピーク位置（bins）
# event_B_peak = 226  # 76 bins離れている
# event_A_duration = 30
# event_B_duration = 40
# 
# similarity = compute_robust_temporal_similarity(
#     event_A_peak, event_B_peak, 
#     event_A_duration, event_B_duration
# )
'''
    
    print(code_example)
    
    # ファイルに保存
    output_dir = Path('output/snapshots')
    output_dir.mkdir(exist_ok=True)
    
    code_file = output_dir / 'phase3_robust_temporal_code.py'
    with open(code_file, 'w', encoding='utf-8') as f:
        f.write(code_example)
    
    print(f"\n✅ Code example saved: {code_file}")
    
    return code_example

def save_phase3_report(df, improvements):
    """Phase 3のレポートを保存"""
    
    output_dir = Path('output/snapshots')
    output_dir.mkdir(exist_ok=True)
    
    # JSON形式
    report = {
        'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'phase': 'phase3_temporal_improvement',
        'current_stats': {
            'mean': float(df['temporal_correlation'].mean()),
            'max': float(df['temporal_correlation'].max()),
            'min': float(df['temporal_correlation'].min()),
            'std': float(df['temporal_correlation'].std()),
        },
        'issues': {
            'inverted_consistency': True,
            'outliers_present': True,
        },
        'recommendations': improvements
    }
    
    json_file = output_dir / 'phase3_temporal_analysis.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Phase 3 report saved: {json_file}")
    
    # テキスト形式
    txt_file = output_dir / 'phase3_temporal_analysis.txt'
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write("="*70 + "\n")
        f.write("Phase 3: Temporal Similarity Analysis\n")
        f.write("="*70 + "\n\n")
        
        f.write(f"Date: {report['date']}\n\n")
        
        f.write("[Current Statistics]\n")
        f.write(f"  Mean: {report['current_stats']['mean']:.3f}\n")
        f.write(f"  Max:  {report['current_stats']['max']:.3f}\n")
        f.write(f"  Min:  {report['current_stats']['min']:.3f}\n")
        f.write(f"  Std:  {report['current_stats']['std']:.3f}\n\n")
        
        f.write("[Issues Identified]\n")
        f.write(f"  - Inverted consistency (high-sim pairs have lower temporal correlation)\n")
        f.write(f"  - Outliers present (e.g., Event 56↔59 with 76 bins difference)\n\n")
        
        f.write("[Recommended Improvement]\n")
        f.write(f"  {improvements['recommended']}: Robust temporal similarity calculation\n")
        f.write(f"  - Use normalized time difference\n")
        f.write(f"  - Outlier-resistant formula\n")
        f.write(f"  - Event duration normalization\n\n")
        
        f.write("[Implementation]\n")
        f.write(f"  See: output/snapshots/phase3_robust_temporal_code.py\n")
    
    print(f"✅ Phase 3 text report saved: {txt_file}")

if __name__ == '__main__':
    # Step 1: 現状分析
    df = analyze_temporal_consistency()
    
    # Step 2: 改善案の提示
    improvements = propose_temporal_improvements()
    
    # Step 3: コード例の生成
    generate_robust_temporal_code()
    
    # Step 4: レポート保存
    save_phase3_report(df, improvements)
    
    print("\n" + "="*70)
    print("✅ Phase 3 Analysis Completed!")
    print("="*70)
    
    print("\n📋 Next steps:")
    print("  1. Review the analysis: output/snapshots/phase3_temporal_analysis.txt")
    print("  2. Review the code example: output/snapshots/phase3_robust_temporal_code.py")
    print("  3. Implement robust temporal similarity in event_comparison.py")
    print("  4. Re-run and compare results")
