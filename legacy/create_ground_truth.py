"""
Ground Truth作成支援ツール
検出されたイベントペアを目視確認し、正解データを作成する
"""

import pandas as pd
import json
from pathlib import Path

def load_event_pairs(csv_path):
    """イベントペアCSVを読み込み"""
    df = pd.read_csv(csv_path)
    return df

def create_ground_truth_interface(df, output_path="output/ground_truth.json"):
    """
    対話的にGround Truthを作成
    
    各ペアについて:
    - イベント情報を表示
    - ユーザーが「同じイベント」か「異なるイベント」かを判定
    - 結果をJSONに保存
    """
    
    print("=" * 80)
    print("Ground Truth 作成ツール")
    print("=" * 80)
    print()
    print("各イベントペアについて、同じイベントかどうかを判定してください。")
    print("判定方法:")
    print("  1 = 同じイベント（確実）")
    print("  0 = 異なるイベント（確実）")
    print("  ? = 不明（スキップ）")
    print("  q = 終了")
    print()
    
    # 既存のGround Truthがあれば読み込み
    ground_truth = {}
    if Path(output_path).exists():
        with open(output_path, 'r', encoding='utf-8') as f:
            ground_truth = json.load(f)
        print(f"既存のGround Truth を読み込みました: {len(ground_truth)} ペア")
        print()
    
    # 各ペアについて判定
    for idx, row in df.iterrows():
        pair_id = f"{row['event_A_id']}_{row['event_B_id']}"
        
        # すでに判定済みならスキップ
        if pair_id in ground_truth:
            continue
        
        print("=" * 80)
        print(f"ペア {idx + 1} / {len(df)}")
        print("=" * 80)
        print()
        print(f"【Event A (ID: {row['event_A_id']})】")
        print(f"  配信者: {row['event_A_streams']}")
        print(f"  コメント数: {row['event_A_comments']}")
        print(f"  ラベル: {row['event_A_label']}")
        print()
        print(f"【Event B (ID: {row['event_B_id']})】")
        print(f"  配信者: {row['event_B_streams']}")
        print(f"  コメント数: {row['event_B_comments']}")
        print(f"  ラベル: {row['event_B_label']}")
        print()
        print(f"【類似度情報】")
        print(f"  Total Similarity: {row['combined_score']:.3f}")
        print(f"  Embedding Similarity: {row['embedding_similarity']:.3f}")
        print(f"  Topic Jaccard: {row['topic_jaccard']:.3f}")
        print(f"  Lexical Similarity: {row['lexical_similarity']:.3f}")
        print(f"  Temporal Correlation: {row['temporal_correlation']:.3f}")
        print()
        
        # ユーザー入力
        while True:
            answer = input("同じイベントですか？ (1=同じ / 0=異なる / ?=不明 / q=終了): ").strip().lower()
            
            if answer == 'q':
                print("終了します。")
                save_ground_truth(ground_truth, output_path)
                return ground_truth
            
            elif answer == '?':
                print("スキップしました。")
                break
            
            elif answer in ['1', '0']:
                ground_truth[pair_id] = {
                    'event_A_id': int(row['event_A_id']),
                    'event_B_id': int(row['event_B_id']),
                    'is_same_event': int(answer),
                    'combined_score': float(row['combined_score']),
                    'embedding_similarity': float(row['embedding_similarity']),
                    'topic_jaccard': float(row['topic_jaccard']),
                }
                print(f"記録しました: {'同じイベント' if answer == '1' else '異なるイベント'}")
                
                # 自動保存（途中で終了しても大丈夫なように）
                save_ground_truth(ground_truth, output_path)
                break
            
            else:
                print("無効な入力です。1, 0, ?, q のいずれかを入力してください。")
        
        print()
    
    print("=" * 80)
    print("すべてのペアの判定が完了しました！")
    print(f"Ground Truth: {len(ground_truth)} ペア")
    print("=" * 80)
    
    return ground_truth

def save_ground_truth(ground_truth, output_path):
    """Ground Truthを保存"""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(ground_truth, f, indent=2, ensure_ascii=False)

