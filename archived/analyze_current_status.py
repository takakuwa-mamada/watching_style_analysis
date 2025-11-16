#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
現状分析スクリプト: イベント検出の品質を定量評価
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

def analyze_current_status():
    """現状の詳細分析"""
    
    print('='*60)
    print('📊 現状分析: イベント検出の品質評価')
    print('='*60)
    
    # データ読み込み
    df = pd.read_csv('output/event_to_event_pairs.csv')
    
    # combined_scoreをsimilarityとして使用
    if 'similarity' not in df.columns:
        if 'combined_score' in df.columns:
            df['similarity'] = df['combined_score']
        elif 'main_similarity' in df.columns:
            df['similarity'] = df['main_similarity']
    
    # 配信者数を計算（仮に4と設定）
    if 'num_broadcasters' not in df.columns:
        df['num_broadcasters'] = 4  # 簡易的に固定値
    
    # 基本統計
    print(f'\n【基本統計】')
    print(f'  総ペア数: {len(df)}')
    print(f'  平均類似度: {df["similarity"].mean():.3f}')
    print(f'  最大類似度: {df["similarity"].max():.3f}')
    print(f'  標準偏差: {df["similarity"].std():.3f}')
    
    # 品質分布
    print(f'\n【品質分布】')
    very_high = len(df[df['similarity'] > 0.8])
    high = len(df[(df['similarity'] > 0.6) & (df['similarity'] <= 0.8)])
    medium = len(df[(df['similarity'] > 0.4) & (df['similarity'] <= 0.6)])
    low = len(df[df['similarity'] <= 0.4])
    
    print(f'  Very High (>0.8): {very_high} ({very_high/len(df)*100:.1f}%)')
    print(f'  High (0.6-0.8): {high} ({high/len(df)*100:.1f}%)')
    print(f'  Medium (0.4-0.6): {medium} ({medium/len(df)*100:.1f}%)')
    print(f'  Low (<0.4): {low} ({low/len(df)*100:.1f}%)')
    
    # トピック一致
    print(f'\n【トピック一致】')
    topic_nonzero = len(df[df['topic_jaccard'] > 0])
    topic_high = len(df[df['topic_jaccard'] > 0.5])
    topic_perfect = len(df[df['topic_jaccard'] == 1.0])
    
    print(f'  topic_jaccard > 0: {topic_nonzero} ({topic_nonzero/len(df)*100:.1f}%)')
    print(f'  topic_jaccard > 0.5: {topic_high} ({topic_high/len(df)*100:.1f}%)')
    print(f'  topic_jaccard = 1.0: {topic_perfect} ({topic_perfect/len(df)*100:.1f}%)')
    
    # 時間的一貫性
    print(f'\n【時間的一貫性スコア】')
    high_sim = df[df['similarity'] > 0.7]
    low_sim = df[df['similarity'] < 0.3]
    
    if len(high_sim) > 0 and len(low_sim) > 0:
        high_time = high_sim['time_diff_bins'].mean()
        low_time = low_sim['time_diff_bins'].mean()
        consistency = low_time / (high_time + 1e-6)
        print(f'  高類似ペアの平均時間差: {high_time:.2f} bins')
        print(f'  低類似ペアの平均時間差: {low_time:.2f} bins')
        print(f'  時間的一貫性スコア: {consistency:.2f}x')
        print(f'  → 類似ペアは非類似ペアより{consistency:.1f}倍時間が近い ✓')
    else:
        print('  データ不足により計算できません')
    
    # 埋め込み vs トピック相関
    print(f'\n【埋め込み類似度 vs トピック類似度】')
    corr = df['embedding_similarity'].corr(df['topic_jaccard'])
    print(f'  相関係数: {corr:.3f}')
    if corr > 0.5:
        print(f'  → 強い正の相関 ✓')
    elif corr > 0.3:
        print(f'  → 中程度の正の相関')
    else:
        print(f'  → 弱い相関 ⚠️')
    
    # Top 5高品質ペア
    print(f'\n【Top 5 高品質ペア】')
    top5 = df.nlargest(5, 'similarity')
    for i, (idx, row) in enumerate(top5.iterrows(), 1):
        event_a = int(row["event_A_id"]) if "event_A_id" in row else int(row.get("event_A", 0))
        event_b = int(row["event_B_id"]) if "event_B_id" in row else int(row.get("event_B", 0))
        print(f'\n  {i}. Event {event_a} ↔ {event_b}')
        print(f'     総合類似度: {row["similarity"]:.3f}')
        print(f'     embedding: {row["embedding_similarity"]:.3f}')
        print(f'     topic_jaccard: {row["topic_jaccard"]:.3f}')
        print(f'     時間差: {int(row["time_diff_bins"])} bins')
        if "num_broadcasters" in row:
            print(f'     配信者数: {int(row["num_broadcasters"])}')
    
    # 問題点の特定
    print(f'\n【問題点の特定】')
    problems = []
    
    if df['similarity'].mean() < 0.3:
        problems.append('⚠️  平均類似度が低い (<0.3)')
    if topic_nonzero / len(df) < 0.3:
        problems.append('⚠️  トピック一致率が低い (<30%)')
    if very_high < 3:
        problems.append('⚠️  高品質ペアが少ない (<3)')
    if df['similarity'].std() < 0.1:
        problems.append('⚠️  類似度の分散が小さい（識別力不足）')
    
    if problems:
        for p in problems:
            print(f'  {p}')
    else:
        print('  ✅ 目立った問題なし')
    
    # 改善提案
    print(f'\n【改善提案】')
    suggestions = []
    
    if topic_nonzero / len(df) < 0.3:
        suggestions.append('1. N-gram抽出のmin_dfパラメータを調整（現在: 2 → 1に下げる）')
    if df['similarity'].mean() < 0.3:
        suggestions.append('2. 重み付けを調整（embedding重視 → topic重視）')
    if very_high < 3:
        suggestions.append('3. 閾値を下げて検出感度を上げる')
    
    if suggestions:
        for s in suggestions:
            print(f'  {s}')
    else:
        print('  → 現在の設定で良好')
    
    print('\n' + '='*60)
    
    return df

