"""
縦断的比較分析 - レアルマドリード3試合
Longitudinal Comparison Analysis - Real Madrid 3 Matches

目的:
- 同一チームの異なる試合を比較
- 試合特性の変化による視聴スタイルの変化を検出
- 配信者を固定して純粋な試合効果を抽出
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

# データディレクトリ
DATA_DIR = Path(r"G:\マイドライブ\大学\4年\ゼミ\watching_style_analysis\data\football")
OUTPUT_DIR = Path(r"G:\マイドライブ\大学\4年\ゼミ\watching_style_analysis\output\longitudinal_real_madrid")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# レアルマドリード3試合（日本語フォルダ名にマッピング）
REAL_MADRID_MATCHES = {
    "Real_Madrid_vs_Barcelona": {
        "folder": "レアルマドリードvsバルセロナ",
        "opponent": "Barcelona",
        "tier": 1,
        "importance": "Ultra-High",
        "context": "El Clasico - 最高峰の一戦"
    },
    "Real_Sociedad_vs_Real_Madrid": {
        "folder": "レアルソシエダvsレアルマドリード",
        "opponent": "Real Sociedad",
        "tier": 3,
        "importance": "Medium",
        "context": "リーグ戦中位対戦"
    },
    "PSG_vs_Inter_Miami": {
        "folder": "パリサンジェルマンvsインテルマイアミ",
        "opponent": "PSG (Real Madrid関連)",
        "tier": 4,
        "importance": "Low",
        "context": "親善試合（注: 正確にはMessi絡み）"
    }
}

def load_match_data(match_folder):
    """
    試合データを読み込み
    
    Parameters:
    -----------
    match_folder : str
        試合フォルダ名
        
    Returns:
    --------
    pd.DataFrame : 読み込まれたデータ
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
            
            all_data.append(df)
        except Exception as e:
            print(f"⚠️ {csv_file.name}: 読み込みエラー - {e}")
            continue
    
    if not all_data:
        return None
    
    combined_df = pd.concat(all_data, ignore_index=True)
    return combined_df

def calculate_engagement_metrics(df):
    """
    エンゲージメント指標を計算
    
    Parameters:
    -----------
    df : pd.DataFrame
        試合データ
        
    Returns:
    --------
    dict : 各種指標
    """
    # タイムスタンプを datetime に変換
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df = df.dropna(subset=['timestamp'])
    df = df.sort_values('timestamp')
    
    # 配信時間
    duration_minutes = (df['timestamp'].max() - df['timestamp'].min()).total_seconds() / 60
    
    # 基本指標
    total_comments = len(df)
    cpm = total_comments / duration_minutes if duration_minutes > 0 else 0
    
    # コメント長
    avg_length = df['comment'].str.len().mean()
    
    # 絵文字率
    emoji_pattern = r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U000024C2-\U0001F251]+'
    emoji_rate = df['comment'].str.contains(emoji_pattern, regex=True, na=False).sum() / total_comments * 100
    
    # エントロピー
    word_freq = defaultdict(int)
    for comment in df['comment'].dropna():
        words = str(comment).split()
        for word in words:
            word_freq[word] += 1
    
    total_words = sum(word_freq.values())
    if total_words > 0:
        probs = np.array(list(word_freq.values())) / total_words
        entropy = -np.sum(probs * np.log2(probs + 1e-10))
    else:
        entropy = 0
    
    # 時系列パターン - バースト検出
    df['minute'] = ((df['timestamp'] - df['timestamp'].min()).dt.total_seconds() / 60).astype(int)
    comments_per_minute = df.groupby('minute').size()
    
    burst_threshold = comments_per_minute.mean() + comments_per_minute.std()
    burst_count = (comments_per_minute > burst_threshold).sum()
    burst_frequency = burst_count / len(comments_per_minute) if len(comments_per_minute) > 0 else 0
    
    # CPMの変動係数
    cpm_cv = comments_per_minute.std() / comments_per_minute.mean() if comments_per_minute.mean() > 0 else 0
    
    return {
        'total_comments': total_comments,
        'duration_minutes': duration_minutes,
        'cpm': cpm,
        'avg_comment_length': avg_length,
        'emoji_rate': emoji_rate,
        'entropy': entropy,
        'burst_count': burst_count,
        'burst_frequency': burst_frequency,
        'cpm_cv': cpm_cv,
        'stream_count': df['stream_source'].nunique()
    }

def analyze_streamer_consistency(all_data):
    """
    配信者の一貫性を分析（同じ配信者が複数試合に出現するか）
    
    Parameters:
    -----------
    all_data : dict
        試合名 -> DataFrame のマッピング
        
    Returns:
    --------
    dict : 配信者の出現パターン
    """
    streamer_appearances = defaultdict(list)
    
    for match, df in all_data.items():
        for streamer in df['stream_source'].unique():
            streamer_appearances[streamer].append(match)
    
    # 複数試合に出現する配信者
    consistent_streamers = {k: v for k, v in streamer_appearances.items() if len(v) > 1}
    
    return consistent_streamers

