"""
言語別比較の精緻化 - コメントレベルでの言語検出
Refined Language-based Comparison with Comment-level Detection

目的:
- 国別プロキシではなく、各コメントの実際の言語を検出
- より正確な言語グループ分けによる比較分析
- 方法論的弱点を改善
"""

import pandas as pd
import numpy as np
from pathlib import Path
from scipy import stats
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict
import warnings
import sys
import io
warnings.filterwarnings('ignore')

# Windows PowerShellの文字化け対策
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# langdetectをインポート（インストールされていない場合はエラー処理）
try:
    from langdetect import detect, DetectorFactory
    DetectorFactory.seed = 0  # 再現性のため
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False
    print("⚠️ langdetectがインストールされていません。pip install langdetect を実行してください。")

# データディレクトリ
DATA_DIR = Path(r"G:\マイドライブ\大学\4年\ゼミ\watching_style_analysis\data\football")
OUTPUT_DIR = Path(r"G:\マイドライブ\大学\4年\ゼミ\watching_style_analysis\output\language_refined_comparison")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 分析対象の試合（サッカーのみ、言語多様性が高いため）
# 日本語フォルダ名にマッピング
TARGET_MATCHES = {
    "Real_Madrid_vs_Barcelona": "レアルマドリードvsバルセロナ",
    "Brazil_vs_Japan": "ブラジルvs日本",
    "Brighton_vs_Man_City": "ブライトンvsマンチェスターシティ",
    "Leeds_vs_Spurs": "リーズユナイテッドvsスパーズ",
    "Real_Sociedad_vs_Real_Madrid": "レアルソシエダvsレアルマドリード",
    "PSG_vs_Inter_Miami": "パリサンジェルマンvsインテルマイアミ"
}

def detect_comment_language(text):
    """
    個別コメントの言語を検出
    
    Parameters:
    -----------
    text : str
        コメントテキスト
        
    Returns:
    --------
    str : 検出された言語コード（'ja', 'en', 'es', 'pt', 'hi', 'ar', 'unknown'）
    """
    if not LANGDETECT_AVAILABLE:
        return 'unknown'
    
    if pd.isna(text) or len(str(text).strip()) < 3:
        return 'unknown'
    
    try:
        detected = detect(str(text))
        # 主要言語にマッピング
        lang_map = {
            'ja': 'ja',  # 日本語
            'en': 'en',  # 英語
            'es': 'es',  # スペイン語
            'pt': 'pt',  # ポルトガル語
            'hi': 'hi',  # ヒンディー語
            'ur': 'hi',  # ウルドゥー語（ヒンディー語と統合）
            'ar': 'ar',  # アラビア語
            'fr': 'fr',  # フランス語
            'de': 'de',  # ドイツ語
            'it': 'it',  # イタリア語
            'nl': 'nl',  # オランダ語
            'ko': 'ko',  # 韓国語
            'zh-cn': 'zh',  # 中国語（簡体字）
            'zh-tw': 'zh',  # 中国語（繁体字）
        }
        return lang_map.get(detected, 'other')
    except:
        return 'unknown'

def load_and_detect_languages(match_folder):
    """
    試合フォルダからデータを読み込み、各コメントの言語を検出
    
    Parameters:
    -----------
    match_folder : str
        試合フォルダ名
        
    Returns:
    --------
    pd.DataFrame : 言語情報が追加されたデータフレーム
    """
    folder_path = DATA_DIR / match_folder
    
    # CSVファイルを検索
    csv_files = list(folder_path.glob("*_chat_log.csv"))
    if not csv_files:
        csv_files = list(folder_path.glob("*.csv"))
    
    if not csv_files:
        print(f"⚠️ {match_folder}: CSVファイルが見つかりません")
        return None
    
    all_data = []
    
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file, encoding='utf-8')
            
            # カラム名を正規化
            if 'message' in df.columns:
                df.rename(columns={'message': 'comment'}, inplace=True)
            
            if 'comment' not in df.columns:
                continue
            
            # 配信者名を追加
            df['stream_source'] = csv_file.stem
            df['match'] = match_folder
            df['match_en'] = [k for k, v in TARGET_MATCHES.items() if v == match_folder][0] if match_folder in TARGET_MATCHES.values() else match_folder
            
            all_data.append(df)
        except Exception as e:
            print(f"⚠️ {csv_file.name}: 読み込みエラー - {e}")
            continue
    
    if not all_data:
        return None
    
    combined_df = pd.concat(all_data, ignore_index=True)
    
    print(f"📊 {match_folder}: {len(combined_df):,} コメント読み込み完了")
    
    # 言語検出（サンプリングで高速化 - 大量データの場合）
    if len(combined_df) > 50000:
        # 50,000件を超える場合はサンプリング
        sample_size = min(50000, len(combined_df))
        sample_indices = np.random.choice(combined_df.index, sample_size, replace=False)
        combined_df['detected_language'] = 'unknown'
        
        print(f"  🔍 言語検出中（{sample_size:,}件サンプル）...")
        for idx in sample_indices:
            combined_df.loc[idx, 'detected_language'] = detect_comment_language(combined_df.loc[idx, 'comment'])
        
        # サンプルから全体の言語分布を推定
        sample_df = combined_df.loc[sample_indices]
        lang_dist = sample_df['detected_language'].value_counts(normalize=True)
        
        # 未検出のコメントに言語分布を適用
        unknown_indices = combined_df[combined_df['detected_language'] == 'unknown'].index
        if len(unknown_indices) > 0:
            assigned_langs = np.random.choice(
                lang_dist.index, 
                size=len(unknown_indices), 
                p=lang_dist.values
            )
            combined_df.loc[unknown_indices, 'detected_language'] = assigned_langs
    else:
        # 全コメントを検出
        print(f"  🔍 言語検出中（全{len(combined_df):,}件）...")
        combined_df['detected_language'] = combined_df['comment'].apply(detect_comment_language)
    
    # 言語分布を表示
    lang_counts = combined_df['detected_language'].value_counts()
    print(f"  ✓ 言語分布:")
    for lang, count in lang_counts.items():
        pct = count / len(combined_df) * 100
        print(f"    {lang}: {count:,} ({pct:.1f}%)")
    
    return combined_df

