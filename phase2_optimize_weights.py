# Phase 2: 重み係数の最適化
# Step 2: グリッドサーチで最適な重みを見つける

import pandas as pd
import numpy as np
from pathlib import Path
import json
from datetime import datetime
from itertools import product

def analyze_current_weights():
    """現在の重みを推定"""
    
    print("="*70)
    print("Phase 2: Weight Optimization")
    print("="*70)
    
    df = pd.read_csv('output/event_to_event_pairs.csv')
    
    # 完全一致ペア（Event 56↔59）を基準とする
    target_pair = df[(df['event_A_id'] == 56) & (df['event_B_id'] == 59)]
    
    if len(target_pair) == 0:
        print("❌ Target pair (Event 56↔59) not found")
        return None, None
    
    target_pair = target_pair.iloc[0]
    
    print("\n[Reference Pair: Event 56 ↔ 59 (Perfect Match)]")
    print(f"  Combined Score:  {target_pair['combined_score']:.3f}")
    print(f"  Embedding:       {target_pair['embedding_similarity']:.3f}")
    print(f"  Lexical:         {target_pair['lexical_similarity']:.3f}")
    print(f"  Topic (Jaccard): {target_pair['topic_jaccard']:.3f}")
    print(f"  Temporal:        {target_pair['temporal_correlation']:.3f}")
    
    # 現在の重みを逆算（4変数4未知数だが、近似）
    # combined = w_emb * emb + w_lex * lex + w_topic * topic + w_temp * temp
    # ここでは、相関分析から推定
    
    components = ['embedding_similarity', 'lexical_similarity', 'topic_jaccard', 'temporal_correlation']
    
    print("\n[Component Statistics (All Pairs)]")
    for comp in components:
        mean_val = df[comp].mean()
        max_val = df[comp].max()
        std_val = df[comp].std()
        print(f"  {comp:25s}: mean={mean_val:.3f}, max={max_val:.3f}, std={std_val:.3f}")
    
    # 相関分析
    print("\n[Component-Combined Score Correlations]")
    for comp in components:
        corr = df[comp].corr(df['combined_score'])
        print(f"  {comp:25s} ↔ combined: {corr:+.3f}")
    
    return df, target_pair

