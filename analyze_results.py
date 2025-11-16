"""
結果出力精度向上ツール
既存のCSVファイルを読み込み、より詳細で分かりやすい形式に変換する
"""

import pandas as pd
import json
from pathlib import Path
import numpy as np

def improve_event_pairs_output():
    """
    event_to_event_pairs.csvを改善
    - ラベルの可読性向上
    - 詳細な統計情報追加
    - 論文用の表形式に変換
    """
    
    csv_path = "output/event_to_event_pairs.csv"
    if not Path(csv_path).exists():
        print(f"エラー: {csv_path} が見つかりません。")
        return
    
    df = pd.read_csv(csv_path)
    
    print("="*80)
    print("イベントペア分析レポート（論文品質）")
    print("="*80)
    print()
    
    # 基本統計
    print("## 1. 基本統計")
    print(f"総ペア数: {len(df)}")
    print(f"平均類似度: {df['combined_score'].mean():.3f}")
    print(f"最高類似度: {df['combined_score'].max():.3f}")
    print(f"最低類似度: {df['combined_score'].min():.3f}")
    print(f"標準偏差: {df['combined_score'].std():.3f}")
    print()
    
    # Top 10 ペア
    print("## 2. Top 10 類似ペア")
    print()
    top10 = df.nlargest(10, 'combined_score')
    
    for i, (idx, row) in enumerate(top10.iterrows(), 1):
        print(f"### ペア #{i}: Event {row['event_A_id']} ↔ Event {row['event_B_id']}")
        print(f"**総合類似度**: {row['combined_score']:.3f}")
        print(f"- Embedding類似度: {row['embedding_similarity']:.3f}")
        print(f"- Topic Jaccard: {row['topic_jaccard']:.3f}")
        print(f"- Lexical類似度: {row['lexical_similarity']:.3f}")
        print(f"- Temporal相関: {row['temporal_correlation']:.3f}")
        print()
        print(f"**Event A**: {row['event_A_label']}")
        print(f"  - 配信者数: {row['event_A_streams']}")
        print(f"  - コメント数: {row['event_A_comments']}")
        print()
        print(f"**Event B**: {row['event_B_label']}")
        print(f"  - 配信者数: {row['event_B_streams']}")
        print(f"  - コメント数: {row['event_B_comments']}")
        print()
        print(f"**時間差**: {row['time_diff_bins']} bins")
        print(f"**信頼度スコア**: {row['confidence_score']:.3f}")
        print()
        print("-"*80)
        print()
    
    # 類似度分布
    print("## 3. 類似度分布")
    bins = [0, 0.3, 0.5, 0.7, 0.9, 1.0]
    labels = ["0.0-0.3 (低)", "0.3-0.5 (中)", "0.5-0.7 (やや高)", "0.7-0.9 (高)", "0.9-1.0 (非常に高)"]
    df['similarity_category'] = pd.cut(df['combined_score'], bins=bins, labels=labels)
    
    category_counts = df['similarity_category'].value_counts().sort_index()
    for cat, count in category_counts.items():
        percentage = count / len(df) * 100
        print(f"{cat}: {count}ペア ({percentage:.1f}%)")
    print()
    
    # Topic Jaccard分析
    print("## 4. Topic Jaccard分析")
    topic_zero = (df['topic_jaccard'] == 0).sum()
    topic_nonzero = (df['topic_jaccard'] > 0).sum()
    topic_high = (df['topic_jaccard'] > 0.5).sum()
    topic_perfect = (df['topic_jaccard'] == 1.0).sum()
    
    print(f"topic_jaccard = 0: {topic_zero}ペア ({topic_zero/len(df)*100:.1f}%)")
    print(f"topic_jaccard > 0: {topic_nonzero}ペア ({topic_nonzero/len(df)*100:.1f}%)")
    print(f"topic_jaccard > 0.5: {topic_high}ペア ({topic_high/len(df)*100:.1f}%)")
    print(f"topic_jaccard = 1.0: {topic_perfect}ペア ({topic_perfect/len(df)*100:.1f}%)")
    print()
    
    # 完璧な一致
    if topic_perfect > 0:
        print("### 完璧なトピック一致 (topic_jaccard = 1.0)")
        perfect_matches = df[df['topic_jaccard'] == 1.0]
        for idx, row in perfect_matches.iterrows():
            print(f"- Event {row['event_A_id']} ↔ Event {row['event_B_id']}: {row['combined_score']:.3f}")
            print(f"  Label: {row['event_A_label']}")
        print()
    
    # Embedding vs Topic Jaccard相関
    print("## 5. 指標間の相関")
    corr_embed_topic = df['embedding_similarity'].corr(df['topic_jaccard'])
    corr_embed_combined = df['embedding_similarity'].corr(df['combined_score'])
    corr_topic_combined = df['topic_jaccard'].corr(df['combined_score'])
    
    print(f"Embedding ↔ Topic Jaccard: {corr_embed_topic:.3f}")
    print(f"Embedding ↔ Combined Score: {corr_embed_combined:.3f}")
    print(f"Topic Jaccard ↔ Combined Score: {corr_topic_combined:.3f}")
    print()
    
    # 論文用テーブル作成
    print("## 6. 論文用テーブル（LaTeX形式）")
    print()
    print("\\begin{table}[h]")
    print("\\centering")
    print("\\caption{Top 5 Event Pairs by Similarity}")
    print("\\begin{tabular}{|c|c|c|c|c|c|}")
    print("\\hline")
    print("Pair & Combined & Embedding & Topic & Temporal & Comments \\\\")
    print("     & Score    & Sim.      & Jaccard & Corr.   & (A/B) \\\\")
    print("\\hline")
    
    top5 = df.nlargest(5, 'combined_score')
    for _, row in top5.iterrows():
        print(f"{row['event_A_id']}-{row['event_B_id']} & "
              f"{row['combined_score']:.3f} & "
              f"{row['embedding_similarity']:.3f} & "
              f"{row['topic_jaccard']:.3f} & "
              f"{row['temporal_correlation']:.3f} & "
              f"{row['event_A_comments']}/{row['event_B_comments']} \\\\")
    
    print("\\hline")
    print("\\end{tabular}")
    print("\\end{table}")
    print()
    
    # CSV保存
    output_csv = "output/event_pairs_improved.csv"
    df_improved = df.copy()
    df_improved = df_improved.sort_values('combined_score', ascending=False)
    df_improved.to_csv(output_csv, index=False, encoding='utf-8-sig')
    print(f"✅ 改善版CSVを保存: {output_csv}")
    print()
    
    # JSON保存（構造化データ）
    output_json = "output/event_pairs_analysis.json"
    analysis = {
        "summary": {
            "total_pairs": len(df),
            "average_similarity": float(df['combined_score'].mean()),
            "max_similarity": float(df['combined_score'].max()),
            "min_similarity": float(df['combined_score'].min()),
            "std_similarity": float(df['combined_score'].std()),
        },
        "topic_jaccard_stats": {
            "zero_count": int(topic_zero),
            "nonzero_count": int(topic_nonzero),
            "high_count": int(topic_high),
            "perfect_count": int(topic_perfect),
        },
        "top_10_pairs": []
    }
    
    for _, row in top10.iterrows():
        analysis["top_10_pairs"].append({
            "event_A_id": int(row['event_A_id']),
            "event_B_id": int(row['event_B_id']),
            "combined_score": float(row['combined_score']),
            "embedding_similarity": float(row['embedding_similarity']),
            "topic_jaccard": float(row['topic_jaccard']),
            "lexical_similarity": float(row['lexical_similarity']),
            "temporal_correlation": float(row['temporal_correlation']),
            "event_A_label": str(row['event_A_label']),
            "event_B_label": str(row['event_B_label']),
        })
    
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 分析結果をJSON保存: {output_json}")
    print()
    
    print("="*80)
    print("分析完了！")
    print("="*80)

if __name__ == "__main__":
    improve_event_pairs_output()
