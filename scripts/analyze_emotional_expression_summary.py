"""
感情表現分析の簡易版 - 論文用
既存のemoji分析結果を統合してレポート生成
"""

import pandas as pd
import os
import json
import re
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# 日本語フォント設定
import matplotlib
matplotlib.rcParams['font.family'] = 'sans-serif'
matplotlib.rcParams['font.sans-serif'] = ['Yu Gothic', 'Meiryo', 'MS Gothic', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

OUTPUT_DIR = 'output/emotional_analysis_summary'
os.makedirs(OUTPUT_DIR, exist_ok=True)

def analyze_emoji_rankings():
    """既存の絵文字ランキングデータを分析"""
    print("\n" + "="*80)
    print("📊 Analyzing Emoji Rankings...")
    print("="*80)
    
    emoji_csv = 'output/emoji_rankings/emoji_rankings.csv'
    
    if not os.path.exists(emoji_csv):
        print("❌ Emoji rankings CSV not found")
        return None
    
    df = pd.read_csv(emoji_csv, encoding='utf-8')
    print(f"✅ Loaded emoji rankings: {len(df)} rows")
    
    # 配信ごとの統計
    stream_stats = []
    for stream in df['stream'].unique():
        df_stream = df[df['stream'] == stream]
        
        # freq_1からfreq_10までの合計を計算
        freq_cols = [col for col in df_stream.columns if col.startswith('freq_')]
        total_count = df_stream[freq_cols].sum().sum()
        unique_emojis = sum(df_stream[freq_cols].notna().sum())
        
        # 国を推定（ファイル名から）
        if 'Japan' in stream or '【' in stream:
            country = 'Japan'
        elif 'Spain' in stream or 'MINUTO' in stream or 'REAL MADRID vs FC' in stream:
            country = 'Spain'
        elif 'UK' in stream or 'Real Madrid vs Barcelona' in stream:
            country = 'UK'
        elif 'France' in stream or 'BARCELONE' in stream:
            country = 'France'
        else:
            country = 'Unknown'
        
        stream_stats.append({
            'stream': stream,
            'country': country,
            'total_emoji_count': total_count,
            'unique_emojis': unique_emojis,
            'diversity': unique_emojis / total_count if total_count > 0 else 0
        })
    
    df_stats = pd.DataFrame(stream_stats)
    
    # 国別集計
    country_summary = df_stats.groupby('country').agg({
        'total_emoji_count': 'sum',
        'unique_emojis': 'mean',
        'diversity': 'mean'
    }).round(3)
    
    print("\n🌍 Country-level emoji statistics:")
    print(country_summary)
    
    # 保存
    output_file = os.path.join(OUTPUT_DIR, 'emoji_statistics_by_country.csv')
    country_summary.to_csv(output_file, encoding='utf-8-sig')
    print(f"✅ Saved: {output_file}")
    
    return df_stats, country_summary

def analyze_event_comments():
    """イベントコメントから感情表現を分析"""
    print("\n" + "="*80)
    print("📊 Analyzing Event Comments for Emotional Expression...")
    print("="*80)
    
    comments_json = 'output/event_comments.json'
    
    if not os.path.exists(comments_json):
        print("❌ Event comments JSON not found")
        return None
    
    with open(comments_json, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"✅ Loaded event comments: {len(data)} events")
    
    # 感情表現パターン
    patterns = {
        'exclamation': r'!+',
        'question': r'\?+',
        'laugh_w': r'w+',
        'laugh_lol': r'(?i)(lol|lmao|haha|jaja)',
        'caps': r'[A-Z]{3,}',
        'repeat': r'(.)\1{2,}'
    }
    
    stream_emotions = {}
    
    for event_id, event_data in data.items():
        for broadcaster, comments in event_data.items():
            if broadcaster not in stream_emotions:
                stream_emotions[broadcaster] = {
                    'total_comments': 0,
                    'exclamation': 0,
                    'question': 0,
                    'laugh_w': 0,
                    'laugh_lol': 0,
                    'caps': 0,
                    'repeat': 0
                }
            
            stream_emotions[broadcaster]['total_comments'] += len(comments)
            
            for comment in comments:
                for pattern_name, pattern in patterns.items():
                    if pd.notna(comment) and re.search(pattern, str(comment)):
                        stream_emotions[broadcaster][pattern_name] += 1
    
    # データフレーム化
    emotion_data = []
    for broadcaster, stats in stream_emotions.items():
        total = stats['total_comments']
        if total > 0:
            emotion_data.append({
                'broadcaster': broadcaster,
                'total_comments': total,
                'exclamation_rate': stats['exclamation'] / total,
                'question_rate': stats['question'] / total,
                'laugh_w_rate': stats['laugh_w'] / total,
                'laugh_lol_rate': stats['laugh_lol'] / total,
                'caps_rate': stats['caps'] / total,
                'repeat_rate': stats['repeat'] / total
            })
    
    df_emotions = pd.DataFrame(emotion_data)
    
    print(f"\n✅ Analyzed {len(df_emotions)} broadcasters")
    print("\nEmotional expression rates (mean):")
    print(df_emotions.drop(columns=['broadcaster', 'total_comments']).mean())
    
    # 保存
    output_file = os.path.join(OUTPUT_DIR, 'emotional_expression_by_broadcaster.csv')
    df_emotions.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"✅ Saved: {output_file}")
    
    return df_emotions