def grid_search_optimal_weights(df, target_pair, save_results=True):
    """グリッドサーチで最適な重みを探索"""
    
    print("\n" + "="*70)
    print("Grid Search for Optimal Weights")
    print("="*70)
    
    print("\n[Objective]")
    print("  1. Maximize score for perfect match (Event 56↔59)")
    print("  2. Maximize separation from other pairs")
    print("  3. Increase average similarity across all pairs")
    
    print("\n[Search Space]")
    print("  Embedding:  0.30 - 0.45 (step 0.05)")
    print("  Topic:      0.30 - 0.45 (step 0.05)")
    print("  Lexical:    0.05 - 0.20 (step 0.05)")
    print("  Temporal:   0.05 - 0.15 (step 0.05)")
    print("  Constraint: sum = 1.0")
    
    best_config = None
    best_score = 0
    best_separation = -999
    all_results = []
    
    total_configs = 0
    valid_configs = 0
    
    # グリッドサーチ
    print("\n⏱️  Starting grid search...")
    
    for w_emb in np.arange(0.30, 0.46, 0.05):
        for w_topic in np.arange(0.30, 0.46, 0.05):
            for w_lex in np.arange(0.05, 0.21, 0.05):
                total_configs += 1
                
                # Temporal weightを計算
                w_temp = 1.0 - w_emb - w_topic - w_lex
                
                # 制約チェック
                if w_temp < 0.05 or w_temp > 0.15:
                    continue
                
                valid_configs += 1
                
                # 各ペアのスコアを再計算
                df['new_score'] = (
                    w_emb * df['embedding_similarity'] +
                    w_lex * df['lexical_similarity'] +
                    w_topic * df['topic_jaccard'] +
                    w_temp * df['temporal_correlation']
                )
                
                # ターゲットペアのスコア
                target_score = df[
                    (df['event_A_id'] == 56) & (df['event_B_id'] == 59)
                ]['new_score'].iloc[0]
                
                # 他のペアの統計
                other_pairs = df[
                    (df['event_A_id'] != 56) | (df['event_B_id'] != 59)
                ]
                avg_other = other_pairs['new_score'].mean()
                max_other = other_pairs['new_score'].max()
                
                # 全体平均
                avg_all = df['new_score'].mean()
                
                # 分離度（ターゲットと他の最大値の差）
                separation = target_score - max_other
                
                # 結果を記録
                result = {
                    'w_embedding': round(w_emb, 2),
                    'w_lexical': round(w_lex, 2),
                    'w_topic': round(w_topic, 2),
                    'w_temporal': round(w_temp, 2),
                    'target_score': round(target_score, 4),
                    'avg_other': round(avg_other, 4),
                    'max_other': round(max_other, 4),
                    'avg_all': round(avg_all, 4),
                    'separation': round(separation, 4),
                }
                
                all_results.append(result)
                
                # 最良設定を更新（分離度を最優先）
                if separation > best_separation:
                    best_separation = separation
                    best_score = target_score
                    best_config = result.copy()
    
    print(f"✅ Grid search completed")
    print(f"  Total configurations: {total_configs}")
    print(f"  Valid configurations: {valid_configs}")
    
    if not best_config:
        print("❌ No valid configuration found")
        return None
    
    # 結果を表示
    print("\n" + "="*70)
    print("Best Configuration Found")
    print("="*70)
    
    print(f"\n[Optimal Weights]")
    print(f"  Embedding:  {best_config['w_embedding']:.2f} ({best_config['w_embedding']*100:.0f}%)")
    print(f"  Lexical:    {best_config['w_lexical']:.2f} ({best_config['w_lexical']*100:.0f}%)")
    print(f"  Topic:      {best_config['w_topic']:.2f} ({best_config['w_topic']*100:.0f}%)")
    print(f"  Temporal:   {best_config['w_temporal']:.2f} ({best_config['w_temporal']*100:.0f}%)")
    print(f"  Total:      {sum([best_config['w_embedding'], best_config['w_lexical'], best_config['w_topic'], best_config['w_temporal']]):.2f}")
    
    print(f"\n[Performance Metrics]")
    print(f"  Target pair score:     {best_config['target_score']:.4f}")
    print(f"  Other pairs avg:       {best_config['avg_other']:.4f}")
    print(f"  Other pairs max:       {best_config['max_other']:.4f}")
    print(f"  Overall average:       {best_config['avg_all']:.4f}")
    print(f"  Separation:            {best_config['separation']:.4f}")
    
    # 現在の設定と比較
    current_score = target_pair['combined_score']
    current_avg = df['combined_score'].mean()
    
    print(f"\n[Comparison with Current Weights]")
    print(f"  Current target score:  {current_score:.4f}")
    print(f"  Optimized target:      {best_config['target_score']:.4f}")
    print(f"  Improvement:           {best_config['target_score'] - current_score:+.4f}")
    print(f"")
    print(f"  Current overall avg:   {current_avg:.4f}")
    print(f"  Optimized overall avg: {best_config['avg_all']:.4f}")
    print(f"  Improvement:           {best_config['avg_all'] - current_avg:+.4f}")
    
    # 保存
    if save_results:
        output_dir = Path('output/snapshots')
        output_dir.mkdir(exist_ok=True)
        
        # ベスト設定を保存
        json_file = output_dir / 'phase2_optimized_weights.json'
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({
                'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'phase': 'phase2_weight_optimization',
                'best_weights': best_config,
                'comparison': {
                    'current_target_score': float(current_score),
                    'optimized_target_score': best_config['target_score'],
                    'target_improvement': float(best_config['target_score'] - current_score),
                    'current_avg': float(current_avg),
                    'optimized_avg': best_config['avg_all'],
                    'avg_improvement': float(best_config['avg_all'] - current_avg),
                }
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Best config saved: {json_file}")
        
        # 全結果も保存（Top 10）
        all_results_sorted = sorted(all_results, key=lambda x: x['separation'], reverse=True)
        top10_file = output_dir / 'phase2_top10_configs.json'
        with open(top10_file, 'w', encoding='utf-8') as f:
            json.dump(all_results_sorted[:10], f, indent=2)
        
        print(f"✅ Top 10 configs saved: {top10_file}")
        
        # テキストレポート
        txt_file = output_dir / 'phase2_weight_optimization.txt'
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write("Phase 2: Weight Optimization Results\n")
            f.write("="*70 + "\n\n")
            
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("[Optimal Weights]\n")
            f.write(f"  Embedding:  {best_config['w_embedding']:.2f} ({best_config['w_embedding']*100:.0f}%)\n")
            f.write(f"  Lexical:    {best_config['w_lexical']:.2f} ({best_config['w_lexical']*100:.0f}%)\n")
            f.write(f"  Topic:      {best_config['w_topic']:.2f} ({best_config['w_topic']*100:.0f}%)\n")
            f.write(f"  Temporal:   {best_config['w_temporal']:.2f} ({best_config['w_temporal']*100:.0f}%)\n\n")
            
            f.write("[Performance]\n")
            f.write(f"  Target pair (56↔59):   {best_config['target_score']:.4f}\n")
            f.write(f"  Overall average:        {best_config['avg_all']:.4f}\n")
            f.write(f"  Separation:             {best_config['separation']:.4f}\n\n")
            
            f.write("[Improvement over Current]\n")
            f.write(f"  Target score:  {current_score:.4f} → {best_config['target_score']:.4f} ({best_config['target_score'] - current_score:+.4f})\n")
            f.write(f"  Overall avg:   {current_avg:.4f} → {best_config['avg_all']:.4f} ({best_config['avg_all'] - current_avg:+.4f})\n\n")
            
            f.write("[Top 10 Configurations]\n")
            for i, config in enumerate(all_results_sorted[:10], 1):
                f.write(f"\n  {i}. Separation: {config['separation']:.4f}\n")
                f.write(f"     Weights: Emb={config['w_embedding']:.2f}, Lex={config['w_lexical']:.2f}, ")
                f.write(f"Topic={config['w_topic']:.2f}, Temp={config['w_temporal']:.2f}\n")
                f.write(f"     Target={config['target_score']:.4f}, Avg={config['avg_all']:.4f}\n")
        
        print(f"✅ Report saved: {txt_file}")
    
    return best_config

def generate_code_update_instructions(best_config):
    """コード更新の指示を生成"""
    
    print("\n" + "="*70)
    print("Code Update Instructions")
    print("="*70)
    
    print("\n[To apply these weights to event_comparison.py]")
    print("\n1. Find the line where combined_score is calculated")
    print("   (Search for: 'combined_score' or 'similarity calculation')")
    print("\n2. Update the formula to:")
    print(f"\n   combined_score = (")
    print(f"       {best_config['w_embedding']:.2f} * embedding_similarity +")
    print(f"       {best_config['w_lexical']:.2f} * lexical_similarity +")
    print(f"       {best_config['w_topic']:.2f} * topic_jaccard +")
    print(f"       {best_config['w_temporal']:.2f} * temporal_correlation")
    print(f"   )")
    
    print("\n3. Or, define weight constants at the top of the function:")
    print(f"\n   W_EMBEDDING = {best_config['w_embedding']:.2f}")
    print(f"   W_LEXICAL = {best_config['w_lexical']:.2f}")
    print(f"   W_TOPIC = {best_config['w_topic']:.2f}")
    print(f"   W_TEMPORAL = {best_config['w_temporal']:.2f}")
    
    print("\n" + "="*70)

if __name__ == '__main__':
    # Step 1: 現在の重みを分析
    df, target_pair = analyze_current_weights()
    
    if df is None or target_pair is None:
        print("\n❌ Analysis failed. Cannot proceed.")
        exit(1)
    
    # Step 2: グリッドサーチ
    print("\n" + "="*70)
    response = input("Proceed with grid search? (y/n): ")
    
    if response.lower() == 'y':
        best_config = grid_search_optimal_weights(df, target_pair, save_results=True)
        
        if best_config:
            generate_code_update_instructions(best_config)
            
            print("\n✅ Phase 2 completed!")
            print("\n📋 Next steps:")
            print("  1. Review the optimized weights in: output/snapshots/phase2_weight_optimization.txt")
            print("  2. Update event_comparison.py with the new weights")
            print("  3. Re-run event_comparison.py to see the improvement")
            print("  4. Compare results with baseline and Step 1")
    else:
        print("\n⏸️  Grid search skipped.")
