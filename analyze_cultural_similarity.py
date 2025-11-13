"""
軸3: 文化的類似度の階層分析
同じ文化内 vs 異なる文化間の類似度を比較
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import f_oneway, mannwhitneyu, kruskal
import os

# 日本語フォント設定
plt.rcParams['font.sans-serif'] = ['MS Gothic', 'Yu Gothic', 'Meiryo']
plt.rcParams['axes.unicode_minus'] = False

def load_event_similarity_data():
    """Event類似度データを読み込む"""
    try:
        df = pd.read_csv('output/event_to_event_pairs.csv')
        return df
    except Exception as e:
        print(f"Error loading event similarity data: {e}")
        return None

def load_event_details():
    """Event詳細データを読み込む"""
    try:
        df = pd.read_csv('output/similar_event_details.csv')
        return df
    except Exception as e:
        print(f"Error loading event details: {e}")
        return None

def extract_broadcaster_from_stream(stream_name):
    """Stream名からbroadcaster名を抽出"""
    if 'Bra' in str(stream_name):
        return 'Brazil'
    elif 'Ja_abema' in str(stream_name):
        return 'Japan_abema'
    elif 'Ja_goat' in str(stream_name):
        return 'Japan_goat'
    elif 'UK' in str(stream_name):
        return 'UK'
    else:
        return 'Unknown'

def get_cultural_category(broadcaster_a, broadcaster_b):
    """2つのbroadcaster間の文化的カテゴリを判定"""
    # 同じbroadcaster
    if broadcaster_a == broadcaster_b:
        return 'Same Broadcaster'
    
    # 同じ言語（Ja_abema ↔ Ja_goat）
    if 'Japan' in broadcaster_a and 'Japan' in broadcaster_b:
        return 'Same Language (Japan)'
    
    # 異なる言語・地域
    return 'Cross-Culture'

def analyze_cultural_similarity():
    """文化的類似度を分析"""
    
    print("="*80)
    print("軸3: 文化的類似度の階層分析")
    print("="*80)
    
    # データ読み込み
    print("\n📊 データ読み込み中...")
    df_pairs = load_event_similarity_data()
    df_details = load_event_details()
    
    if df_pairs is None:
        print("❌ Event pairsデータが見つかりません")
        return
    
    print(f"✅ Total pairs: {len(df_pairs)}")
    print(f"Columns: {df_pairs.columns.tolist()}")
    
    # Event IDごとのbroadcaster情報を取得
    event_broadcasters = {}
    if df_details is not None:
        for idx, row in df_details.iterrows():
            event_id = row['sim_event_id']
            stream = row['stream']
            broadcaster = extract_broadcaster_from_stream(stream)
            if event_id not in event_broadcasters:
                event_broadcasters[event_id] = []
            if broadcaster != 'Unknown' and broadcaster not in event_broadcasters[event_id]:
                event_broadcasters[event_id].append(broadcaster)
    
    print(f"\n✅ Event broadcasters extracted: {len(event_broadcasters)} events")
    
    # Event pairsにbroadcaster情報を追加
    results = []
    
    for idx, row in df_pairs.iterrows():
        # Event IDを取得（カラム名を確認）
        if 'event_A_id' in df_pairs.columns and 'event_B_id' in df_pairs.columns:
            event_a = row['event_A_id']
            event_b = row['event_B_id']
        elif 'event_A' in df_pairs.columns and 'event_B' in df_pairs.columns:
            event_a = row['event_A']
            event_b = row['event_B']
        elif 'sim_event_id_A' in df_pairs.columns and 'sim_event_id_B' in df_pairs.columns:
            event_a = row['sim_event_id_A']
            event_b = row['sim_event_id_B']
        else:
            print("⚠️ Event ID columns not found")
            continue
        
        # Broadcasterを取得
        broadcasters_a = event_broadcasters.get(event_a, [])
        broadcasters_b = event_broadcasters.get(event_b, [])
        
        if not broadcasters_a or not broadcasters_b:
            continue
        
        # 類似度スコアを取得
        if 'combined_score' in df_pairs.columns:
            combined_score = row['combined_score']
        elif 'similarity_score' in df_pairs.columns:
            combined_score = row['similarity_score']
        else:
            combined_score = None
        
        # 各broadcaster組み合わせについて
        for broadcaster_a in broadcasters_a:
            for broadcaster_b in broadcasters_b:
                category = get_cultural_category(broadcaster_a, broadcaster_b)
                
                result = {
                    'event_A': event_a,
                    'event_B': event_b,
                    'broadcaster_A': broadcaster_a,
                    'broadcaster_B': broadcaster_b,
                    'category': category,
                    'combined_score': combined_score,
                    'embedding_similarity': row.get('embedding_similarity', None),
                    'topic_jaccard': row.get('topic_jaccard', None),
                    'lexical_similarity': row.get('lexical_similarity', None)
                }
                results.append(result)
    
    df_analysis = pd.DataFrame(results)
    
    if len(df_analysis) == 0:
        print("❌ 分析データが作成できませんでした")
        return
    
    print(f"\n✅ Analysis pairs created: {len(df_analysis)}")
    
    # カテゴリ別に集計
    print("\n" + "="*80)
    print("📊 カテゴリ別集計")
    print("="*80)
    
    category_summary = df_analysis.groupby('category').agg({
        'combined_score': ['count', 'mean', 'std', 'min', 'max'],
        'topic_jaccard': ['mean', lambda x: (x > 0).sum()],  # Topic coverage
    }).round(3)
    
    print(category_summary)
    
    # 統計的検定
    print("\n" + "="*80)
    print("📈 統計的検定")
    print("="*80)
    
    categories = df_analysis['category'].unique()
    
    if len(categories) >= 2:
        # Kruskal-Wallis test
        groups = [df_analysis[df_analysis['category'] == cat]['combined_score'].dropna().values 
                  for cat in categories]
        groups = [g for g in groups if len(g) > 0]
        
        if len(groups) >= 2:
            h_stat, p_value = kruskal(*groups)
            print(f"\nCombined Score:")
            print(f"  Kruskal-Wallis H = {h_stat:.3f}, p = {p_value:.4f}")
            
            if p_value < 0.05:
                print(f"  ✅ Significant difference detected!")
                
                # Post-hoc pairwise comparisons
                print(f"\n  Post-hoc pairwise comparisons:")
                for i, cat1 in enumerate(categories):
                    for cat2 in categories[i+1:]:
                        group1 = df_analysis[df_analysis['category'] == cat1]['combined_score'].dropna().values
                        group2 = df_analysis[df_analysis['category'] == cat2]['combined_score'].dropna().values
                        
                        if len(group1) > 0 and len(group2) > 0:
                            u_stat, p = mannwhitneyu(group1, group2, alternative='two-sided')
                            cohens_d = (np.mean(group1) - np.mean(group2)) / np.sqrt((np.std(group1)**2 + np.std(group2)**2) / 2)
                            print(f"    {cat1} vs {cat2}: U={u_stat:.1f}, p={p:.4f}, d={cohens_d:.3f}")
            else:
                print(f"  ❌ No significant difference")
    
    # 結果を保存
    output_dir = 'output/cultural_similarity_analysis'
    os.makedirs(output_dir, exist_ok=True)
    
    df_analysis.to_csv(f'{output_dir}/cultural_similarity_results.csv', index=False, encoding='utf-8-sig')
    print(f"\n✅ Results saved to {output_dir}/cultural_similarity_results.csv")
    
    # 可視化
    print("\n" + "="*80)
    print("🎨 可視化作成中...")
    print("="*80)
    
    create_visualizations(df_analysis, output_dir)
    
    print("\n✅ 分析完了！")
    print(f"📁 結果は {output_dir}/ に保存されました")
    
    return df_analysis

def create_visualizations(df, output_dir):
    """可視化を作成"""
    
    # Figure 1: Boxplot - Cultural categories comparison
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    metrics = [
        ('combined_score', 'Combined Similarity Score', axes[0]),
        ('embedding_similarity', 'Embedding Similarity', axes[1]),
        ('topic_jaccard', 'Topic Jaccard', axes[2])
    ]
    
    for metric, title, ax in metrics:
        data_to_plot = df[['category', metric]].dropna()
        
        if len(data_to_plot) > 0:
            sns.boxplot(data=data_to_plot, x='category', y=metric, ax=ax, hue='category', palette='Set2', legend=False)
            
            # Individual points
            for i, category in enumerate(df['category'].unique()):
                values = df[df['category'] == category][metric].dropna().values
                if len(values) > 0:
                    x_positions = np.random.normal(i, 0.04, size=len(values))
                    ax.scatter(x_positions, values, alpha=0.4, color='black', s=20)
            
            ax.set_title(title, fontsize=12, fontweight='bold')
            ax.set_xlabel('Cultural Category', fontsize=10)
            ax.set_ylabel(title, fontsize=10)
            ax.tick_params(axis='x', rotation=45)
            ax.grid(alpha=0.3, axis='y')
        else:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/cultural_similarity_comparison.png', dpi=300, bbox_inches='tight')
    print(f"✅ Saved: cultural_similarity_comparison.png")
    plt.close()
    
    # Figure 2: Violin plot
    fig, ax = plt.subplots(figsize=(10, 6))
    
    data_to_plot = df[['category', 'combined_score']].dropna()
    
    if len(data_to_plot) > 0:
        sns.violinplot(data=data_to_plot, x='category', y='combined_score', ax=ax, hue='category', palette='Set3', legend=False)
        sns.swarmplot(data=data_to_plot, x='category', y='combined_score', ax=ax, color='black', alpha=0.5, size=3)
        
        ax.set_title('Distribution of Similarity Scores by Cultural Category', fontsize=14, fontweight='bold')
        ax.set_xlabel('Cultural Category', fontsize=12)
        ax.set_ylabel('Combined Similarity Score', fontsize=12)
        ax.tick_params(axis='x', rotation=45)
        ax.grid(alpha=0.3, axis='y')
        
        # 平均値を追加
        for i, category in enumerate(df['category'].unique()):
            mean_val = df[df['category'] == category]['combined_score'].mean()
            ax.plot([i-0.3, i+0.3], [mean_val, mean_val], 'r-', linewidth=2)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/similarity_distribution_by_category.png', dpi=300, bbox_inches='tight')
    print(f"✅ Saved: similarity_distribution_by_category.png")
    plt.close()
    
    # Figure 3: Heatmap - Category summary
    fig, ax = plt.subplots(figsize=(10, 6))
    
    category_metrics = df.groupby('category').agg({
        'combined_score': 'mean',
        'embedding_similarity': 'mean',
        'topic_jaccard': ['mean', lambda x: (x > 0).mean()]  # Topic coverage rate
    }).T
    
    category_metrics.index = ['Combined Score', 'Embedding Sim', 'Topic Jaccard (mean)', 'Topic Coverage Rate']
    
    sns.heatmap(category_metrics, annot=True, fmt='.3f', cmap='YlGnBu', ax=ax, cbar_kws={'label': 'Score'})
    ax.set_title('Cultural Similarity Profile', fontsize=14, fontweight='bold')
    ax.set_xlabel('Cultural Category', fontsize=12)
    ax.set_ylabel('Metric', fontsize=12)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/cultural_similarity_heatmap.png', dpi=300, bbox_inches='tight')
    print(f"✅ Saved: cultural_similarity_heatmap.png")
    plt.close()
    
    # Figure 4: Bar chart with error bars
    fig, ax = plt.subplots(figsize=(10, 6))
    
    category_stats = df.groupby('category')['combined_score'].agg(['mean', 'std', 'count']).reset_index()
    category_stats['se'] = category_stats['std'] / np.sqrt(category_stats['count'])
    
    x_pos = np.arange(len(category_stats))
    ax.bar(x_pos, category_stats['mean'], yerr=category_stats['se'], 
           capsize=5, alpha=0.7, color='steelblue', edgecolor='black')
    
    ax.set_xticks(x_pos)
    ax.set_xticklabels(category_stats['category'], rotation=45, ha='right')
    ax.set_ylabel('Mean Combined Similarity Score', fontsize=12)
    ax.set_title('Cultural Similarity Hierarchy\n(Error bars = Standard Error)', 
                 fontsize=14, fontweight='bold')
    ax.grid(alpha=0.3, axis='y')
    
    # サンプルサイズを表示
    for i, row in category_stats.iterrows():
        ax.text(i, row['mean'] + row['se'] + 0.02, f'n={int(row["count"])}', 
                ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/cultural_hierarchy_bar.png', dpi=300, bbox_inches='tight')
    print(f"✅ Saved: cultural_hierarchy_bar.png")
    plt.close()

if __name__ == "__main__":
    analyze_cultural_similarity()
