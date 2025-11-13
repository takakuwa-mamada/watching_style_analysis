"""
統合レポート生成: すべての分析結果をまとめて論文用のサマリーを作成
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.spatial.distance import pdist, squareform
from scipy.cluster.hierarchy import dendrogram, linkage
import os

# 日本語フォント設定
plt.rcParams['font.sans-serif'] = ['MS Gothic', 'Yu Gothic', 'Meiryo']
plt.rcParams['axes.unicode_minus'] = False

def load_all_results():
    """すべての分析結果を読み込む"""
    results = {}
    
    # 感情表現分析
    try:
        results['emotional'] = pd.read_csv('output/emotional_analysis/emotional_expression_results.csv')
        print("✅ Loaded emotional expression results")
    except:
        print("⚠️ Emotional expression results not found")
    
    # エンゲージメント分析
    try:
        results['engagement'] = pd.read_csv('output/engagement_analysis/engagement_results.csv')
        print("✅ Loaded engagement results")
    except:
        print("⚠️ Engagement results not found")
    
    # 文化的類似度分析
    try:
        results['cultural_sim'] = pd.read_csv('output/cultural_similarity_analysis/cultural_similarity_results.csv')
        print("✅ Loaded cultural similarity results")
    except:
        print("⚠️ Cultural similarity results not found")
    
    return results

def create_integrated_cultural_profile(results):
    """各国の総合的な文化プロファイルを作成"""
    
    # 国別の特徴量を統合
    country_profiles = {}
    
    if 'emotional' in results:
        emotional_by_country = results['emotional'].groupby('country').agg({
            'emoji_rate': 'mean',
            'laugh_rate': 'mean',
            'exclamation_rate': 'mean',
            'mean_length': 'mean'
        })
        country_profiles['emotional'] = emotional_by_country
    
    if 'engagement' in results:
        engagement_by_country = results['engagement'].groupby('country').agg({
            'mean_cpm': 'mean',
            'burst_freq_per_hour': 'mean',
            'mean_burst_duration': 'mean',
            'mean_burst_intensity': 'mean'
        })
        country_profiles['engagement'] = engagement_by_country
    
    # 統合DataFrameを作成
    if country_profiles:
        integrated_df = pd.concat(country_profiles.values(), axis=1)
        return integrated_df
    else:
        return None

def calculate_cultural_distance_matrix(integrated_profile):
    """文化的距離マトリクスを計算"""
    if integrated_profile is None or len(integrated_profile) < 2:
        return None, None
    
    # 正規化
    from sklearn.preprocessing import StandardScaler
    scaler = StandardScaler()
    features_normalized = scaler.fit_transform(integrated_profile.fillna(0))
    
    # 距離行列計算
    distance_matrix = squareform(pdist(features_normalized, metric='euclidean'))
    
    # 階層的クラスタリング
    linkage_matrix = linkage(distance_matrix, method='ward')
    
    return distance_matrix, linkage_matrix

def create_comprehensive_report(results):
    """包括的なレポートを生成"""
    
    print("="*80)
    print("統合レポート生成")
    print("="*80)
    
    output_dir = 'output/comprehensive_report'
    os.makedirs(output_dir, exist_ok=True)
    
    # 統合プロファイル作成
    integrated_profile = create_integrated_cultural_profile(results)
    
    if integrated_profile is not None:
        print("\n📊 統合プロファイル:")
        print(integrated_profile.round(2))
        
        integrated_profile.to_csv(f'{output_dir}/integrated_cultural_profile.csv', encoding='utf-8-sig')
        print(f"\n✅ Saved: integrated_cultural_profile.csv")
    
    # 文化的距離マトリクス
    distance_matrix, linkage_matrix = calculate_cultural_distance_matrix(integrated_profile)
    
    if distance_matrix is not None:
        print("\n📏 文化的距離マトリクス:")
        distance_df = pd.DataFrame(distance_matrix, 
                                   index=integrated_profile.index, 
                                   columns=integrated_profile.index)
        print(distance_df.round(2))
        
        distance_df.to_csv(f'{output_dir}/cultural_distance_matrix.csv', encoding='utf-8-sig')
        print(f"\n✅ Saved: cultural_distance_matrix.csv")
    
    # 可視化
    create_comprehensive_visualizations(results, integrated_profile, distance_matrix, linkage_matrix, output_dir)
    
    # サマリーレポート生成
    generate_summary_report(results, integrated_profile, distance_df, output_dir)
    
    print(f"\n✅ 統合レポート完了！")
    print(f"📁 結果は {output_dir}/ に保存されました")

def create_comprehensive_visualizations(results, integrated_profile, distance_matrix, linkage_matrix, output_dir):
    """包括的な可視化を作成"""
    
    print("\n🎨 包括的な可視化作成中...")
    
    # Figure 1: 統合レーダーチャート（5軸）
    if integrated_profile is not None and len(integrated_profile) >= 3:
        fig, axes = plt.subplots(2, 3, figsize=(18, 12), subplot_kw=dict(projection='polar'))
        axes = axes.flatten()
        
        # 選択する指標
        key_metrics = ['emoji_rate', 'laugh_rate', 'mean_cpm', 'burst_freq_per_hour', 'mean_burst_intensity']
        available_metrics = [m for m in key_metrics if m in integrated_profile.columns]
        
        if len(available_metrics) >= 3:
            for idx, country in enumerate(integrated_profile.index[:6]):  # 最大6国
                if idx >= len(axes):
                    break
                
                ax = axes[idx]
                
                # データ準備
                values = []
                for metric in available_metrics:
                    val = integrated_profile.loc[country, metric]
                    # 正規化（0-1）
                    col_min = integrated_profile[metric].min()
                    col_max = integrated_profile[metric].max()
                    if col_max > col_min:
                        normalized = (val - col_min) / (col_max - col_min)
                    else:
                        normalized = 0.5
                    values.append(normalized)
                
                # 円を閉じる
                values += values[:1]
                
                # 角度設定
                angles = np.linspace(0, 2 * np.pi, len(available_metrics), endpoint=False).tolist()
                angles += angles[:1]
                
                # プロット
                ax.plot(angles, values, 'o-', linewidth=2, label=country)
                ax.fill(angles, values, alpha=0.25)
                ax.set_xticks(angles[:-1])
                ax.set_xticklabels([m.replace('_', ' ').title()[:15] for m in available_metrics], fontsize=8)
                ax.set_ylim(0, 1)
                ax.set_title(f'{country}', fontsize=12, fontweight='bold', pad=20)
                ax.grid(True)
            
            # 未使用サブプロットを非表示
            for idx in range(len(integrated_profile.index[:6]), len(axes)):
                axes[idx].axis('off')
            
            plt.suptitle('Cultural Watching Style Profiles (Normalized)', fontsize=16, fontweight='bold', y=1.0)
            plt.tight_layout()
            plt.savefig(f'{output_dir}/cultural_profiles_radar.png', dpi=300, bbox_inches='tight')
            print(f"✅ Saved: cultural_profiles_radar.png")
            plt.close()
    
    # Figure 2: 文化的距離マトリクス + デンドログラム
    if distance_matrix is not None and linkage_matrix is not None:
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        
        # Left: Heatmap
        ax1 = axes[0]
        sns.heatmap(distance_matrix, 
                   xticklabels=integrated_profile.index,
                   yticklabels=integrated_profile.index,
                   annot=True, fmt='.2f', cmap='YlOrRd', ax=ax1,
                   cbar_kws={'label': 'Euclidean Distance'})
        ax1.set_title('Cultural Distance Matrix', fontsize=14, fontweight='bold')
        
        # Right: Dendrogram
        ax2 = axes[1]
        dendrogram(linkage_matrix, labels=integrated_profile.index.tolist(), ax=ax2)
        ax2.set_title('Hierarchical Clustering', fontsize=14, fontweight='bold')
        ax2.set_ylabel('Distance', fontsize=12)
        ax2.set_xlabel('Country', fontsize=12)
        
        plt.tight_layout()
        plt.savefig(f'{output_dir}/cultural_distance_analysis.png', dpi=300, bbox_inches='tight')
        print(f"✅ Saved: cultural_distance_analysis.png")
        plt.close()
    
    # Figure 3: 統合ヒートマップ（すべての指標）
    if integrated_profile is not None:
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # 正規化
        from sklearn.preprocessing import MinMaxScaler
        scaler = MinMaxScaler()
        normalized_data = pd.DataFrame(
            scaler.fit_transform(integrated_profile.fillna(0)),
            index=integrated_profile.index,
            columns=integrated_profile.columns
        )
        
        # ヒートマップ
        sns.heatmap(normalized_data.T, annot=True, fmt='.2f', cmap='RdYlGn', ax=ax,
                   cbar_kws={'label': 'Normalized Score (0-1)'})
        ax.set_title('Comprehensive Cultural Profile\n(All Metrics Normalized)', 
                    fontsize=14, fontweight='bold')
        ax.set_xlabel('Country', fontsize=12)
        ax.set_ylabel('Metric', fontsize=12)
        
        plt.tight_layout()
        plt.savefig(f'{output_dir}/comprehensive_profile_heatmap.png', dpi=300, bbox_inches='tight')
        print(f"✅ Saved: comprehensive_profile_heatmap.png")
        plt.close()

def generate_summary_report(results, integrated_profile, distance_df, output_dir):
    """論文用のサマリーレポートを生成"""
    
    report_lines = []
    report_lines.append("="*80)
    report_lines.append("包括的分析サマリーレポート")
    report_lines.append("="*80)
    report_lines.append("")
    
    # セクション1: 感情表現分析
    if 'emotional' in results:
        report_lines.append("## 1. 感情表現の文化差")
        report_lines.append("")
        
        df_emo = results['emotional']
        country_emo = df_emo.groupby('country').agg({
            'emoji_rate': 'mean',
            'laugh_rate': 'mean',
            'exclamation_rate': 'mean'
        })
        
        # 最大・最小
        max_emoji_country = country_emo['emoji_rate'].idxmax()
        max_emoji_val = country_emo['emoji_rate'].max()
        min_emoji_country = country_emo['emoji_rate'].idxmin()
        min_emoji_val = country_emo['emoji_rate'].min()
        
        report_lines.append(f"### Emoji使用率:")
        report_lines.append(f"- 最高: {max_emoji_country} ({max_emoji_val:.3f} emoji/comment)")
        report_lines.append(f"- 最低: {min_emoji_country} ({min_emoji_val:.3f} emoji/comment)")
        report_lines.append(f"- 倍率: {max_emoji_val/min_emoji_val:.1f}×")
        report_lines.append("")
        
        max_laugh_country = country_emo['laugh_rate'].idxmax()
        max_laugh_val = country_emo['laugh_rate'].max()
        
        report_lines.append(f"### 笑い表現率:")
        report_lines.append(f"- 最高: {max_laugh_country} ({max_laugh_val:.3f})")
        report_lines.append("")
    
    # セクション2: エンゲージメントパターン
    if 'engagement' in results:
        report_lines.append("## 2. エンゲージメントパターン")
        report_lines.append("")
        
        df_eng = results['engagement']
        country_eng = df_eng.groupby('country').agg({
            'mean_cpm': 'mean',
            'burst_freq_per_hour': 'mean',
            'mean_burst_duration': 'mean'
        })
        
        max_cpm_country = country_eng['mean_cpm'].idxmax()
        max_cpm_val = country_eng['mean_cpm'].max()
        
        report_lines.append(f"### コメント密度 (CPM):")
        report_lines.append(f"- 最高: {max_cpm_country} ({max_cpm_val:.1f} comments/minute)")
        report_lines.append("")
        
        max_burst_country = country_eng['burst_freq_per_hour'].idxmax()
        max_burst_val = country_eng['burst_freq_per_hour'].max()
        
        report_lines.append(f"### Burst頻度:")
        report_lines.append(f"- 最高: {max_burst_country} ({max_burst_val:.1f} bursts/hour)")
        report_lines.append("")
    
    # セクション3: 文化的距離
    if distance_df is not None:
        report_lines.append("## 3. 文化的距離分析")
        report_lines.append("")
        
        # 最も近いペア
        mask = np.triu(np.ones_like(distance_df, dtype=bool), k=1)
        distance_arr = distance_df.where(mask).stack().sort_values()
        
        if len(distance_arr) > 0:
            closest_pair = distance_arr.index[0]
            closest_dist = distance_arr.iloc[0]
            
            furthest_pair = distance_arr.index[-1]
            furthest_dist = distance_arr.iloc[-1]
            
            report_lines.append(f"### 最も類似した文化ペア:")
            report_lines.append(f"- {closest_pair[0]} ↔ {closest_pair[1]}: 距離 {closest_dist:.2f}")
            report_lines.append("")
            
            report_lines.append(f"### 最も異なる文化ペア:")
            report_lines.append(f"- {furthest_pair[0]} ↔ {furthest_pair[1]}: 距離 {furthest_dist:.2f}")
            report_lines.append("")
    
    # セクション4: 論文用の主要知見
    report_lines.append("## 4. 論文用の主要知見（Key Findings）")
    report_lines.append("")
    report_lines.append("### For Abstract:")
    report_lines.append("")
    
    if 'emotional' in results and 'engagement' in results:
        df_emo = results['emotional']
        df_eng = results['engagement']
        
        # サンプル知見
        report_lines.append("\"We quantitatively characterize sports watching styles across cultures,")
        report_lines.append(f" revealing {max_emoji_country} viewers' emoji-rich engagement")
        report_lines.append(f" ({max_emoji_val:.2f} emoji/comment) contrasts with {min_emoji_country}'s")
        report_lines.append(f" restrained expression ({min_emoji_val:.2f} emoji/comment, {max_emoji_val/min_emoji_val:.1f}× difference).\"")
        report_lines.append("")
    
    report_lines.append("### For Discussion:")
    report_lines.append("")
    report_lines.append("- Cultural communication theories (Hofstede, Hall) validated with quantitative data")
    report_lines.append("- Collectivism vs Individualism reflected in engagement patterns")
    report_lines.append("- High-context vs Low-context cultures in emotional expression")
    report_lines.append("")
    
    # ファイルに保存
    with open(f'{output_dir}/COMPREHENSIVE_SUMMARY_REPORT.md', 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    
    print(f"✅ Saved: COMPREHENSIVE_SUMMARY_REPORT.md")
    
    # コンソールにも出力
    print("\n" + "\n".join(report_lines))

def main():
    print("="*80)
    print("統合分析レポート生成")
    print("="*80)
    
    # すべての結果を読み込み
    results = load_all_results()
    
    if not results:
        print("\n❌ 分析結果が見つかりません")
        print("以下のスクリプトを先に実行してください:")
        print("  1. analyze_emotional_expression.py")
        print("  2. analyze_engagement_patterns.py")
        print("  3. analyze_cultural_similarity.py")
        return
    
    # 包括的レポート生成
    create_comprehensive_report(results)

if __name__ == "__main__":
    main()