def calculate_metrics(df, ground_truth, threshold=0.5):
    """
    Ground Truthを使ってPrecision/Recall/F1を計算
    
    Args:
        df: イベントペアのDataFrame
        ground_truth: Ground Truth辞書
        threshold: 類似度の閾値
    """
    
    if not ground_truth:
        print("Ground Truth がありません。")
        return
    
    TP = 0  # True Positive: 同じイベントを同じと判定
    FP = 0  # False Positive: 異なるイベントを同じと判定
    TN = 0  # True Negative: 異なるイベントを異なると判定
    FN = 0  # False Negative: 同じイベントを異なると判定
    
    for idx, row in df.iterrows():
        pair_id = f"{row['event_A_id']}_{row['event_B_id']}"
        
        if pair_id not in ground_truth:
            continue
        
        # Ground Truthのラベル
        is_same_event_gt = ground_truth[pair_id]['is_same_event']
        
        # システムの予測（閾値ベース）
        is_same_event_pred = 1 if row['combined_score'] >= threshold else 0
        
        if is_same_event_gt == 1 and is_same_event_pred == 1:
            TP += 1
        elif is_same_event_gt == 0 and is_same_event_pred == 1:
            FP += 1
        elif is_same_event_gt == 0 and is_same_event_pred == 0:
            TN += 1
        elif is_same_event_gt == 1 and is_same_event_pred == 0:
            FN += 1
    
    # Precision/Recall/F1の計算
    precision = TP / (TP + FP) if (TP + FP) > 0 else 0
    recall = TP / (TP + FN) if (TP + FN) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    accuracy = (TP + TN) / (TP + FP + TN + FN) if (TP + FP + TN + FN) > 0 else 0
    
    print("=" * 80)
    print(f"評価結果（閾値: {threshold}）")
    print("=" * 80)
    print(f"True Positive (TP):  {TP}")
    print(f"False Positive (FP): {FP}")
    print(f"True Negative (TN):  {TN}")
    print(f"False Negative (FN): {FN}")
    print()
    print(f"Precision: {precision:.3f} ({TP}/{TP + FP})")
    print(f"Recall:    {recall:.3f} ({TP}/{TP + FN})")
    print(f"F1-score:  {f1:.3f}")
    print(f"Accuracy:  {accuracy:.3f}")
    print("=" * 80)
    
    return {
        'TP': TP, 'FP': FP, 'TN': TN, 'FN': FN,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'accuracy': accuracy
    }

def plot_precision_recall_curve(df, ground_truth, output_path="output/precision_recall_curve.png"):
    """
    Precision-Recall曲線をプロット
    """
    import matplotlib.pyplot as plt
    import numpy as np
    
    if not ground_truth:
        print("Ground Truth がありません。")
        return
    
    thresholds = np.linspace(0, 1, 101)
    precisions = []
    recalls = []
    f1_scores = []
    
    for threshold in thresholds:
        metrics = calculate_metrics(df, ground_truth, threshold=threshold)
        if metrics:
            precisions.append(metrics['precision'])
            recalls.append(metrics['recall'])
            f1_scores.append(metrics['f1'])
    
    # プロット
    plt.figure(figsize=(12, 5))
    
    # Precision-Recall曲線
    plt.subplot(1, 2, 1)
    plt.plot(recalls, precisions, marker='o', markersize=2)
    plt.xlabel('Recall')
    plt.ylabel('Precision')
    plt.title('Precision-Recall Curve')
    plt.grid(True)
    
    # F1-score vs Threshold
    plt.subplot(1, 2, 2)
    plt.plot(thresholds, f1_scores, marker='o', markersize=2)
    plt.xlabel('Threshold')
    plt.ylabel('F1-score')
    plt.title('F1-score vs Threshold')
    plt.grid(True)
    
    # 最高F1スコアの点を強調
    max_f1_idx = np.argmax(f1_scores)
    max_f1 = f1_scores[max_f1_idx]
    max_f1_threshold = thresholds[max_f1_idx]
    plt.axvline(max_f1_threshold, color='r', linestyle='--', 
                label=f'Best: {max_f1:.3f} @ {max_f1_threshold:.2f}')
    plt.legend()
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"Precision-Recall曲線を保存: {output_path}")
    
    print(f"\n最高F1スコア: {max_f1:.3f} (閾値: {max_f1_threshold:.2f})")

if __name__ == "__main__":
    import sys
    
    # CSVパス
    csv_path = "output/event_to_event_pairs.csv"
    
    if not Path(csv_path).exists():
        print(f"エラー: {csv_path} が見つかりません。")
        print("event_comparison.py を先に実行してください。")
        sys.exit(1)
    
    # イベントペアを読み込み
    df = load_event_pairs(csv_path)
    print(f"イベントペア数: {len(df)}")
    print()
    
    # Ground Truth作成モード
    if "--create" in sys.argv:
        ground_truth = create_ground_truth_interface(df)
    
    # 評価モード
    elif "--evaluate" in sys.argv:
        ground_truth_path = "output/ground_truth.json"
        
        if not Path(ground_truth_path).exists():
            print(f"エラー: {ground_truth_path} が見つかりません。")
            print("--create オプションで先にGround Truthを作成してください。")
            sys.exit(1)
        
        with open(ground_truth_path, 'r', encoding='utf-8') as f:
            ground_truth = json.load(f)
        
        print(f"Ground Truth: {len(ground_truth)} ペア")
        print()
        
        # 複数の閾値で評価
        for threshold in [0.3, 0.4, 0.5, 0.6, 0.7]:
            calculate_metrics(df, ground_truth, threshold=threshold)
            print()
        
        # Precision-Recall曲線を描画
        plot_precision_recall_curve(df, ground_truth)
    
    else:
        print("使用方法:")
        print("  python create_ground_truth.py --create     # Ground Truthを作成")
        print("  python create_ground_truth.py --evaluate   # 評価指標を計算")