def create_summary_visualization(df_emoji_stats, country_summary, df_emotions):
    """感情表現のサマリー可視化"""
    print("\n" + "="*80)
    print("📊 Creating Summary Visualizations...")
    print("="*80)
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # 1. 国別絵文字使用量
    ax1 = axes[0, 0]
    if df_emoji_stats is not None:
        country_emoji = df_emoji_stats.groupby('country')['total_emoji_count'].sum().sort_values(ascending=False)
        ax1.bar(country_emoji.index, country_emoji.values, color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A'])
        ax1.set_title('Total Emoji Usage by Country', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Total Emoji Count', fontsize=12)
        ax1.set_xlabel('Country', fontsize=12)
        for i, v in enumerate(country_emoji.values):
            ax1.text(i, v + 100, f'{int(v):,}', ha='center', va='bottom', fontweight='bold')
    
    # 2. 国別絵文字多様性
    ax2 = axes[0, 1]
    if country_summary is not None:
        diversity = country_summary['diversity'].sort_values(ascending=False)
        ax2.bar(diversity.index, diversity.values, color=['#95E1D3', '#F38181', '#AA96DA', '#FCBAD3'])
        ax2.set_title('Emoji Diversity by Country', fontsize=14, fontweight='bold')
        ax2.set_ylabel('Diversity Score', fontsize=12)
        ax2.set_xlabel('Country', fontsize=12)
        for i, v in enumerate(diversity.values):
            ax2.text(i, v + 0.0001, f'{v:.4f}', ha='center', va='bottom', fontweight='bold')
    
    # 3. 感情表現率の比較
    ax3 = axes[1, 0]
    if df_emotions is not None:
        emotion_cols = ['exclamation_rate', 'laugh_w_rate', 'laugh_lol_rate', 'caps_rate']
        emotion_means = df_emotions[emotion_cols].mean()
        colors_emotion = ['#FF6B9D', '#C44569', '#FEA47F', '#25CCF7']
        ax3.barh(range(len(emotion_means)), emotion_means.values, color=colors_emotion)
        ax3.set_yticks(range(len(emotion_means)))
        ax3.set_yticklabels(['Exclamation (!)', 'Laugh (w)', 'Laugh (lol)', 'CAPS'], fontsize=11)
        ax3.set_title('Average Emotional Expression Rates', fontsize=14, fontweight='bold')
        ax3.set_xlabel('Rate (per comment)', fontsize=12)
        for i, v in enumerate(emotion_means.values):
            ax3.text(v + 0.01, i, f'{v:.3f}', va='center', fontweight='bold')
    
    # 4. 配信者別感情表現パターン
    ax4 = axes[1, 1]
    if df_emotions is not None and len(df_emotions) > 0:
        # Top 5配信者の感情表現プロファイル
        top_broadcasters = df_emotions.nlargest(5, 'total_comments')
        
        emotion_matrix = top_broadcasters[['exclamation_rate', 'laugh_w_rate', 'laugh_lol_rate', 'caps_rate']].T
        
        im = ax4.imshow(emotion_matrix.values, cmap='YlOrRd', aspect='auto')
        ax4.set_xticks(range(len(top_broadcasters)))
        ax4.set_xticklabels([b[:20] + '...' if len(b) > 20 else b 
                             for b in top_broadcasters['broadcaster']], 
                            rotation=45, ha='right', fontsize=9)
        ax4.set_yticks(range(len(emotion_matrix)))
        ax4.set_yticklabels(['Exclamation', 'Laugh (w)', 'Laugh (lol)', 'CAPS'], fontsize=11)
        ax4.set_title('Emotional Expression Profiles (Top 5 Broadcasters)', 
                     fontsize=14, fontweight='bold')
        
        # カラーバー
        plt.colorbar(im, ax=ax4, fraction=0.046, pad=0.04)
    
    plt.tight_layout()
    output_file = os.path.join(OUTPUT_DIR, 'emotional_expression_summary.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✅ Saved: {output_file}")
    plt.close()

def generate_report(df_emoji_stats, country_summary, df_emotions):
    """レポート生成"""
    print("\n" + "="*80)
    print("📝 Generating Report...")
    print("="*80)
    
    report = []
    report.append("# Emotional Expression Analysis Report")
    report.append("\n## Executive Summary\n")
    
    if df_emoji_stats is not None:
        report.append(f"- **Total Streams Analyzed**: {len(df_emoji_stats)}")
        report.append(f"- **Total Emoji Count**: {df_emoji_stats['total_emoji_count'].sum():,}")
        report.append(f"- **Average Unique Emojis per Stream**: {df_emoji_stats['unique_emojis'].mean():.1f}")
    
    if df_emotions is not None:
        report.append(f"- **Total Comments Analyzed**: {df_emotions['total_comments'].sum():,}")
        report.append(f"- **Broadcasters Analyzed**: {len(df_emotions)}")
    
    report.append("\n## Country-level Emoji Statistics\n")
    if country_summary is not None:
        report.append("```")
        report.append(str(country_summary))
        report.append("```")
    
    report.append("\n## Emotional Expression Patterns\n")
    if df_emotions is not None:
        emotion_summary = df_emotions.drop(columns=['broadcaster', 'total_comments']).describe()
        report.append("```")
        report.append(str(emotion_summary))
        report.append("```")
    
    report.append("\n## Key Findings\n")
    
    if country_summary is not None:
        top_emoji_country = country_summary['total_emoji_count'].idxmax()
        top_diversity_country = country_summary['diversity'].idxmax()
        report.append(f"1. **{top_emoji_country}** shows the highest total emoji usage")
        report.append(f"2. **{top_diversity_country}** has the most diverse emoji repertoire")
    
    if df_emotions is not None:
        top_exclamation = df_emotions.nlargest(1, 'exclamation_rate').iloc[0]
        top_laugh = df_emotions.nlargest(1, 'laugh_w_rate').iloc[0]
        report.append(f"3. Highest exclamation rate: **{top_exclamation['exclamation_rate']:.3f}**")
        report.append(f"4. Highest laugh (w) rate: **{top_laugh['laugh_w_rate']:.3f}**")
    
    report_text = '\n'.join(report)
    
    output_file = os.path.join(OUTPUT_DIR, 'EMOTIONAL_EXPRESSION_REPORT.md')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report_text)
    
    print(f"✅ Saved: {output_file}")
    print("\n" + report_text)

def main():
    print("="*80)
    print("🎭 Emotional Expression Analysis - Summary Version")
    print("="*80)
    
    # 1. 絵文字ランキング分析
    df_emoji_stats, country_summary = analyze_emoji_rankings()
    
    # 2. イベントコメント感情分析
    df_emotions = analyze_event_comments()
    
    # 3. 可視化
    create_summary_visualization(df_emoji_stats, country_summary, df_emotions)
    
    # 4. レポート生成
    generate_report(df_emoji_stats, country_summary, df_emotions)
    
    print("\n" + "="*80)
    print("✅ Emotional Expression Analysis Complete!")
    print(f"📁 Output directory: {OUTPUT_DIR}/")
    print("="*80)

if __name__ == '__main__':
    main()
