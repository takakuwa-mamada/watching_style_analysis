# Phase 0: 現状の完全把握
# Step 0.1: 現在のパフォーマンスのスナップショットを作成

import pandas as pd
import json
from pathlib import Path
from datetime import datetime

def snapshot_current_state():
    """現状のスナップショットを作成"""
    
    print("="*60)
    print("Creating Baseline Performance Snapshot")
    print("="*60)
    
    snapshot = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "version": "baseline",
        "description": "Initial state before any optimizations",
        "data": {}
    }
    
    # 1. 結果データの読み込み
    pairs_file = Path('output/event_to_event_pairs.csv')
    
    if not pairs_file.exists():
        print(f"❌ File not found: {pairs_file}")
        print("   Please run event_comparison.py first.")
        return None
    
    print(f"\n[1/7] Loading data from {pairs_file}...")
    df = pd.read_csv(pairs_file)
    print(f"✅ Loaded {len(df)} event pairs")
    
    # 2. 基本統計
    print("\n[2/7] Computing basic statistics...")
    snapshot["data"]["basic_stats"] = {
        "total_pairs": len(df),
        "avg_similarity": float(df['combined_score'].mean()),
        "max_similarity": float(df['combined_score'].max()),
        "min_similarity": float(df['combined_score'].min()),
        "std_similarity": float(df['combined_score'].std()),
        "median_similarity": float(df['combined_score'].median()),
    }
    
    print(f"  Total pairs: {len(df)}")
    print(f"  Average similarity: {df['combined_score'].mean():.3f}")
    print(f"  Max similarity: {df['combined_score'].max():.3f}")
    
    # 3. 品質分布
    print("\n[3/7] Analyzing quality distribution...")
    snapshot["data"]["quality_distribution"] = {
        "very_high": int(len(df[df['combined_score'] > 0.8])),
        "high": int(len(df[(df['combined_score'] > 0.6) & (df['combined_score'] <= 0.8)])),
        "medium": int(len(df[(df['combined_score'] > 0.4) & (df['combined_score'] <= 0.6)])),
        "low": int(len(df[df['combined_score'] <= 0.4])),
    }
    
    for quality, count in snapshot["data"]["quality_distribution"].items():
        percentage = count / len(df) * 100
        print(f"  {quality:>10}: {count:2d} ({percentage:5.1f}%)")
    
    # 4. トピック統計
    print("\n[4/7] Computing topic statistics...")
    snapshot["data"]["topic_stats"] = {
        "coverage": float(len(df[df['topic_jaccard'] > 0]) / len(df)),
        "perfect_matches": int(len(df[df['topic_jaccard'] == 1.0])),
        "avg_jaccard": float(df['topic_jaccard'].mean()),
        "max_jaccard": float(df['topic_jaccard'].max()),
        "pairs_with_topics": int(len(df[df['topic_jaccard'] > 0])),
    }
    
    print(f"  Coverage: {snapshot['data']['topic_stats']['coverage']:.1%}")
    print(f"  Perfect matches: {snapshot['data']['topic_stats']['perfect_matches']}")
    print(f"  Average Jaccard: {snapshot['data']['topic_stats']['avg_jaccard']:.3f}")
    
    # 5. コンポーネント別統計
    print("\n[5/7] Computing component statistics...")
    components = ['embedding_similarity', 'lexical_similarity', 'topic_jaccard', 'temporal_correlation']
    
    for component in components:
        if component in df.columns:
            snapshot["data"][f"{component}_stats"] = {
                "mean": float(df[component].mean()),
                "max": float(df[component].max()),
                "min": float(df[component].min()),
                "std": float(df[component].std()),
                "median": float(df[component].median()),
            }
            print(f"  {component:25s}: mean={df[component].mean():.3f}, max={df[component].max():.3f}")
    
    # 6. 相関
    print("\n[6/7] Computing correlations...")
    snapshot["data"]["correlations"] = {
        "embedding_topic": float(df['embedding_similarity'].corr(df['topic_jaccard'])),
        "embedding_lexical": float(df['embedding_similarity'].corr(df['lexical_similarity'])),
        "embedding_temporal": float(df['embedding_similarity'].corr(df['temporal_correlation'])),
        "topic_lexical": float(df['topic_jaccard'].corr(df['lexical_similarity'])),
        "topic_temporal": float(df['topic_jaccard'].corr(df['temporal_correlation'])),
        "lexical_temporal": float(df['lexical_similarity'].corr(df['temporal_correlation'])),
    }
    
    for name, value in snapshot['data']['correlations'].items():
        print(f"  {name:20s}: {value:+.3f}")
    
    # 7. Top 5ペア
    print("\n[7/7] Recording top 5 pairs...")
    top5 = df.nlargest(5, 'combined_score')
    snapshot["data"]["top5_pairs"] = []
    
    for idx, row in top5.iterrows():
        pair_info = {
            "event_A": int(row['event_A_id']),
            "event_B": int(row['event_B_id']),
            "combined_score": float(row['combined_score']),
            "embedding": float(row['embedding_similarity']),
            "topic_jaccard": float(row['topic_jaccard']),
            "lexical": float(row['lexical_similarity']),
            "temporal": float(row['temporal_correlation']),
        }
        
        # ラベルも保存
        if 'event_A_label' in row and pd.notna(row['event_A_label']):
            pair_info['label_A'] = str(row['event_A_label'])
        if 'event_B_label' in row and pd.notna(row['event_B_label']):
            pair_info['label_B'] = str(row['event_B_label'])
        
        snapshot["data"]["top5_pairs"].append(pair_info)
        
        print(f"  #{len(snapshot['data']['top5_pairs'])}: Event {row['event_A_id']:2d} ↔ {row['event_B_id']:2d} = {row['combined_score']:.3f}")
    
    # 保存
    print("\n" + "="*60)
    print("Saving snapshot...")
    print("="*60)
    
    output_dir = Path('output/snapshots')
    output_dir.mkdir(exist_ok=True)
    
    # JSON形式で保存
    json_file = output_dir / 'baseline_2025-11-10.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ JSON snapshot saved: {json_file}")
    
    # 人間が読める形式でも保存
    txt_file = output_dir / 'baseline_2025-11-10.txt'
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write("="*70 + "\n")
        f.write("Baseline Performance Snapshot (2025-11-10)\n")
        f.write("="*70 + "\n\n")
        
        f.write("[Basic Statistics]\n")
        f.write(f"  Date: {snapshot['date']}\n")
        f.write(f"  Total Pairs: {snapshot['data']['basic_stats']['total_pairs']}\n")
        f.write(f"  Average Similarity: {snapshot['data']['basic_stats']['avg_similarity']:.3f}\n")
        f.write(f"  Max Similarity: {snapshot['data']['basic_stats']['max_similarity']:.3f}\n")
        f.write(f"  Min Similarity: {snapshot['data']['basic_stats']['min_similarity']:.3f}\n")
        f.write(f"  Std Deviation: {snapshot['data']['basic_stats']['std_similarity']:.3f}\n")
        f.write(f"  Median: {snapshot['data']['basic_stats']['median_similarity']:.3f}\n\n")
        
        f.write("[Quality Distribution]\n")
        total = snapshot['data']['basic_stats']['total_pairs']
        for quality, count in snapshot['data']['quality_distribution'].items():
            percentage = count / total * 100
            f.write(f"  {quality.capitalize():>10}: {count:2d} ({percentage:5.1f}%)\n")
        
        f.write(f"\n[Topic Statistics]\n")
        f.write(f"  Coverage: {snapshot['data']['topic_stats']['coverage']:.1%} ")
        f.write(f"({snapshot['data']['topic_stats']['pairs_with_topics']}/{total} pairs)\n")
        f.write(f"  Perfect Matches: {snapshot['data']['topic_stats']['perfect_matches']}\n")
        f.write(f"  Avg Jaccard: {snapshot['data']['topic_stats']['avg_jaccard']:.3f}\n")
        f.write(f"  Max Jaccard: {snapshot['data']['topic_stats']['max_jaccard']:.3f}\n\n")
        
        f.write("[Component Statistics]\n")
        for component in components:
            if f"{component}_stats" in snapshot['data']:
                stats = snapshot['data'][f"{component}_stats"]
                f.write(f"  {component}:\n")
                f.write(f"    Mean:   {stats['mean']:.3f}\n")
                f.write(f"    Max:    {stats['max']:.3f}\n")
                f.write(f"    Min:    {stats['min']:.3f}\n")
                f.write(f"    Std:    {stats['std']:.3f}\n")
                f.write(f"    Median: {stats['median']:.3f}\n\n")
        
        f.write("[Component Correlations]\n")
        for name, value in snapshot['data']['correlations'].items():
            f.write(f"  {name:20s}: {value:+.3f}\n")
        
        f.write(f"\n[Top 5 Pairs]\n")
        for i, pair in enumerate(snapshot['data']['top5_pairs'], 1):
            f.write(f"\n  {i}. Event {pair['event_A']} ↔ Event {pair['event_B']}\n")
            f.write(f"     Combined Score: {pair['combined_score']:.3f}\n")
            f.write(f"     Components:\n")
            f.write(f"       Embedding: {pair['embedding']:.3f}\n")
            f.write(f"       Topic:     {pair['topic_jaccard']:.3f}\n")
            f.write(f"       Lexical:   {pair['lexical']:.3f}\n")
            f.write(f"       Temporal:  {pair['temporal']:.3f}\n")
            if 'label_A' in pair:
                f.write(f"     Label A: {pair['label_A']}\n")
            if 'label_B' in pair:
                f.write(f"     Label B: {pair['label_B']}\n")
    
    print(f"✅ Human-readable report saved: {txt_file}")
    
    print("\n" + "="*60)
    print("✅ Baseline snapshot creation completed!")
    print("="*60)
    
    return snapshot

if __name__ == '__main__':
    snapshot = snapshot_current_state()
    
    if snapshot:
        print("\n📊 Summary:")
        print(f"  - Total pairs: {snapshot['data']['basic_stats']['total_pairs']}")
        print(f"  - Average similarity: {snapshot['data']['basic_stats']['avg_similarity']:.3f}")
        print(f"  - Topic coverage: {snapshot['data']['topic_stats']['coverage']:.1%}")
        print(f"  - Perfect matches: {snapshot['data']['topic_stats']['perfect_matches']}")
        print("\n✅ Ready for Phase 1 improvements!")