def perform_longitudinal_tests(metrics_df):
    """
    縦断的比較の統計検定
    
    Parameters:
    -----------
    metrics_df : pd.DataFrame
        試合別指標
        
    Returns:
    --------
    dict : 統計検定結果
    """
    print("\n" + "="*80)
    print("縦断的比較の統計検定...")
    print("="*80)
    
    results = {}
    
    test_metrics = ['cpm', 'avg_comment_length', 'emoji_rate', 'entropy', 'burst_frequency', 'cpm_cv']
    
    for metric in test_metrics:
        print(f"\n📊 {metric}:")
        
        # 試合別の平均値
        for _, row in metrics_df.iterrows():
            print(f"  {row['match']}: {row[metric]:.2f}")
        
        # 3試合間の差の検定（Kruskal-Wallis）
        groups = [metrics_df[metrics_df['match'] == match][metric].values 
                  for match in metrics_df['match'].unique()]
        
        if len(groups) >= 2 and all(len(g) > 0 for g in groups):
            h_stat, p_val = stats.kruskal(*groups)
            print(f"  Kruskal-Wallis: H={h_stat:.3f}, p={p_val:.4f}")
            
            results[metric] = {
                'test': 'Kruskal-Wallis',
                'statistic': h_stat,
                'p_value': p_val,
                'significant': p_val < 0.05
            }
    
    return results

def create_visualizations(metrics_df, all_data):
    """
    縦断的比較の可視化
    
    Parameters:
    -----------
    metrics_df : pd.DataFrame
        試合別指標
    all_data : dict
        全試合データ
    """
    print("\n" + "="*80)
    print("可視化作成中...")
    print("="*80)
    
    # 1. 試合別指標の比較
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle('レアルマドリード縦断的比較\nReal Madrid Longitudinal Comparison', 
                 fontsize=16, fontweight='bold')
    
    metrics_to_plot = [
        ('cpm', 'Comments Per Minute (CPM)', axes[0, 0]),
        ('avg_comment_length', 'Average Comment Length (characters)', axes[0, 1]),
        ('emoji_rate', 'Emoji Usage Rate (%)', axes[0, 2]),
        ('entropy', 'Comment Diversity (Entropy)', axes[1, 0]),
        ('burst_frequency', 'Burst Frequency', axes[1, 1]),
        ('cpm_cv', 'CPM Coefficient of Variation', axes[1, 2])
    ]
    
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1']
    
    for metric, title, ax in metrics_to_plot:
        # 試合別の平均値をプロット
        match_names = metrics_df['match'].unique()
        match_means = [metrics_df[metrics_df['match'] == m][metric].mean() for m in match_names]
        match_stds = [metrics_df[metrics_df['match'] == m][metric].std() for m in match_names]
        
        x_pos = np.arange(len(match_names))
        ax.bar(x_pos, match_means, yerr=match_stds, capsize=5, color=colors, alpha=0.7, edgecolor='black')
        
        ax.set_title(title, fontsize=11, fontweight='bold')
        ax.set_xticks(x_pos)
        ax.set_xticklabels([m.replace('_', ' ') for m in match_names], rotation=15, ha='right', fontsize=9)
        ax.set_ylabel(title.split('(')[0].strip(), fontsize=10)
        ax.grid(True, alpha=0.3, axis='y')
        
        # サンプル数を表示
        for i, match in enumerate(match_names):
            n = len(metrics_df[metrics_df['match'] == match])
            ax.text(i, ax.get_ylim()[0], f'N={n}', ha='center', va='top', fontsize=8)
    
    plt.tight_layout()
    output_path = OUTPUT_DIR / "longitudinal_metrics_comparison.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  ✓ 指標比較保存: {output_path.name}")
    plt.close()
    
    # 2. 時系列パターンの可視化
    fig, axes = plt.subplots(len(all_data), 1, figsize=(14, 4 * len(all_data)))
    if len(all_data) == 1:
        axes = [axes]
    
    fig.suptitle('試合ごとのコメントパターン推移\nComment Pattern Over Time by Match', 
                 fontsize=14, fontweight='bold')
    
    for idx, (match, df) in enumerate(all_data.items()):
        ax = axes[idx]
        
        # タイムスタンプを datetime に変換
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df = df.dropna(subset=['timestamp'])
        df = df.sort_values('timestamp')
        
        # 分単位でグループ化
        df['minute'] = ((df['timestamp'] - df['timestamp'].min()).dt.total_seconds() / 60).astype(int)
        comments_per_minute = df.groupby('minute').size()
        
        # プロット
        ax.plot(comments_per_minute.index, comments_per_minute.values, color=colors[idx % len(colors)], linewidth=1.5)
        ax.fill_between(comments_per_minute.index, comments_per_minute.values, alpha=0.3, color=colors[idx % len(colors)])
        
        # 平均線
        mean_cpm = comments_per_minute.mean()
        ax.axhline(mean_cpm, color='red', linestyle='--', linewidth=1, alpha=0.7, label=f'Mean: {mean_cpm:.1f}')
        
        ax.set_title(f"{match.replace('_', ' ')}", fontsize=11, fontweight='bold')
        ax.set_xlabel('Time (minutes)', fontsize=10)
        ax.set_ylabel('Comments per Minute', fontsize=10)
        ax.legend(loc='upper right', fontsize=9)
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    output_path = OUTPUT_DIR / "longitudinal_time_series.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  ✓ 時系列パターン保存: {output_path.name}")
    plt.close()