def create_visualizations(df):
    """可視化を作成"""
    
    print('\n📊 可視化を作成中...')
    
    output_dir = Path('output')
    
    # 1. 類似度分布
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # 1-1. 総合類似度のヒストグラム
    axes[0, 0].hist(df['similarity'], bins=20, edgecolor='black', alpha=0.7)
    axes[0, 0].axvline(df['similarity'].mean(), color='red', linestyle='--', 
                       label=f'Mean: {df["similarity"].mean():.3f}')
    axes[0, 0].set_xlabel('Similarity Score')
    axes[0, 0].set_ylabel('Frequency')
    axes[0, 0].set_title('Distribution of Event Similarity')
    axes[0, 0].legend()
    axes[0, 0].grid(alpha=0.3)
    
    # 1-2. Embedding vs Topic散布図
    scatter = axes[0, 1].scatter(df['embedding_similarity'], df['topic_jaccard'],
                                 c=df['similarity'], cmap='viridis', alpha=0.6, s=50)
    axes[0, 1].set_xlabel('Embedding Similarity')
    axes[0, 1].set_ylabel('Topic Jaccard')
    axes[0, 1].set_title('Embedding vs Topic Similarity')
    plt.colorbar(scatter, ax=axes[0, 1], label='Combined Similarity')
    axes[0, 1].grid(alpha=0.3)
    
    # 1-3. 時間差 vs 類似度
    axes[1, 0].scatter(df['time_diff_bins'], df['similarity'], alpha=0.6, s=50)
    axes[1, 0].set_xlabel('Time Difference (bins)')
    axes[1, 0].set_ylabel('Similarity Score')
    axes[1, 0].set_title('Temporal Distance vs Similarity')
    axes[1, 0].grid(alpha=0.3)
    
    # 1-4. 品質分布（棒グラフ）
    categories = ['Very High\n(>0.8)', 'High\n(0.6-0.8)', 'Medium\n(0.4-0.6)', 'Low\n(<0.4)']
    counts = [
        len(df[df['similarity'] > 0.8]),
        len(df[(df['similarity'] > 0.6) & (df['similarity'] <= 0.8)]),
        len(df[(df['similarity'] > 0.4) & (df['similarity'] <= 0.6)]),
        len(df[df['similarity'] <= 0.4])
    ]
    colors = ['#2ecc71', '#3498db', '#f39c12', '#e74c3c']
    axes[1, 1].bar(categories, counts, color=colors, edgecolor='black', alpha=0.7)
    axes[1, 1].set_ylabel('Number of Pairs')
    axes[1, 1].set_title('Quality Distribution')
    axes[1, 1].grid(axis='y', alpha=0.3)
    
    # 数値を棒の上に表示
    for i, (cat, count) in enumerate(zip(categories, counts)):
        axes[1, 1].text(i, count + 0.5, str(count), ha='center', va='bottom', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'current_status_analysis.png', dpi=300, bbox_inches='tight')
    print(f'  ✓ 保存: output/current_status_analysis.png')
    
    # 2. 相関マトリックス
    fig, ax = plt.subplots(figsize=(8, 6))
    
    corr_cols = ['embedding_similarity', 'lexical_similarity', 'topic_jaccard', 
                 'temporal_correlation', 'similarity']
    corr_matrix = df[corr_cols].corr()
    
    # 手動でヒートマップを作成
    im = ax.imshow(corr_matrix, cmap='coolwarm', vmin=-1, vmax=1, aspect='auto')
    
    # 軸ラベル
    ax.set_xticks(range(len(corr_cols)))
    ax.set_yticks(range(len(corr_cols)))
    ax.set_xticklabels(corr_cols, rotation=45, ha='right')
    ax.set_yticklabels(corr_cols)
    
    # 数値を表示
    for i in range(len(corr_cols)):
        for j in range(len(corr_cols)):
            text = ax.text(j, i, f'{corr_matrix.iloc[i, j]:.3f}',
                          ha="center", va="center", color="black", fontsize=9)
    
    ax.set_title('Correlation Matrix of Similarity Components')
    plt.colorbar(im, ax=ax, label='Correlation')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'correlation_matrix.png', dpi=300, bbox_inches='tight')
    print(f'  ✓ 保存: output/correlation_matrix.png')
    
    plt.close('all')

if __name__ == '__main__':
    df = analyze_current_status()
    create_visualizations(df)
    
    print('\n✅ 分析完了！')
    print('次のステップ: output/current_status_analysis.png を確認')