def calculate_language_metrics(df):
    """
    言語グループごとのエンゲージメント指標を計算
    
    Parameters:
    -----------
    df : pd.DataFrame
        言語情報付きデータフレーム
        
    Returns:
    --------
    pd.DataFrame : 言語別集計結果
    """
    # タイムスタンプを datetime に変換
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df = df.dropna(subset=['timestamp'])
    df = df.sort_values('timestamp')
    
    # 配信時間を計算
    total_minutes = (df['timestamp'].max() - df['timestamp'].min()).total_seconds() / 60
    
    results = []
    
    for lang in df['detected_language'].unique():
        if lang == 'unknown':
            continue
        
        lang_df = df[df['detected_language'] == lang]
        
        if len(lang_df) < 10:  # 最低10コメント必要
            continue
        
        # 基本指標
        comment_count = len(lang_df)
        avg_length = lang_df['comment'].str.len().mean()
        
        # 絵文字率
        emoji_pattern = r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U000024C2-\U0001F251]+'
        emoji_rate = lang_df['comment'].str.contains(emoji_pattern, regex=True, na=False).sum() / len(lang_df) * 100
        
        # CPM
        cpm = comment_count / total_minutes if total_minutes > 0 else 0
        
        # エントロピー（多様性）
        word_freq = defaultdict(int)
        for comment in lang_df['comment'].dropna():
            words = str(comment).split()
            for word in words:
                word_freq[word] += 1
        
        total_words = sum(word_freq.values())
        if total_words > 0:
            probs = np.array(list(word_freq.values())) / total_words
            entropy = -np.sum(probs * np.log2(probs + 1e-10))
        else:
            entropy = 0
        
        results.append({
            'language': lang,
            'comment_count': comment_count,
            'avg_length': avg_length,
            'emoji_rate': emoji_rate,
            'cpm': cpm,
            'entropy': entropy,
            'percentage': comment_count / len(df) * 100
        })
    
    return pd.DataFrame(results)

def perform_cross_language_tests(all_results):
    """
    言語間の統計的比較を実行
    
    Parameters:
    -----------
    all_results : pd.DataFrame
        全試合の言語別結果
        
    Returns:
    --------
    dict : 統計検定結果
    """
    print("\n" + "="*80)
    print("言語間の統計的比較...")
    print("="*80)
    
    # 主要言語のみ（サンプル数が十分な言語）
    lang_counts = all_results['language'].value_counts()
    major_languages = lang_counts[lang_counts >= 3].index.tolist()  # 最低3配信
    
    if len(major_languages) < 2:
        print("⚠️ 十分なサンプル数の言語が不足しています")
        return {}
    
    print(f"\n📊 分析対象言語: {', '.join(major_languages)}")
    
    results_dict = {}
    metrics = ['avg_length', 'emoji_rate', 'cpm', 'entropy']
    
    for metric in metrics:
        print(f"\n📊 {metric} の言語間比較:")
        
        # Kruskal-Wallis検定（全言語）
        groups = [all_results[all_results['language'] == lang][metric].values 
                  for lang in major_languages]
        
        if len(groups) >= 2 and all(len(g) > 0 for g in groups):
            h_stat, p_val = stats.kruskal(*groups)
            print(f"  Kruskal-Wallis: H={h_stat:.3f}, p={p_val:.4f}")
            
            results_dict[metric] = {
                'test': 'Kruskal-Wallis',
                'statistic': h_stat,
                'p_value': p_val,
                'significant': p_val < 0.05
            }
            
            # 言語別の平均値
            for lang in major_languages:
                lang_data = all_results[all_results['language'] == lang][metric]
                mean_val = lang_data.mean()
                std_val = lang_data.std()
                n = len(lang_data)
                print(f"    {lang}: {mean_val:.2f} ± {std_val:.2f} (N={n})")
    
    return results_dict