def main():
    """メイン処理"""
    print("="*80)
    print("縦断的比較分析 - レアルマドリード3試合")
    print("Longitudinal Comparison Analysis - Real Madrid 3 Matches")
    print("="*80)
    
    print("\n🚀 分析開始\n")
    
    # 各試合のデータを読み込み
    all_data = {}
    all_metrics = []
    
    for match, info in REAL_MADRID_MATCHES.items():
        print(f"\n{'='*80}")
        print(f"📂 {match}")
        print(f"   対戦相手: {info['opponent']}")
        print(f"   重要度: Tier {info['tier']} ({info['importance']})")
        print(f"   文脈: {info['context']}")
        print(f"{'='*80}")
        
        df = load_match_data(info['folder'])
        
        if df is None:
            print(f"⚠️ {match}: データ読み込み失敗")
            continue
        
        print(f"✓ {len(df):,} コメント読み込み完了")
        print(f"  配信数: {df['stream_source'].nunique()}")
        
        all_data[match] = df
        
        # 配信ごとに指標を計算
        for stream in df['stream_source'].unique():
            stream_df = df[df['stream_source'] == stream]
            metrics = calculate_engagement_metrics(stream_df)
            metrics['match'] = match
            metrics['stream_source'] = stream
            metrics['tier'] = info['tier']
            metrics['importance'] = info['importance']
            all_metrics.append(metrics)
    
    if not all_metrics:
        print("\n❌ データが読み込めませんでした")
        return
    
    metrics_df = pd.DataFrame(all_metrics)
    
    # 結果を保存
    output_csv = OUTPUT_DIR / "longitudinal_real_madrid_metrics.csv"
    metrics_df.to_csv(output_csv, index=False, encoding='utf-8-sig')
    print(f"\n✓ 縦断的指標保存: {output_csv}")
    
    # 配信者の一貫性を確認
    print("\n" + "="*80)
    print("配信者の出現パターン...")
    print("="*80)
    
    consistent_streamers = analyze_streamer_consistency(all_data)
    
    if consistent_streamers:
        print(f"\n✅ 複数試合に出現する配信者: {len(consistent_streamers)}名")
        for streamer, matches in consistent_streamers.items():
            print(f"  - {streamer}: {', '.join(matches)}")
    else:
        print("\n⚠️ 複数試合に出現する配信者なし（試合間の直接比較が困難）")
    
    # 統計検定
    stats_results = perform_longitudinal_tests(metrics_df)
    
    # 可視化
    create_visualizations(metrics_df, all_data)
    
    # サマリーレポート作成
    create_summary_report(metrics_df, stats_results, consistent_streamers)
    
    print("\n" + "="*80)
    print("✅ 縦断的比較分析 完了")
    print("="*80)

