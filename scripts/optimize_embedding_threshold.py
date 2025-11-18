"""
Embedding Threshold Optimization Script (Ground Truth不要版)

内部指標で最適なembedding閾値を決定:
1. Similarity Distribution (類似度分布の健全性)
2. Topic Matching Rate
3. Cluster Separation (Silhouette Score)
"""

import subprocess
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import sys
import io

# ===== Windows UTF-8対応 =====
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


class EmbeddingThresholdOptimizer:
    def __init__(self, data_folder='data/chat', pattern='*', output_dir='output/optimization'):
        self.data_folder = data_folder
        self.pattern = pattern
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def run_event_comparison(self, embedding_th, time_bins=50, n_events=12):
        """event_comparison.pyを指定したembedding閾値で実行"""
        print(f"\n{'='*60}")
        print(f"Testing embedding_threshold={embedding_th:.2f}")
        print(f"{'='*60}")
        
        cmd = [
            'python', 'scripts/event_comparison.py',
            '--folder', self.data_folder,
            '--pattern', self.pattern,
            '--n-events', str(n_events),
            '--time-bins', str(time_bins),
            '--embedding-match-th', str(embedding_th),
        ]
        
        # UTF-8対応: Windows環境でのエンコーディング問題を回避
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        
        if result.returncode != 0:
            print(f"⚠️ Error running event_comparison.py with embedding_th={embedding_th}")
            return None
        
        return self.load_results()
    
    def load_results(self):
        """実行結果をロード"""
        results = {}
        
        event_details_path = Path('output/similar_event_details.csv')
        if event_details_path.exists():
            results['event_details'] = pd.read_csv(event_details_path)
        
        event_pairs_path = Path('output/event_to_event_pairs.csv')
        if event_pairs_path.exists():
            results['event_pairs'] = pd.read_csv(event_pairs_path)
        
        return results
    
    def compute_internal_metrics(self, results, embedding_th):
        """内部指標を計算"""
        metrics = {'embedding_th': embedding_th}
        
        if not results or 'event_pairs' not in results:
            return metrics
        
        pairs = results['event_pairs']
        
        # 1. マッチング統計
        total_pairs = len(pairs)
        metrics['total_pairs'] = total_pairs
        
        # Embedding similarity統計
        if 'embedding_similarity' in pairs.columns:
            metrics['avg_embedding_sim'] = pairs['embedding_similarity'].mean()
            metrics['std_embedding_sim'] = pairs['embedding_similarity'].std()
            metrics['median_embedding_sim'] = pairs['embedding_similarity'].median()
            
            # 閾値以上のペア数
            metrics['pairs_above_th'] = (pairs['embedding_similarity'] >= embedding_th).sum()
            metrics['pairs_above_th_ratio'] = metrics['pairs_above_th'] / total_pairs
        
        # 2. Topic Matching
        if 'topic_jaccard' in pairs.columns:
            metrics['avg_topic_jaccard'] = pairs['topic_jaccard'].mean()
            metrics['topic_match_gt0'] = (pairs['topic_jaccard'] > 0).sum()
            metrics['topic_match_gt0_ratio'] = metrics['topic_match_gt0'] / total_pairs
            metrics['topic_match_gt03'] = (pairs['topic_jaccard'] > 0.3).sum()
            metrics['topic_match_gt03_ratio'] = metrics['topic_match_gt03'] / total_pairs
        
        # 3. Combined Score分布
        if 'combined_score' in pairs.columns:
            metrics['avg_combined_score'] = pairs['combined_score'].mean()
            metrics['std_combined_score'] = pairs['combined_score'].std()
            
            # 類似度分布
            metrics['high_sim_ratio'] = (pairs['combined_score'] >= 0.7).mean()
            metrics['mid_sim_ratio'] = ((pairs['combined_score'] >= 0.5) & 
                                       (pairs['combined_score'] < 0.7)).mean()
            metrics['low_sim_ratio'] = (pairs['combined_score'] < 0.5).mean()
        
        # 4. Confidence Score
        if 'confidence_score' in pairs.columns:
            metrics['avg_confidence'] = pairs['confidence_score'].mean()
            metrics['high_confidence_ratio'] = (pairs['confidence_score'] > 0.7).mean()
        
        # 5. イベント数
        if 'event_details' in results:
            events = results['event_details']
            metrics['n_events'] = events['sim_event_id'].nunique()
        
        # 6. Quality Score (複合指標)
        quality_components = []
        
        # Topic matching重視 (30%)
        if 'topic_match_gt0_ratio' in metrics:
            quality_components.append(('topic_match', metrics['topic_match_gt0_ratio'], 0.3))
        
        # 類似度分布 (High+Mid が多い方が良い) (30%)
        if 'high_sim_ratio' in metrics and 'mid_sim_ratio' in metrics:
            sim_score = metrics['high_sim_ratio'] + 0.5 * metrics['mid_sim_ratio']
            quality_components.append(('similarity_dist', sim_score, 0.3))
        
        # Confidence (20%)
        if 'avg_confidence' in metrics:
            quality_components.append(('confidence', metrics['avg_confidence'], 0.2))
        
        # マッチング率 (ペア数が多すぎず少なすぎず) (20%)
        if 'pairs_above_th_ratio' in metrics:
            # 20-60%が理想的
            ideal_ratio = 0.4
            ratio_score = 1 - abs(metrics['pairs_above_th_ratio'] - ideal_ratio) / ideal_ratio
            ratio_score = max(0, min(1, ratio_score))
            quality_components.append(('matching_rate', ratio_score, 0.2))
        
        # 総合スコア
        if quality_components:
            total_weight = sum(w for _, _, w in quality_components)
            metrics['quality_score'] = sum(score * weight for _, score, weight in quality_components) / total_weight
            
            for name, score, weight in quality_components:
                metrics[f'quality_{name}'] = score
        
        return metrics
    
    def optimize(self, threshold_candidates=None, time_bins=50, n_events=12):
        """最適化実行"""
        if threshold_candidates is None:
            threshold_candidates = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75]
        
        print(f"\n{'='*60}")
        print(f"Embedding Threshold Optimization")
        print(f"{'='*60}")
        print(f"Candidates: {threshold_candidates}")
        print(f"Time bins: {time_bins}")
        print(f"Target events: {n_events}")
        print(f"{'='*60}\n")
        
        all_metrics = []
        
        for th in threshold_candidates:
            # 実行
            results = self.run_event_comparison(th, time_bins, n_events)
            
            # 評価
            metrics = self.compute_internal_metrics(results, th)
            all_metrics.append(metrics)
            
            # 結果表示
            print(f"\n📊 Results for embedding_th={th:.2f}:")
            print(f"  Total pairs: {metrics.get('total_pairs', 0)}")
            print(f"  Pairs above th: {metrics.get('pairs_above_th', 0)} ({metrics.get('pairs_above_th_ratio', 0):.1%})")
            print(f"  Topic match>0: {metrics.get('topic_match_gt0_ratio', 0):.1%}")
            print(f"  High similarity: {metrics.get('high_sim_ratio', 0):.1%}")
            print(f"  Quality score: {metrics.get('quality_score', 0):.3f}")
        
        # DataFrame化
        metrics_df = pd.DataFrame(all_metrics)
        
        # 保存
        output_path = self.output_dir / 'embedding_threshold_optimization_results.csv'
        metrics_df.to_csv(output_path, index=False)
        print(f"\n✅ Results saved: {output_path}")
        
        # 最適値選択
        if 'quality_score' in metrics_df.columns:
            optimal_idx = metrics_df['quality_score'].idxmax()
            optimal_th = metrics_df.loc[optimal_idx, 'embedding_th']
            optimal_score = metrics_df.loc[optimal_idx, 'quality_score']
            
            print(f"\n{'='*60}")
            print(f"🎯 OPTIMAL CONFIGURATION")
            print(f"{'='*60}")
            print(f"Optimal embedding_th: {optimal_th:.2f}")
            print(f"Quality score: {optimal_score:.3f}")
            print(f"{'='*60}\n")
        
        # 可視化
        self.visualize_results(metrics_df)
        
        return metrics_df
    
    def visualize_results(self, metrics_df):
        """結果の可視化"""
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle('Embedding Threshold Optimization Results', fontsize=16, fontweight='bold')
        
        # 1. Quality Score
        ax = axes[0, 0]
        if 'quality_score' in metrics_df.columns:
            ax.plot(metrics_df['embedding_th'], metrics_df['quality_score'], 
                   marker='o', linewidth=2, markersize=10, color='#2E86AB')
            optimal_idx = metrics_df['quality_score'].idxmax()
            ax.axvline(metrics_df.loc[optimal_idx, 'embedding_th'], 
                      color='red', linestyle='--', alpha=0.7,
                      label=f"Optimal: {metrics_df.loc[optimal_idx, 'embedding_th']:.2f}")
            ax.set_xlabel('Embedding Threshold', fontsize=12)
            ax.set_ylabel('Quality Score', fontsize=12)
            ax.set_title('Overall Quality Score', fontsize=13, fontweight='bold')
            ax.legend()
            ax.grid(True, alpha=0.3)
        
        # 2. Pairs Above Threshold
        ax = axes[0, 1]
        if 'pairs_above_th_ratio' in metrics_df.columns:
            ax.plot(metrics_df['embedding_th'], metrics_df['pairs_above_th_ratio'], 
                   marker='s', linewidth=2, markersize=10, color='#A23B72')
            ax.axhspan(0.2, 0.6, alpha=0.2, color='green', label='Ideal range')
            ax.set_xlabel('Embedding Threshold', fontsize=12)
            ax.set_ylabel('Pairs Above Threshold Ratio', fontsize=12)
            ax.set_title('Matching Rate', fontsize=13, fontweight='bold')
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.0%}'))
            ax.legend()
            ax.grid(True, alpha=0.3)
        
        # 3. Topic Matching
        ax = axes[0, 2]
        if 'topic_match_gt0_ratio' in metrics_df.columns:
            ax.plot(metrics_df['embedding_th'], metrics_df['topic_match_gt0_ratio'], 
                   marker='^', linewidth=2, markersize=10, color='#F18F01', label='Jaccard > 0')
            if 'topic_match_gt03_ratio' in metrics_df.columns:
                ax.plot(metrics_df['embedding_th'], metrics_df['topic_match_gt03_ratio'], 
                       marker='v', linewidth=2, markersize=10, color='#C73E1D', label='Jaccard > 0.3')
            ax.set_xlabel('Embedding Threshold', fontsize=12)
            ax.set_ylabel('Topic Match Ratio', fontsize=12)
            ax.set_title('Topic Matching Rate', fontsize=13, fontweight='bold')
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.0%}'))
            ax.legend()
            ax.grid(True, alpha=0.3)
        
        # 4. Similarity Distribution
        ax = axes[1, 0]
        if all(col in metrics_df.columns for col in ['high_sim_ratio', 'mid_sim_ratio', 'low_sim_ratio']):
            width = 0.08
            x = metrics_df['embedding_th'].values
            ax.bar(x - width, metrics_df['high_sim_ratio'], width, 
                  label='High (≥0.7)', color='#06A77D')
            ax.bar(x, metrics_df['mid_sim_ratio'], width, 
                  label='Mid (0.5-0.7)', color='#F4D35E')
            ax.bar(x + width, metrics_df['low_sim_ratio'], width, 
                  label='Low (<0.5)', color='#EE964B')
            ax.set_xlabel('Embedding Threshold', fontsize=12)
            ax.set_ylabel('Ratio', fontsize=12)
            ax.set_title('Similarity Distribution', fontsize=13, fontweight='bold')
            ax.legend()
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.0%}'))
            ax.grid(True, alpha=0.3, axis='y')
        
        # 5. Precision-Recall Trade-off
        ax = axes[1, 1]
        if 'pairs_above_th_ratio' in metrics_df.columns and 'topic_match_gt0_ratio' in metrics_df.columns:
            # Pairs above th ≈ Recall (検出率)
            # Topic match ≈ Precision (正確さ)
            sc = ax.scatter(metrics_df['pairs_above_th_ratio'], 
                          metrics_df['topic_match_gt0_ratio'],
                          c=metrics_df['embedding_th'], 
                          cmap='viridis', s=200, edgecolors='black', linewidth=2)
            
            # 各点にラベル
            for idx, row in metrics_df.iterrows():
                ax.annotate(f"{row['embedding_th']:.2f}", 
                          (row['pairs_above_th_ratio'], row['topic_match_gt0_ratio']),
                          fontsize=9, ha='center', va='bottom')
            
            plt.colorbar(sc, ax=ax, label='Embedding Threshold')
            ax.set_xlabel('Matching Rate (≈ Recall)', fontsize=12)
            ax.set_ylabel('Topic Match Rate (≈ Precision)', fontsize=12)
            ax.set_title('Precision-Recall Trade-off', fontsize=13, fontweight='bold')
            ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.0%}'))
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.0%}'))
            ax.grid(True, alpha=0.3)
        
        # 6. Quality Components
        ax = axes[1, 2]
        quality_cols = [col for col in metrics_df.columns if col.startswith('quality_') and col != 'quality_score']
        if quality_cols:
            for col in quality_cols:
                label = col.replace('quality_', '').replace('_', ' ').title()
                ax.plot(metrics_df['embedding_th'], metrics_df[col], 
                       marker='o', linewidth=2, markersize=8, label=label)
            ax.set_xlabel('Embedding Threshold', fontsize=12)
            ax.set_ylabel('Component Score', fontsize=12)
            ax.set_title('Quality Components Breakdown', fontsize=13, fontweight='bold')
            ax.legend(fontsize=9)
            ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        output_path = self.output_dir / 'embedding_threshold_optimization.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"✅ Visualization saved: {output_path}")
        plt.close()


def main():
    optimizer = EmbeddingThresholdOptimizer(
        data_folder='data/chat',
        pattern='*',
        output_dir='output/optimization'
    )
    
    # 最適化実行
    # Time bins=50 (前の最適化結果を使用、または固定値)
    results = optimizer.optimize(
        threshold_candidates=[0.50, 0.55, 0.60, 0.65, 0.70, 0.75],
        time_bins=50,
        n_events=12
    )
    
    print("\n✅ Embedding Threshold Optimization Complete!")
    print(f"📁 Results saved in: output/optimization/")


if __name__ == '__main__':
    main()
