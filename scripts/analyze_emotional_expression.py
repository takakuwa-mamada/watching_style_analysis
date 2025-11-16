"""
軸2: 感情表現の文化差分析
Emoji、onomatopoeia、exclamationなどの感情表現の地域差を定量化
"""

import pandas as pd
import numpy as np
import emoji
import re
from collections import Counter
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import kruskal, mannwhitneyu
import os

# 日本語フォント設定
plt.rcParams['font.sans-serif'] = ['MS Gothic', 'Yu Gothic', 'Meiryo']
plt.rcParams['axes.unicode_minus'] = False

def load_comments(stream_file):
    """コメントデータを読み込む"""
    file_path = f"data/chat/{stream_file}"
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
        # カラム名の確認と調整
        if 'message' in df.columns:
            comments = df['message'].astype(str).tolist()
        elif 'text' in df.columns:
            comments = df['text'].astype(str).tolist()
        elif 'comment' in df.columns:
            comments = df['comment'].astype(str).tolist()
        else:
            # 最初のテキスト列を使用
            text_cols = df.select_dtypes(include=['object']).columns
            if len(text_cols) > 0:
                comments = df[text_cols[0]].astype(str).tolist()
            else:
                print(f"Warning: No text column found in {stream_file}")
                return []
        
        # nanを除外
        comments = [c for c in comments if c != 'nan' and len(c) > 0]
        return comments
    except Exception as e:
        print(f"Error loading {stream_file}: {e}")
        return []

def analyze_emoji_usage(comments):
    """Emoji使用率と多様性を分析"""
    emoji_counts = []
    all_emojis = []
    
    for comment in comments:
        emoji_list = emoji.emoji_list(comment)
        emoji_counts.append(len(emoji_list))
        all_emojis.extend([e['emoji'] for e in emoji_list])
    
    emoji_rate = sum(emoji_counts) / len(comments) if comments else 0
    emoji_diversity = len(set(all_emojis))
    top_emojis = Counter(all_emojis).most_common(5) if all_emojis else []
    
    return {
        'emoji_rate': emoji_rate,
        'emoji_diversity': emoji_diversity,
        'top_emojis': top_emojis,
        'total_emojis': sum(emoji_counts)
    }

def analyze_laughter(comments, region):
    """笑いの表現を分析"""
    laugh_patterns = {
        'Brazil': r'k{3,}|rs{2,}|hue+|ha{3,}',
        'Japan': r'w{3,}|草+|笑+|ワロ',
        'UK': r'lol|haha+|lmao|rofl|lmfao',
        'France': r'mdr|ptdr|lol',
        'Spain': r'jaja+|jeje+|jiji+',
        'India': r'lol|haha+|lmao'
    }
    
    pattern = laugh_patterns.get(region, r'lol|haha+')
    
    laugh_matches = []
    for comment in comments:
        matches = re.findall(pattern, comment.lower())
        if matches:
            laugh_matches.extend(matches)
    
    laugh_rate = len([c for c in comments if re.search(pattern, c.lower())]) / len(comments) if comments else 0
    laugh_lengths = [len(match) for match in laugh_matches]
    avg_laugh_length = np.mean(laugh_lengths) if laugh_lengths else 0
    
    return {
        'laugh_rate': laugh_rate,
        'laugh_mean_length': avg_laugh_length,
        'laugh_total_count': len(laugh_matches)
    }

def analyze_exclamation(comments):
    """Exclamation（!）の使用を分析"""
    exclamation_counts = [comment.count('!') for comment in comments]
    exclamation_rate = sum(exclamation_counts) / len(comments) if comments else 0
    
    # ALL CAPSの使用
    caps_words = []
    for comment in comments:
        caps_found = re.findall(r'\b[A-Z]{3,}\b', comment)
        caps_words.extend(caps_found)
    
    caps_rate = len(caps_words) / len(comments) if comments else 0
    
    # Question marks
    question_counts = [comment.count('?') for comment in comments]
    question_rate = sum(question_counts) / len(comments) if comments else 0
    
    return {
        'exclamation_rate': exclamation_rate,
        'caps_rate': caps_rate,
        'question_rate': question_rate
    }

