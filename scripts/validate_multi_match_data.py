#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
複数試合データの品質検証スクリプト

検証項目:
1. 各試合のコメント数、配信数
2. タイムスタンプの範囲と整合性
3. 欠損データの有無
4. 言語分布の確認
5. データ品質スコアの算出
"""

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 日本語フォント設定
plt.rcParams['font.sans-serif'] = ['Yu Gothic', 'Meiryo', 'MS Gothic']
plt.rcParams['axes.unicode_minus'] = False

# パス設定
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output" / "data_quality_report"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 80)
print("データ品質検証スクリプト - Data Quality Validation")
print("=" * 80)


def detect_language(text):
    """簡易的な言語検出"""
    if pd.isna(text) or not isinstance(text, str):
        return 'unknown'
    
    # 日本語
    if any('\u3040' <= c <= '\u309F' or '\u30A0' <= c <= '\u30FF' or '\u4E00' <= c <= '\u9FAF' for c in text):
        return 'Japanese'
    
    # スペイン語キーワード
    spanish_words = ['gol', 'vamos', 'madrid', 'barcelona', 'qué', 'sí', 'no']
    if any(word in text.lower() for word in spanish_words):
        return 'Spanish'
    
    # ポルトガル語キーワード
    portuguese_words = ['brasil', 'sim', 'não', 'gol', 'jogo']
    if any(word in text.lower() for word in portuguese_words):
        return 'Portuguese'
    
    # フランス語キーワード
    french_words = ['le', 'la', 'oui', 'non', 'bien', 'paris']
    if any(word in text.lower() for word in french_words):
        return 'French'
    
    # 英語（デフォルト）
    return 'English'


def validate_single_match(match_folder):
    """単一試合のデータを検証"""
    folder_path = DATA_DIR / "football" / match_folder
    
    if not folder_path.exists():
        return None
    
    validation_result = {
        'match_folder': match_folder,
        'num_streams': 0,
        'total_comments': 0,
        'timestamp_start': None,
        'timestamp_end': None,
        'duration_minutes': np.nan,
        'missing_timestamps': 0,
        'missing_comments': 0,
        'languages': {},
        'quality_score': 0.0,
        'issues': []
    }
    
    csv_files = list(folder_path.glob("*_chat_log.csv"))
    # CSVファイルを検索（複数パターン対応）
    csv_files = list(folder_path.glob("*_chat_log.csv"))
    if not csv_files:
        csv_files = list(folder_path.glob("*.csv"))  # 他のパターンもチェック
    
    validation_result['num_streams'] = len(csv_files)
    
    all_timestamps = []
    all_languages = []
    
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file, encoding='utf-8-sig')
            
            # 基本統計
            validation_result['total_comments'] += len(df)
            
            # 欠損値チェック
            if 'timestamp' in df.columns:
                missing_ts = df['timestamp'].isna().sum()
                validation_result['missing_timestamps'] += missing_ts
                
                # タイムスタンプの範囲
                df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
                valid_timestamps = df['timestamp'].dropna()
                if len(valid_timestamps) > 0:
                    all_timestamps.extend(valid_timestamps.tolist())
            
            if 'comment' in df.columns:
                missing_comments = df['comment'].isna().sum()
                validation_result['missing_comments'] += missing_comments
                
                # 言語検出（サンプル100件）
                sample_comments = df['comment'].dropna().sample(min(100, len(df)), random_state=42)
                for comment in sample_comments:
                    lang = detect_language(comment)
                    all_languages.append(lang)
            
        except Exception as e:
            validation_result['issues'].append(f"ファイル読み込みエラー: {csv_file.name} - {str(e)}")
    
    # タイムスタンプ範囲
    if all_timestamps:
        validation_result['timestamp_start'] = min(all_timestamps)
        validation_result['timestamp_end'] = max(all_timestamps)
        duration = (validation_result['timestamp_end'] - validation_result['timestamp_start']).total_seconds() / 60
        validation_result['duration_minutes'] = duration
    
    # 言語分布
    if all_languages:
        lang_counts = pd.Series(all_languages).value_counts()
        validation_result['languages'] = lang_counts.to_dict()
    
    # 品質スコア計算（0-100）
    score = 100.0
    
    # ペナルティ
    if validation_result['num_streams'] == 0:
        score -= 100
    if validation_result['total_comments'] < 100:
        score -= 30
    if validation_result['missing_timestamps'] > validation_result['total_comments'] * 0.1:
        score -= 20
    if validation_result['missing_comments'] > validation_result['total_comments'] * 0.05:
        score -= 15
    if not all_timestamps:
        score -= 25
    
    validation_result['quality_score'] = max(0, score)
    
    return validation_result


def validate_all_matches():
    """全試合のデータを検証"""
    print("\n" + "=" * 80)
    print("全試合データ検証中...")
    print("=" * 80)
    
    football_dir = DATA_DIR / "football"
    match_folders = [d.name for d in football_dir.iterdir() if d.is_dir()]
    
    results = []
    
    for match_folder in sorted(match_folders):
        print(f"\n📊 検証中: {match_folder}")
        
        result = validate_single_match(match_folder)
        
        if result:
            print(f"  ✓ 配信数: {result['num_streams']}")
            print(f"  ✓ コメント総数: {result['total_comments']:,}")
            print(f"  ✓ 試合時間: {result['duration_minutes']:.1f} 分" if not np.isnan(result['duration_minutes']) else "  ⚠ 試合時間取得不可")
            print(f"  ✓ 品質スコア: {result['quality_score']:.1f}/100")
            
            if result['languages']:
                print(f"  ✓ 検出言語: {', '.join([f'{k}({v})' for k, v in result['languages'].items()])}")
            
            if result['issues']:
                print(f"  ⚠ 問題点:")
                for issue in result['issues']:
                    print(f"    - {issue}")
            
            results.append(result)
    
    # データフレームに変換
    results_df = pd.DataFrame(results)
    
    # 言語情報を展開
    language_columns = {}
    for idx, row in results_df.iterrows():
        for lang, count in row['languages'].items():
            if lang not in language_columns:
                language_columns[lang] = [0] * len(results_df)
            language_columns[lang][idx] = count
    
    for lang, counts in language_columns.items():
        results_df[f'lang_{lang}'] = counts
    
    # 保存
    output_path = OUTPUT_DIR / "data_quality_summary.csv"
    results_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"\n✓ データ品質サマリー保存: {output_path}")
    
    return results_df


def create_visualizations(df):
    """データ品質の可視化"""
    print("\n" + "=" * 80)
    print("可視化作成中...")
    print("=" * 80)
    
    # 図1: 試合別コメント数と配信数
    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    
    # コメント数
    ax1 = axes[0]
    df_sorted = df.sort_values('total_comments', ascending=False)
    bars1 = ax1.bar(range(len(df_sorted)), df_sorted['total_comments'], color='steelblue')
    ax1.set_xticks(range(len(df_sorted)))
    ax1.set_xticklabels(df_sorted['match_folder'], rotation=45, ha='right')
    ax1.set_title('試合別コメント総数', fontsize=13, fontweight='bold')
    ax1.set_ylabel('コメント数', fontsize=11)
    ax1.grid(axis='y', alpha=0.3)
    
    # 配信数
    ax2 = axes[1]
    bars2 = ax2.bar(range(len(df_sorted)), df_sorted['num_streams'], color='coral')
    ax2.set_xticks(range(len(df_sorted)))
    ax2.set_xticklabels(df_sorted['match_folder'], rotation=45, ha='right')
    ax2.set_title('試合別配信数', fontsize=13, fontweight='bold')
    ax2.set_ylabel('配信数', fontsize=11)
    ax2.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    output_path = OUTPUT_DIR / "match_statistics_barplot.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  ✓ 棒グラフ保存: {output_path.name}")
    plt.close()
    
    # 図2: 品質スコア
    fig, ax = plt.subplots(figsize=(12, 6))
    
    df_sorted = df.sort_values('quality_score', ascending=True)
    colors = ['red' if score < 70 else 'orange' if score < 85 else 'green' 
              for score in df_sorted['quality_score']]
    
    ax.barh(range(len(df_sorted)), df_sorted['quality_score'], color=colors)
    ax.set_yticks(range(len(df_sorted)))
    ax.set_yticklabels(df_sorted['match_folder'])
    ax.set_xlabel('品質スコア (0-100)', fontsize=11)
    ax.set_title('試合別データ品質スコア', fontsize=13, fontweight='bold')
    ax.axvline(x=85, color='green', linestyle='--', alpha=0.5, label='優良 (85+)')
    ax.axvline(x=70, color='orange', linestyle='--', alpha=0.5, label='許容 (70+)')
    ax.legend()
    ax.grid(axis='x', alpha=0.3)
    
    plt.tight_layout()
    output_path = OUTPUT_DIR / "quality_score_barplot.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  ✓ 品質スコア保存: {output_path.name}")
    plt.close()
    
    # 図3: 言語分布（ヒートマップ）
    lang_columns = [col for col in df.columns if col.startswith('lang_')]
    if lang_columns:
        fig, ax = plt.subplots(figsize=(10, 8))
        
        lang_data = df[['match_folder'] + lang_columns].set_index('match_folder')
        lang_data.columns = [col.replace('lang_', '') for col in lang_data.columns]
        
        sns.heatmap(lang_data, annot=True, fmt='.0f', cmap='YlOrRd', ax=ax,
                   cbar_kws={'label': 'サンプル言語検出数'})
        
        ax.set_title('試合別言語分布（サンプル100件/配信）', fontsize=13, fontweight='bold')
        ax.set_xlabel('言語', fontsize=11)
        ax.set_ylabel('試合', fontsize=11)
        
        plt.tight_layout()
        output_path = OUTPUT_DIR / "language_distribution_heatmap.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"  ✓ 言語分布ヒートマップ保存: {output_path.name}")
        plt.close()
    
    print("\n✓ 全可視化完了")


def create_quality_report(df):
    """品質レポートを作成"""
    print("\n" + "=" * 80)
    print("品質レポート作成中...")
    print("=" * 80)
    
    report = []
    report.append("# データ品質検証レポート\n\n")
    report.append(f"**検証日時**: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}\n\n")
    report.append("---\n\n")
    
    # 全体統計
    report.append("## 📊 全体統計\n\n")
    report.append(f"- **総試合数**: {len(df)} 試合\n")
    report.append(f"- **総配信数**: {df['num_streams'].sum():.0f} 配信\n")
    report.append(f"- **総コメント数**: {df['total_comments'].sum():,.0f} 件\n")
    report.append(f"- **平均品質スコア**: {df['quality_score'].mean():.1f}/100\n\n")
    
    # 試合別詳細
    report.append("## 📋 試合別詳細\n\n")
    report.append("| 試合名 | 配信数 | コメント数 | 試合時間(分) | 品質スコア | 判定 |\n")
    report.append("|--------|--------|-----------|-------------|-----------|------|\n")
    
    for _, row in df.iterrows():
        quality_label = "🟢 優良" if row['quality_score'] >= 85 else "🟡 許容" if row['quality_score'] >= 70 else "🔴 要注意"
        duration_str = f"{row['duration_minutes']:.0f}" if not np.isnan(row['duration_minutes']) else "N/A"
        
        report.append(f"| {row['match_folder']} | {row['num_streams']:.0f} | "
                     f"{row['total_comments']:,} | {duration_str} | "
                     f"{row['quality_score']:.1f} | {quality_label} |\n")
    report.append("\n")
    
    # 言語分布
    lang_columns = [col for col in df.columns if col.startswith('lang_')]
    if lang_columns:
        report.append("## 🌍 言語分布サマリー\n\n")
        
        total_lang_counts = {}
        for col in lang_columns:
            lang = col.replace('lang_', '')
            total_lang_counts[lang] = df[col].sum()
        
        total_samples = sum(total_lang_counts.values())
        
        report.append("| 言語 | サンプル検出数 | 割合(%) |\n")
        report.append("|------|---------------|--------|\n")
        
        for lang, count in sorted(total_lang_counts.items(), key=lambda x: x[1], reverse=True):
            if count > 0:
                percentage = (count / total_samples) * 100 if total_samples > 0 else 0
                report.append(f"| {lang} | {count:.0f} | {percentage:.1f} |\n")
        report.append("\n")
    
    # 品質判定
    report.append("## ✅ 品質判定\n\n")
    
    excellent = len(df[df['quality_score'] >= 85])
    acceptable = len(df[(df['quality_score'] >= 70) & (df['quality_score'] < 85)])
    needs_attention = len(df[df['quality_score'] < 70])
    
    report.append(f"- **優良（85点以上）**: {excellent} 試合\n")
    report.append(f"- **許容範囲（70-84点）**: {acceptable} 試合\n")
    report.append(f"- **要注意（70点未満）**: {needs_attention} 試合\n\n")
    
    if needs_attention > 0:
        report.append("### 要注意試合の詳細\n\n")
        low_quality = df[df['quality_score'] < 70]
        for _, row in low_quality.iterrows():
            report.append(f"- **{row['match_folder']}** (スコア: {row['quality_score']:.1f})\n")
            if row['total_comments'] < 100:
                report.append(f"  - コメント数不足: {row['total_comments']} 件\n")
            if row['missing_timestamps'] > 0:
                report.append(f"  - タイムスタンプ欠損: {row['missing_timestamps']} 件\n")
        report.append("\n")
    
    # 推奨アクション
    report.append("## 💡 推奨アクション\n\n")
    
    if df['quality_score'].mean() >= 85:
        report.append("✅ **全体的にデータ品質は良好です。分析を進めて問題ありません。**\n\n")
    elif df['quality_score'].mean() >= 70:
        report.append("⚠ **概ね許容範囲ですが、一部改善が望ましい試合があります。**\n\n")
    else:
        report.append("🔴 **データ品質に課題があります。以下の対応を推奨します。**\n\n")
    
    report.append("### 具体的な推奨事項\n\n")
    
    if needs_attention > 0:
        report.append("1. **要注意試合の再調査**\n")
        report.append("   - 配信URLの確認\n")
        report.append("   - データ収集プロセスの再実行\n\n")
    
    if df['missing_timestamps'].sum() > 0:
        report.append("2. **タイムスタンプ欠損への対応**\n")
        report.append("   - 時系列分析では該当試合を除外\n")
        report.append("   - または補完手法の検討\n\n")
    
    report.append("3. **分析への活用**\n")
    report.append("   - 品質スコア85点以上の試合を優先的に使用\n")
    report.append("   - 低品質試合は感度分析で除外を検討\n\n")
    
    # 保存
    output_path = OUTPUT_DIR / "DATA_QUALITY_REPORT.md"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(report)
    
    print(f"\n✓ 品質レポート保存完了: {output_path}")
    
    # コンソールにも出力
    print("\n" + "".join(report))


def main():
    """メイン実行関数"""
    print("\n🔍 データ品質検証開始\n")
    
    # 1. 全試合データ検証
    results_df = validate_all_matches()
    
    # 2. 可視化
    create_visualizations(results_df)
    
    # 3. 品質レポート
    create_quality_report(results_df)
    
    print("\n" + "=" * 80)
    print("✅ データ品質検証完了!")
    print("=" * 80)
    print(f"\n📁 出力ディレクトリ: {OUTPUT_DIR}")
    print("\n生成されたファイル:")
    for file in sorted(OUTPUT_DIR.glob("*")):
        print(f"  - {file.name}")
    print()


if __name__ == "__main__":
    main()