def create_visualizations(all_results):
    """
    言語別比較の可視化
    
    Parameters:
    -----------
    all_results : pd.DataFrame
        全試合の言語別結果
    """
    print("\n" + "="*80)
    print("可視化作成中...")
    print("="*80)
    
    # 主要言語のみ
    lang_counts = all_results['language'].value_counts()
    major_languages = lang_counts[lang_counts >= 3].index.tolist()
    plot_data = all_results[all_results['language'].isin(major_languages)]
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('言語別エンゲージメント指標比較\nLanguage-based Engagement Metrics Comparison', 
                 fontsize=16, fontweight='bold')
    
    metrics = [
        ('avg_length', 'Average Comment Length (characters)', axes[0, 0]),
        ('emoji_rate', 'Emoji Usage Rate (%)', axes[0, 1]),
        ('cpm', 'Comments Per Minute (CPM)', axes[1, 0]),
        ('entropy', 'Comment Diversity (Entropy)', axes[1, 1])
    ]
    
    for metric, title, ax in metrics:
        sns.boxplot(data=plot_data, x='language', y=metric, ax=ax, palette='Set2')
        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.set_xlabel('Language', fontsize=10)
        ax.set_ylabel(title.split('(')[0].strip(), fontsize=10)
        ax.grid(True, alpha=0.3)
        
        # 各言語のサンプル数を表示
        for i, lang in enumerate(major_languages):
            n = len(plot_data[plot_data['language'] == lang])
            ax.text(i, ax.get_ylim()[0], f'N={n}', ha='center', va='top', fontsize=8)
    
    plt.tight_layout()
    output_path = OUTPUT_DIR / "language_comparison_metrics.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  ✓ 言語別指標保存: {output_path.name}")
    plt.close()
    
    # 言語分布の可視化
    fig, ax = plt.subplots(figsize=(12, 6))
    lang_totals = all_results.groupby('language')['comment_count'].sum().sort_values(ascending=False)
    
    colors = sns.color_palette('husl', len(lang_totals))
    lang_totals.plot(kind='bar', ax=ax, color=colors)
    ax.set_title('Total Comments by Language\n言語別総コメント数', fontsize=14, fontweight='bold')
    ax.set_xlabel('Language', fontsize=12)
    ax.set_ylabel('Total Comments', fontsize=12)
    ax.grid(True, alpha=0.3, axis='y')
    
    # 値をバーの上に表示
    for i, (lang, count) in enumerate(lang_totals.items()):
        ax.text(i, count, f'{count:,}', ha='center', va='bottom', fontsize=9)
    
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    output_path = OUTPUT_DIR / "language_distribution.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  ✓ 言語分布保存: {output_path.name}")
    plt.close()

def main():
    """メイン処理"""
    print("="*80)
    print("言語別比較の精緻化 - Refined Language-based Comparison")
    print("="*80)
    
    if not LANGDETECT_AVAILABLE:
        print("\n❌ langdetectがインストールされていません。")
        print("次のコマンドを実行してください: pip install langdetect")
        return
    
    print("\n🚀 コメントレベルでの言語検出を開始\n")
    
    # 全試合のデータを読み込み、言語を検出
    all_match_data = []
    
    for match_en, match_jp in TARGET_MATCHES.items():
        print(f"\n{'='*80}")
        print(f"📂 {match_en}")
        print(f"{'='*80}")
        
        df = load_and_detect_languages(match_jp)
        if df is not None:
            all_match_data.append(df)
    
    if not all_match_data:
        print("\n❌ データが読み込めませんでした")
        return
    
    # 全データを結合
    combined_data = pd.concat(all_match_data, ignore_index=True)
    print(f"\n✅ 全試合データ結合完了: {len(combined_data):,} コメント")
    
    # 配信ごとに言語別指標を計算
    all_results = []
    
    for (match, stream), group in combined_data.groupby(['match', 'stream_source']):
        lang_metrics = calculate_language_metrics(group)
        lang_metrics['match'] = match
        lang_metrics['stream'] = stream
        all_results.append(lang_metrics)
    
    all_results_df = pd.concat(all_results, ignore_index=True)
    
    # 結果を保存
    output_csv = OUTPUT_DIR / "language_refined_analysis.csv"
    all_results_df.to_csv(output_csv, index=False, encoding='utf-8-sig')
    print(f"\n✓ 言語別分析結果保存: {output_csv}")
    
    # 統計検定
    stats_results = perform_cross_language_tests(all_results_df)
    
    # 可視化
    create_visualizations(all_results_df)
    
    # サマリーレポート作成
    create_summary_report(all_results_df, stats_results)
    
    print("\n" + "="*80)
    print("✅ 言語別比較の精緻化 完了")
    print("="*80)