def analyze_comment_length(comments):
    """コメントの長さを分析"""
    lengths = [len(comment) for comment in comments]
    return {
        'mean_length': np.mean(lengths) if lengths else 0,
        'std_length': np.std(lengths) if lengths else 0,
        'median_length': np.median(lengths) if lengths else 0
    }

def get_broadcaster_mapping():
    """ファイル名からbroadcaster情報へのマッピング"""
    return {
        # El Clasico streams
        '⏱️ MINUTO A MINUTO _ Real Madrid vs Barcelona _ El Clásico_chat_log.csv': {
            'name': 'Spain_1',
            'country': 'Spain',
            'language': 'Spanish',
            'region': 'Europe'
        },
        '⚽️ REAL MADRID vs FC BARCELONA _ #LaLiga 25_26 - Jornada 10 _ \'EL CLÁSICO\' EN DIRECTO_chat_log.csv': {
            'name': 'Spain_2',
            'country': 'Spain',
            'language': 'Spanish',
            'region': 'Europe'
        },
        'REAL MADRID VS FC BARCELONA EN DIRECTO _ EL CLASICO _ LALIGA _ Tiempo de Juego COPE _ EN VIVO_chat_log.csv': {
            'name': 'Spain_3',
            'country': 'Spain',
            'language': 'Spanish',
            'region': 'Europe'
        },
        '【エルクラシコ】レアルマドリード×バルセロナ 0_15キックオフ リアルタイム戦術分析_chat_log.csv': {
            'name': 'Japan_1',
            'country': 'Japan',
            'language': 'Japanese',
            'region': 'Asia'
        },
        '【LIVE分析】レアルマドリードvsバルセロナ　▷ラ・リーガ｜第10節　エルクラシコ_chat_log.csv': {
            'name': 'Japan_2',
            'country': 'Japan',
            'language': 'Japanese',
            'region': 'Asia'
        },
        'Real Madrid vs Barcelona _EL CLASICO_ Laliga 2025 Live Reaction_chat_log.csv': {
            'name': 'UK_1',
            'country': 'UK',
            'language': 'English',
            'region': 'Europe'
        },
        'Real Madrid vs Barcelona _ La Liga LIVE WATCHALONG_chat_log.csv': {
            'name': 'UK_2',
            'country': 'UK',
            'language': 'English',
            'region': 'Europe'
        },
        'REAL MADRID VS BARCELONA _ EL CLASICO LIVE REACTION!_chat_log.csv': {
            'name': 'UK_3',
            'country': 'UK',
            'language': 'English',
            'region': 'Europe'
        },
        'Real Madrid vs Barcelona El Clasico Watchalong LaLiga LIVE _ TFHD_chat_log.csv': {
            'name': 'UK_4',
            'country': 'UK',
            'language': 'English',
            'region': 'Europe'
        },
        '🔴 REAL MADRID - BARCELONE LIVE _ 🚨LE CLASICO POUR LA 1ERE PLACE ! _ 🔥PLACE AU SPECTACLE ! _ LIGA_chat_log.csv': {
            'name': 'France',
            'country': 'France',
            'language': 'French',
            'region': 'Europe'
        },
        # Baseball streams
        'Dodgers_WhiteSox_Japan.csv': {
            'name': 'Japan_Baseball',
            'country': 'Japan',
            'language': 'Japanese',
            'region': 'Asia'
        },
        'Dodgers_WhiteSox_US.csv': {
            'name': 'US_Baseball',
            'country': 'USA',
            'language': 'English',
            'region': 'North America'
        },
        'Dodgers_WhiteSox_Dominican.csv': {
            'name': 'Dominican_Baseball',
            'country': 'Dominican',
            'language': 'Spanish',
            'region': 'Latin America'
        }
    }