def create_summary_report(metrics_df, stats_results, consistent_streamers):
    """サマリーレポートを作成"""
    report = []
    report.append("# 縦断的比較分析 - Longitudinal Comparison Report\n")
    report.append(f"**分析日時**: {pd.Timestamp.now().strftime('%Y年%m月%d日 %H:%M')}\n")
    report.append(f"**対象**: レアルマドリード関連3試合\n")
    report.append("---\n\n")
    
    # データ概要
    report.append("## 📊 データ概要\n\n")
    
    for match in metrics_df['match'].unique():
        match_data = metrics_df[metrics_df['match'] == match]
        report.append(f"### {match.replace('_', ' ')}\n")
        report.append(f"- 配信数: {match_data['stream_count'].iloc[0]}\n")
        report.append(f"- 総コメント数: {match_data['total_comments'].sum():,}\n")
        report.append(f"- 重要度: {match_data['importance'].iloc[0]}\n\n")
    
    # 試合別指標
    report.append("## 🎯 試合別エンゲージメント指標\n\n")
    
    summary_metrics = metrics_df.groupby('match').agg({
        'cpm': ['mean', 'std'],
        'avg_comment_length': ['mean', 'std'],
        'emoji_rate': ['mean', 'std'],
        'entropy': ['mean', 'std'],
        'burst_frequency': ['mean', 'std'],
        'cpm_cv': ['mean', 'std']
    }).round(2)
    
    report.append("| 試合 | CPM | コメント長 | 絵文字率(%) | エントロピー | バースト頻度 | CPM変動係数 |\n")
    report.append("|------|-----|-----------|------------|-------------|-------------|-------------|\n")
    
    for match in metrics_df['match'].unique():
        match_data = metrics_df[metrics_df['match'] == match]
        report.append(f"| {match.replace('_', ' ')} | "
                     f"{match_data['cpm'].mean():.1f}±{match_data['cpm'].std():.1f} | "
                     f"{match_data['avg_comment_length'].mean():.1f}±{match_data['avg_comment_length'].std():.1f} | "
                     f"{match_data['emoji_rate'].mean():.1f}±{match_data['emoji_rate'].std():.1f} | "
                     f"{match_data['entropy'].mean():.2f}±{match_data['entropy'].std():.2f} | "
                     f"{match_data['burst_frequency'].mean():.3f}±{match_data['burst_frequency'].std():.3f} | "
                     f"{match_data['cpm_cv'].mean():.2f}±{match_data['cpm_cv'].std():.2f} |\n")
    
    report.append("\n")
    
    # 統計的検定
    report.append("## 📈 統計的検定結果\n\n")
    
    if stats_results:
        for metric, result in stats_results.items():
            sig_mark = "✅ **有意**" if result['significant'] else "❌ 非有意"
            report.append(f"### {metric}\n\n")
            report.append(f"- 検定: {result['test']}\n")
            report.append(f"- 統計量: {result['statistic']:.3f}\n")
            report.append(f"- p値: {result['p_value']:.4f}\n")
            report.append(f"- 結果: {sig_mark}\n\n")
    
    # 配信者の一貫性
    report.append("## 👥 配信者の出現パターン\n\n")
    
    if consistent_streamers:
        report.append(f"**複数試合に出現する配信者**: {len(consistent_streamers)}名\n\n")
        for streamer, matches in consistent_streamers.items():
            report.append(f"- `{streamer}`: {', '.join(matches)}\n")
        report.append("\n💡 これらの配信者を用いることで、より厳密な試合間比較が可能\n\n")
    else:
        report.append("⚠️ 複数試合に出現する配信者なし\n")
        report.append("→ 試合間の直接比較には限界あり（配信者効果が混交）\n\n")
    
    # 発見と示唆
    report.append("## 🔍 主要な発見\n\n")
    
    # CPMの変化
    cpm_by_match = metrics_df.groupby('match')['cpm'].mean().sort_values(ascending=False)
    report.append("### CPM（コメント密度）の変化\n\n")
    for match, cpm in cpm_by_match.items():
        tier = metrics_df[metrics_df['match'] == match]['tier'].iloc[0]
        report.append(f"- **{match.replace('_', ' ')}** (Tier {tier}): {cpm:.1f} CPM\n")
    report.append("\n")
    
    # 時系列パターンの特徴
    report.append("### 時系列パターンの特徴\n\n")
    burst_by_match = metrics_df.groupby('match')['burst_frequency'].mean().sort_values(ascending=False)
    for match, freq in burst_by_match.items():
        report.append(f"- **{match.replace('_', ' ')}**: バースト頻度 {freq:.3f}\n")
    report.append("\n")
    
    # 今後の展開
    report.append("## 🚀 今後の展開\n\n")
    report.append("1. **同一配信者での試合間比較**\n")
    report.append("   - 複数試合に出現する配信者に絞った分析\n")
    report.append("   - 配信者効果を制御した純粋な試合効果の抽出\n\n")
    
    report.append("2. **試合展開との対応**\n")
    report.append("   - 得点シーンとコメントバーストの対応分析\n")
    report.append("   - 試合の緊迫度とエンゲージメントの関係\n\n")
    
    report.append("3. **他チームとの比較**\n")
    report.append("   - レアルマドリードと他チームの縦断的パターン比較\n")
    report.append("   - チーム特性（攻撃的 vs 守備的）の影響\n\n")
    
    # ファイル保存
    report_path = OUTPUT_DIR / "LONGITUDINAL_ANALYSIS_SUMMARY.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.writelines(report)
    
    print(f"\n✓ サマリーレポート保存: {report_path}")

if __name__ == "__main__":
    main()