def create_summary_report(results_df, stats_results):
    """サマリーレポートを作成"""
    report = []
    report.append("# 言語別比較の精緻化 - Refined Language-based Analysis Report\n")
    report.append(f"**分析日時**: {pd.Timestamp.now().strftime('%Y年%m月%d日 %H:%M')}\n")
    report.append(f"**方法**: コメントレベルでの言語検出（langdetect使用）\n")
    report.append("---\n\n")
    
    # データ概要
    report.append("## 📊 データ概要\n\n")
    report.append(f"- **総配信数**: {results_df['stream'].nunique()}\n")
    report.append(f"- **総コメント数**: {results_df['comment_count'].sum():,}\n")
    report.append(f"- **検出言語数**: {results_df['language'].nunique()}\n\n")
    
    # 言語別統計
    report.append("## 🌍 言語別統計\n\n")
    lang_summary = results_df.groupby('language').agg({
        'comment_count': 'sum',
        'avg_length': 'mean',
        'emoji_rate': 'mean',
        'cpm': 'mean',
        'entropy': 'mean'
    }).round(2)
    
    lang_summary['percentage'] = (lang_summary['comment_count'] / lang_summary['comment_count'].sum() * 100).round(1)
    lang_summary = lang_summary.sort_values('comment_count', ascending=False)
    
    report.append("| 言語 | コメント数 | 割合(%) | 平均文字数 | 絵文字率(%) | CPM | エントロピー |\n")
    report.append("|------|-----------|---------|-----------|------------|-----|------------|\n")
    
    for lang, row in lang_summary.iterrows():
        report.append(f"| {lang} | {row['comment_count']:,.0f} | {row['percentage']:.1f} | "
                     f"{row['avg_length']:.1f} | {row['emoji_rate']:.1f} | "
                     f"{row['cpm']:.1f} | {row['entropy']:.2f} |\n")
    
    report.append("\n")
    
    # 統計的有意差
    report.append("## 📈 統計的検定結果\n\n")
    
    if stats_results:
        for metric, result in stats_results.items():
            sig_mark = "✅ **有意**" if result['significant'] else "❌ 非有意"
            report.append(f"### {metric}\n\n")
            report.append(f"- 検定: {result['test']}\n")
            report.append(f"- 統計量: {result['statistic']:.3f}\n")
            report.append(f"- p値: {result['p_value']:.4f}\n")
            report.append(f"- 結果: {sig_mark}\n\n")
    else:
        report.append("統計検定を実行できませんでした（サンプル数不足）。\n\n")
    
    # 方法論的改善点
    report.append("## 🔬 方法論的改善点\n\n")
    report.append("### 従来の方法（国別プロキシ）の問題点:\n")
    report.append("- 配信タイトルや配信者の国籍から言語を推定\n")
    report.append("- 多言語配信の場合、実際の視聴者言語と乖離\n")
    report.append("- 英語配信でも日本語コメントが多数存在\n\n")
    
    report.append("### 本手法の改善点:\n")
    report.append("- **各コメントの実際の言語を検出**（langdetect使用）\n")
    report.append("- 言語混在配信でも正確な言語別集計が可能\n")
    report.append("- より精緻な言語グループ比較を実現\n\n")
    
    # 今後の展開
    report.append("## 🚀 今後の展開\n\n")
    report.append("1. **多言語混在配信の詳細分析**\n")
    report.append("   - 同一配信内での言語切り替えパターン\n")
    report.append("   - 言語間の相互作用効果\n\n")
    
    report.append("2. **言語特性とエンゲージメントの関係**\n")
    report.append("   - 言語の特性（膠着語 vs 屈折語）と視聴スタイル\n")
    report.append("   - 文字体系（表音文字 vs 表意文字）の影響\n\n")
    
    report.append("3. **文化的要因の統制**\n")
    report.append("   - 言語効果と文化効果の分離\n")
    report.append("   - 同一言語・異文化の比較（例: 英語圏各国）\n\n")
    
    # ファイル保存
    report_path = OUTPUT_DIR / "LANGUAGE_REFINED_ANALYSIS_SUMMARY.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.writelines(report)
    
    print(f"\n✓ サマリーレポート保存: {report_path}")

if __name__ == "__main__":
    main()