def main():
    print("="*80)
    print("軸2: 感情表現の文化差分析")
    print("="*80)
    
    # ファイルマッピング取得
    file_mapping = get_broadcaster_mapping()
    
    # 分析結果を格納
    all_results = []
    
    print("\n📊 各配信の分析開始...\n")
    
    for filename, info in file_mapping.items():
        print(f"Processing: {info['name']} ({info['country']})...")
        
        # コメント読み込み
        comments = load_comments(filename)
        
        if not comments:
            print(f"  ⚠️ No comments found")
            continue
        
        print(f"  Total comments: {len(comments)}")
        
        # 各種分析
        emoji_results = analyze_emoji_usage(comments)
        laugh_results = analyze_laughter(comments, info['country'])
        exclamation_results = analyze_exclamation(comments)
        length_results = analyze_comment_length(comments)
        
        # 結果統合
        result = {
            'broadcaster': info['name'],
            'country': info['country'],
            'language': info['language'],
            'region': info['region'],
            'total_comments': len(comments),
            **emoji_results,
            **laugh_results,
            **exclamation_results,
            **length_results
        }
        
        all_results.append(result)
        
        print(f"  ✅ Emoji rate: {emoji_results['emoji_rate']:.3f}")
        print(f"  ✅ Laugh rate: {laugh_results['laugh_rate']:.3f}")
        print(f"  ✅ Exclamation rate: {exclamation_results['exclamation_rate']:.3f}")
        print()
    
    # DataFrameに変換
    df_results = pd.DataFrame(all_results)
    
    # 結果を保存
    output_dir = 'output/emotional_analysis'
    os.makedirs(output_dir, exist_ok=True)
    
    df_results.to_csv(f'{output_dir}/emotional_expression_results.csv', index=False, encoding='utf-8-sig')
    print(f"✅ Results saved to {output_dir}/emotional_expression_results.csv")
    
    # 国別に集計
    print("\n" + "="*80)
    print("📊 国別集計結果")
    print("="*80)
    
    country_summary = df_results.groupby('country').agg({
        'emoji_rate': ['mean', 'std'],
        'laugh_rate': ['mean', 'std'],
        'exclamation_rate': ['mean', 'std'],
        'mean_length': ['mean', 'std']
    }).round(3)
    
    print(country_summary)
    
    # 統計的検定
    print("\n" + "="*80)
    print("📈 統計的検定")
    print("="*80)
    
    countries = df_results['country'].unique()
    
    if len(countries) >= 3:
        # Kruskal-Wallis test
        for metric in ['emoji_rate', 'laugh_rate', 'exclamation_rate', 'mean_length']:
            groups = [df_results[df_results['country'] == c][metric].values for c in countries]
            groups = [g for g in groups if len(g) > 0]
            
            if len(groups) >= 2:
                h_stat, p_value = kruskal(*groups)
                print(f"\n{metric}:")
                print(f"  Kruskal-Wallis H = {h_stat:.3f}, p = {p_value:.4f}")
                
                if p_value < 0.05:
                    print(f"  ✅ Significant difference detected!")
                else:
                    print(f"  ❌ No significant difference")
    
    # 可視化
    print("\n" + "="*80)
    print("🎨 可視化作成中...")
    print("="*80)
    
    create_visualizations(df_results, output_dir)
    
    print("\n✅ 分析完了！")
    print(f"📁 結果は {output_dir}/ に保存されました")

