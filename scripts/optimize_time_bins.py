"""
Time Binning Optimization Script (Ground Truth不要版)

内部指標で最適なbin数を決定:
1. Topic Coherence (トピックの一貫性)
2. Event Count (検出イベント数)
3. Similarity Distribution (類似度分布の健全性)
4. Silhouette Score (クラスタリング品質)
"""

import subprocess
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import json
import sys
import io

# ===== Windows UTF-8対応 =====
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

class TimeBinningOptimizer:
    def __init__(self, data_folder='data/chat', pattern='*', output_dir='output/optimization'):
        self.data_folder = data_folder
        self.pattern = pattern
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def run_event_comparison(self, n_bins, n_events=12):
        """event_comparison.pyを指定したbin数で実行"""
        print(f"\n{'='*60}")
        print(f"Testing n_bins={n_bins}")
        print(f"{'='*60}")
        
        cmd = [
            'python', 'scripts/event_comparison.py',
            '--folder', self.data_folder,
            '--pattern', self.pattern,
            '--n-events', str(n_events),
            '--time-bins', str(n_bins),
        ]
        
        # UTF-8対応: Windows環境でのエンコーディング問題を回避
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        
        if result.returncode != 0:
            print(f"⚠️ Error running event_comparison.py with n_bins={n_bins}")
            print(result.stderr)
            return None
        
        return self.load_results()
    
    def load_results(self):
        """実行結果をロード"""
        results = {}
        
        # Event details
        event_details_path = Path('output/similar_event_details.csv')
        if event_details_path.exists():
            results['event_details'] = pd.read_csv(event_details_path)
        
        # Event pairs
        event_pairs_path = Path('output/event_to_event_pairs.csv')
        if event_pairs_path.exists():
            results['event_pairs'] = pd.read_csv(event_pairs_path)
        
        # Event comparison
        event_comparison_path = Path('output/event_comparison_results.csv')
        if event_comparison_path.exists():
            results['event_comparison'] = pd.read_csv(event_comparison_path)
        
        return results
    
    def compute_internal_metrics(self, results, n_bins):
        """内部指標を計算"""
        metrics = {'n_bins': n_bins}
        
        if not results:
            return metrics
        
        # 1. Event Count (イベント数)
        if 'event_details' in results:
            event_details = results['event_details']
            unique_events = event_details['sim_event_id'].nunique()
            metrics['n_events'] = unique_events
            
            # イベントあたりの平均コメント数
            if 'top_words' in event_details.columns:
                event_sizes = event_details.groupby('sim_event_id').size()
                metrics['avg_streams_per_event'] = event_sizes.mean()
                metrics['std_streams_per_event'] = event_sizes.std()
        
        # 2. Similarity Distribution
        if 'event_pairs' in results:
            pairs = results['event_pairs']
            
            # 類似度統計
            if 'combined_score' in pairs.columns:
                metrics['avg_similarity'] = pairs['combined_score'].mean()
                metrics['std_similarity'] = pairs['combined_score'].std()
                metrics['median_similarity'] = pairs['combined_score'].median()
                
                # 類似度分布の健全性 (High similarity比率)
                metrics['high_similarity_ratio'] = (pairs['combined_score'] >= 0.7).mean()
                metrics['mid_similarity_ratio'] = ((pairs['combined_score'] >= 0.5) & 
                                                   (pairs['combined_score'] < 0.7)).mean()
                metrics['low_similarity_ratio'] = (pairs['combined_score'] < 0.5).mean()
            
            # Topic Jaccard統計
            if 'topic_jaccard' in pairs.columns:
                metrics['avg_topic_jaccard'] = pairs['topic_jaccard'].mean()
                metrics['topic_jaccard_gt0_ratio'] = (pairs['topic_jaccard'] > 0).mean()
                metrics['topic_jaccard_gt03_ratio'] = (pairs['topic_jaccard'] > 0.3).mean()
            
            # Temporal Correlation
            if 'temporal_correlation' in pairs.columns:
                metrics['avg_temporal_correlation'] = pairs['temporal_correlation'].mean()
                metrics['high_temporal_corr_ratio'] = (pairs['temporal_correlation'] > 0.5).mean()
            
            # Confidence Score
            if 'confidence_score' in pairs.columns:
                metrics['avg_confidence'] = pairs['confidence_score'].mean()
                metrics['high_confidence_ratio'] = (pairs['confidence_score'] > 0.7).mean()
        
        # 3. Quality Score (複合指標)
        # 高品質 = 適度なイベント数 + 高いtopic matching + 良い類似度分布
        quality_components = []
        
        # イベント数スコア (5-15イベントが理想)
        if 'n_events' in metrics:
            ideal_events = 10
            event_score = 1 - abs(metrics['n_events'] - ideal_events) / ideal_events
            event_score = max(0, min(1, event_score))
            quality_components.append(('event_count', event_score, 0.2))
        
        # Topic matching スコア
        if 'topic_jaccard_gt0_ratio' in metrics:
            quality_components.append(('topic_matching', metrics['topic_jaccard_gt0_ratio'], 0.3))
        
        # 類似度分布スコア
        if 'high_similarity_ratio' in metrics and 'mid_similarity_ratio' in metrics:
            # High + Mid が多い方が良い (Lowは少ない方が良い)
            similarity_score = metrics['high_similarity_ratio'] + 0.5 * metrics['mid_similarity_ratio']
            quality_components.append(('similarity_distribution', similarity_score, 0.3))
        
        # Confidence スコア
        if 'avg_confidence' in metrics:
            quality_components.append(('confidence', metrics['avg_confidence'], 0.2))
        
        # 総合品質スコア
        if quality_components:
            total_weight = sum(w for _, _, w in quality_components)
            metrics['quality_score'] = sum(score * weight for _, score, weight in quality_components) / total_weight
            
            # 各コンポーネントの詳細
            for name, score, weight in quality_components:
                metrics[f'quality_{name}'] = score
        
        return metrics
    
    def optimize(self, bin_candidates=None, n_events=12):
        """最適化実行"""
        if bin_candidates is None:
            bin_candidates = [20, 30, 50, 75, 100]
        
        print(f"\n{'='*60}")
        print(f"Time Binning Optimization")
        print(f"{'='*60}")
        print(f"Candidates: {bin_candidates}")
        print(f"Target events: {n_events}")
        print(f"Evaluation: Internal metrics (no ground truth)")
        print(f"{'='*60}\n")
        
        all_metrics = []
        
        for n_bins in bin_candidates:
            # 実行
            results = self.run_event_comparison(n_bins, n_events)
            
            # 評価
            metrics = self.compute_internal_metrics(results, n_bins)
            all_metrics.append(metrics)
            
            # 結果表示
            print(f"\n📊 Results for n_bins={n_bins}:")
            print(f"  Events detected: {metrics.get('n_events', 'N/A')}")
            print(f"  Avg similarity: {metrics.get('avg_similarity', 0):.3f}")
            print(f"  Topic jaccard>0: {metrics.get('topic_jaccard_gt0_ratio', 0):.1%}")
            print(f"  High similarity: {metrics.get('high_similarity_ratio', 0):.1%}")
            print(f"  Quality score: {metrics.get('quality_score', 0):.3f}")
        
        # DataFrameに変換
        metrics_df = pd.DataFrame(all_metrics)
        
        # 結果保存
        output_path = self.output_dir / 'time_bins_optimization_results.csv'
        metrics_df.to_csv(output_path, index=False)
        print(f"\n✅ Results saved: {output_path}")
        
        # 最適値を選択
        if 'quality_score' in metrics_df.columns:
            optimal_idx = metrics_df['quality_score'].idxmax()
            optimal_bins = metrics_df.loc[optimal_idx, 'n_bins']
            optimal_score = metrics_df.loc[optimal_idx, 'quality_score']
            
            print(f"\n{'='*60}")
            print(f"🎯 OPTIMAL CONFIGURATION")
            print(f"{'='*60}")
            print(f"Optimal n_bins: {optimal_bins}")
            print(f"Quality score: {optimal_score:.3f}")
            print(f"{'='*60}\n")
        
        # 可視化
        self.visualize_results(metrics_df)
        
        return metrics_df
    
    def visualize_results(self, metrics_df):
        """結果の可視化"""
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle('Time Binning Optimization Results', fontsize=16, fontweight='bold')
        
        # 1. Quality Score
        ax = axes[0, 0]
        if 'quality_score' in metrics_df.columns:
            ax.plot(metrics_df['n_bins'], metrics_df['quality_score'], 
                   marker='o', linewidth=2, markersize=10, color='#2E86AB')
            optimal_idx = metrics_df['quality_score'].idxmax()
            ax.axvline(metrics_df.loc[optimal_idx, 'n_bins'], 
                      color='red', linestyle='--', alpha=0.7,
                      label=f"Optimal: {metrics_df.loc[optimal_idx, 'n_bins']}")
            ax.set_xlabel('Number of Time Bins', fontsize=12)
            ax.set_ylabel('Quality Score', fontsize=12)
            ax.set_title('Overall Quality Score', fontsize=13, fontweight='bold')
            ax.legend()
            ax.grid(True, alpha=0.3)
        
        # 2. Number of Events
        ax = axes[0, 1]
        if 'n_events' in metrics_df.columns:
            ax.plot(metrics_df['n_bins'], metrics_df['n_events'], 
                   marker='s', linewidth=2, markersize=10, color='#A23B72')
            ax.axhline(10, color='green', linestyle='--', alpha=0.5, label='Ideal: 10 events')
            ax.set_xlabel('Number of Time Bins', fontsize=12)
            ax.set_ylabel('Number of Events', fontsize=12)
            ax.set_title('Events Detected', fontsize=13, fontweight='bold')
            ax.legend()
            ax.grid(True, alpha=0.3)
        
        # 3. Topic Matching
        ax = axes[0, 2]
        if 'topic_jaccard_gt0_ratio' in metrics_df.columns:
            ax.plot(metrics_df['n_bins'], metrics_df['topic_jaccard_gt0_ratio'], 
                   marker='^', linewidth=2, markersize=10, color='#F18F01')
            ax.set_xlabel('Number of Time Bins', fontsize=12)
            ax.set_ylabel('Topic Jaccard > 0 Ratio', fontsize=12)
            ax.set_title('Topic Matching Rate', fontsize=13, fontweight='bold')
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.0%}'))
            ax.grid(True, alpha=0.3)
        
        # 4. Similarity Distribution
        ax = axes[1, 0]
        if all(col in metrics_df.columns for col in ['high_similarity_ratio', 'mid_similarity_ratio', 'low_similarity_ratio']):
            width = 0.25
            x = np.arange(len(metrics_df))
            ax.bar(x - width, metrics_df['high_similarity_ratio'], width, 
                  label='High (≥0.7)', color='#06A77D')
            ax.bar(x, metrics_df['mid_similarity_ratio'], width, 
                  label='Mid (0.5-0.7)', color='#F4D35E')
            ax.bar(x + width, metrics_df['low_similarity_ratio'], width, 
                  label='Low (<0.5)', color='#EE964B')
            ax.set_xlabel('Configuration', fontsize=12)
            ax.set_ylabel('Ratio', fontsize=12)
            ax.set_title('Similarity Distribution', fontsize=13, fontweight='bold')
            ax.set_xticks(x)
            ax.set_xticklabels([f'{int(b)} bins' for b in metrics_df['n_bins']])
            ax.legend()
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.0%}'))
            ax.grid(True, alpha=0.3, axis='y')
        
        # 5. Average Similarity
        ax = axes[1, 1]
        if 'avg_similarity' in metrics_df.columns:
            ax.plot(metrics_df['n_bins'], metrics_df['avg_similarity'], 
                   marker='D', linewidth=2, markersize=10, color='#C73E1D')
            if 'std_similarity' in metrics_df.columns:
                ax.fill_between(metrics_df['n_bins'], 
                               metrics_df['avg_similarity'] - metrics_df['std_similarity'],
                               metrics_df['avg_similarity'] + metrics_df['std_similarity'],
                               alpha=0.3, color='#C73E1D')
            ax.set_xlabel('Number of Time Bins', fontsize=12)
            ax.set_ylabel('Average Similarity', fontsize=12)
            ax.set_title('Similarity Score (Mean ± Std)', fontsize=13, fontweight='bold')
            ax.grid(True, alpha=0.3)
        
        # 6. Quality Components
        ax = axes[1, 2]
        quality_cols = [col for col in metrics_df.columns if col.startswith('quality_') and col != 'quality_score']
        if quality_cols:
            for col in quality_cols:
                label = col.replace('quality_', '').replace('_', ' ').title()
                ax.plot(metrics_df['n_bins'], metrics_df[col], 
                       marker='o', linewidth=2, markersize=8, label=label)
            ax.set_xlabel('Number of Time Bins', fontsize=12)
            ax.set_ylabel('Component Score', fontsize=12)
            ax.set_title('Quality Components Breakdown', fontsize=13, fontweight='bold')
            ax.legend(fontsize=9)
            ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        output_path = self.output_dir / 'time_bins_optimization.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"✅ Visualization saved: {output_path}")
        plt.close()
        
        # Summary table
        self.create_summary_table(metrics_df)
    
    def create_summary_table(self, metrics_df):
        """サマリーテーブル作成"""
        fig, ax = plt.subplots(figsize=(14, 6))
        ax.axis('tight')
        ax.axis('off')
        
        # 表示する列を選択
        display_cols = ['n_bins', 'n_events', 'avg_similarity', 'topic_jaccard_gt0_ratio', 
                       'high_similarity_ratio', 'quality_score']
        display_cols = [col for col in display_cols if col in metrics_df.columns]
        
        table_data = metrics_df[display_cols].copy()
        
        # フォーマット
        if 'avg_similarity' in table_data.columns:
            table_data['avg_similarity'] = table_data['avg_similarity'].apply(lambda x: f'{x:.3f}')
        if 'topic_jaccard_gt0_ratio' in table_data.columns:
            table_data['topic_jaccard_gt0_ratio'] = table_data['topic_jaccard_gt0_ratio'].apply(lambda x: f'{x:.1%}')
        if 'high_similarity_ratio' in table_data.columns:
            table_data['high_similarity_ratio'] = table_data['high_similarity_ratio'].apply(lambda x: f'{x:.1%}')
        if 'quality_score' in table_data.columns:
            table_data['quality_score'] = table_data['quality_score'].apply(lambda x: f'{x:.3f}')
        
        # カラム名を整形
        col_labels = {
            'n_bins': 'Time Bins',
            'n_events': 'Events',
            'avg_similarity': 'Avg Sim',
            'topic_jaccard_gt0_ratio': 'Topic Match',
            'high_similarity_ratio': 'High Sim',
            'quality_score': 'Quality'
        }
        table_data.columns = [col_labels.get(col, col) for col in table_data.columns]
        
        table = ax.table(cellText=table_data.values,
                        colLabels=table_data.columns,
                        cellLoc='center',
                        loc='center',
                        colColours=['#E8E8E8']*len(table_data.columns))
        
        table.auto_set_font_size(False)
        table.set_fontsize(11)
        table.scale(1, 2)
        
        # 最適行をハイライト
        if 'Quality' in table_data.columns:
            quality_col_idx = list(table_data.columns).index('Quality')
            max_quality_idx = table_data['Quality'].apply(lambda x: float(x)).idxmax()
            
            for col in range(len(table_data.columns)):
                table[(max_quality_idx + 1, col)].set_facecolor('#90EE90')
                table[(max_quality_idx + 1, col)].set_text_props(weight='bold')
        
        plt.title('Time Binning Optimization Summary', fontsize=14, fontweight='bold', pad=20)
        
        output_path = self.output_dir / 'time_bins_summary_table.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"✅ Summary table saved: {output_path}")
        plt.close()


def main():
    optimizer = TimeBinningOptimizer(
        data_folder='data/chat',
        pattern='*',
        output_dir='output/optimization'
    )
    
    # 最適化実行
    # 候補: 20, 30, 50, 75, 100
    results = optimizer.optimize(
        bin_candidates=[20, 30, 50, 75, 100],
        n_events=12
    )
    
    print("\n✅ Time Binning Optimization Complete!")
    print(f"📁 Results saved in: output/optimization/")
    print(f"📊 Check the visualizations to see the optimal configuration")


if __name__ == '__main__':
    main()