def create_visualizations(df, output_dir):
    """可視化を作成"""
    
    # 国別に平均を計算
    country_means = df.groupby('country').agg({
        'emoji_rate': 'mean',
        'laugh_rate': 'mean',
        'exclamation_rate': 'mean',
        'mean_length': 'mean',
        'emoji_diversity': 'mean'
    }).reset_index()
    
    # Figure 1: 4つのメトリクスの比較
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    metrics = [
        ('emoji_rate', 'Emoji Usage Rate (emoji/comment)', axes[0, 0]),
        ('laugh_rate', 'Laughter Expression Rate', axes[0, 1]),
        ('exclamation_rate', 'Exclamation Rate (!/comment)', axes[1, 0]),
        ('mean_length', 'Mean Comment Length (characters)', axes[1, 1])
    ]
    
    for metric, title, ax in metrics:
        # Barplot
        sns.barplot(data=df, x='country', y=metric, ax=ax, palette='Set2', errorbar='sd')
        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.set_xlabel('Country', fontsize=10)
        ax.set_ylabel(title.split('(')[0].strip(), fontsize=10)
        ax.tick_params(axis='x', rotation=45)
        
        # データポイントを追加
        for i, country in enumerate(df['country'].unique()):
            values = df[df['country'] == country][metric].values
            x_positions = np.random.normal(i, 0.04, size=len(values))
            ax.scatter(x_positions, values, alpha=0.5, color='black', s=20)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/emotional_expression_comparison.png', dpi=300, bbox_inches='tight')
    print(f"✅ Saved: emotional_expression_comparison.png")
    plt.close()
    
    # Figure 2: Emoji多様性と使用率
    fig, ax = plt.subplots(figsize=(10, 6))
    
    for country in df['country'].unique():
        country_data = df[df['country'] == country]
        ax.scatter(country_data['emoji_rate'], 
                  country_data['emoji_diversity'],
                  label=country, s=100, alpha=0.7)
    
    ax.set_xlabel('Emoji Rate (emoji/comment)', fontsize=12)
    ax.set_ylabel('Emoji Diversity (unique emoji types)', fontsize=12)
    ax.set_title('Emoji Usage: Rate vs Diversity', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/emoji_rate_vs_diversity.png', dpi=300, bbox_inches='tight')
    print(f"✅ Saved: emoji_rate_vs_diversity.png")
    plt.close()
    
    # Figure 3: Heatmap（国別の特徴）
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # 正規化（0-1スケール）
    metrics_for_heatmap = ['emoji_rate', 'laugh_rate', 'exclamation_rate', 'mean_length', 'emoji_diversity']
    heatmap_data = country_means[metrics_for_heatmap]
    heatmap_data_normalized = (heatmap_data - heatmap_data.min()) / (heatmap_data.max() - heatmap_data.min())
    heatmap_data_normalized.index = country_means['country']
    
    sns.heatmap(heatmap_data_normalized.T, annot=True, fmt='.2f', cmap='YlOrRd', 
                cbar_kws={'label': 'Normalized Score (0-1)'}, ax=ax)
    ax.set_title('Cultural Emotional Expression Profile (Normalized)', fontsize=14, fontweight='bold')
    ax.set_xlabel('Country', fontsize=12)
    ax.set_ylabel('Metric', fontsize=12)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/emotional_profile_heatmap.png', dpi=300, bbox_inches='tight')
    print(f"✅ Saved: emotional_profile_heatmap.png")
    plt.close()
    
    # Figure 4: Top emojis per country
    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    axes = axes.flatten()
    
    for idx, country in enumerate(df['country'].unique()):
        if idx >= len(axes):
            break
        
        ax = axes[idx]
        country_data = df[df['country'] == country]
        
        # Top emojisを集計
        all_top_emojis = []
        for emojis_list in country_data['top_emojis']:
            if isinstance(emojis_list, list):
                all_top_emojis.extend(emojis_list)
        
        if all_top_emojis:
            emoji_counter = Counter()
            for emoji_item, count in all_top_emojis:
                emoji_counter[emoji_item] += count
            
            top_10 = emoji_counter.most_common(10)
            
            if top_10:
                emojis, counts = zip(*top_10)
                ax.barh(range(len(emojis)), counts, color='skyblue')
                ax.set_yticks(range(len(emojis)))
                ax.set_yticklabels(emojis, fontsize=14)
                ax.invert_yaxis()
                ax.set_xlabel('Count', fontsize=10)
                ax.set_title(f'{country} - Top Emojis', fontsize=12, fontweight='bold')
            else:
                ax.text(0.5, 0.5, 'No emojis', ha='center', va='center', transform=ax.transAxes)
                ax.set_title(f'{country} - Top Emojis', fontsize=12, fontweight='bold')
        else:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes)
            ax.set_title(f'{country} - Top Emojis', fontsize=12, fontweight='bold')
    
    # 未使用のサブプロットを非表示
    for idx in range(len(df['country'].unique()), len(axes)):
        axes[idx].axis('off')
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/top_emojis_by_country.png', dpi=300, bbox_inches='tight')
    print(f"✅ Saved: top_emojis_by_country.png")
    plt.close()

if __name__ == "__main__":
    main()
