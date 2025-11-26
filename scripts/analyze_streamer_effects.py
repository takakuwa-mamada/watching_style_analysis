"""
配信者効果の分離 - 混交変数の制御
Streamer Effect Separation - Confounding Variable Control

目的:
- 配信者の個人特性（配信スタイル、視聴者層）を制御
- 試合特性の純粋な効果を推定
- 混合効果モデルによる階層的分析
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

# statsmodelsをインポート（混合効果モデル用）
try:
    import statsmodels.api as sm
    import statsmodels.formula.api as smf
    from statsmodels.regression.mixed_linear_model import MixedLM
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False
    print("⚠️ statsmodelsがインストールされていません。pip install statsmodels を実行してください。")

# データディレクトリ
DATA_DIR = Path(r"G:\マイドライブ\大学\4年\ゼミ\watching_style_analysis\data\football")
OUTPUT_DIR = Path(r"G:\マイドライブ\大学\4年\ゼミ\watching_style_analysis\output\streamer_effects")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 試合メタデータ（日本語フォルダ名にマッピング）
MATCH_METADATA = {
    "Real_Madrid_vs_Barcelona": {"folder": "レアルマドリードvsバルセロナ", "tier": 1, "importance_score": 10},
    "Brazil_vs_Japan": {"folder": "ブラジルvs日本", "tier": 2, "importance_score": 8},
    "Brighton_vs_Man_City": {"folder": "ブライトンvsマンチェスターシティ", "tier": 3, "importance_score": 5},
    "Real_Sociedad_vs_Real_Madrid": {"folder": "レアルソシエダvsレアルマドリード", "tier": 3, "importance_score": 5},
    "Leeds_vs_Spurs": {"folder": "リーズユナイテッドvsスパーズ", "tier": 4, "importance_score": 3},
    "PSG_vs_Inter_Miami": {"folder": "パリサンジェルマンvsインテルマイアミ", "tier": 4, "importance_score": 2}
}

def load_all_streams():
    """
    全配信のデータを読み込み
    
    Returns:
    --------
    pd.DataFrame : 全配信データ
    """
    all_streams = []
    
    for match, metadata in MATCH_METADATA.items():
        folder_path = DATA_DIR / metadata['folder']
        
        # CSVファイルを検索
        csv_files = list(folder_path.glob("*_chat_log.csv"))
        if not csv_files:
            csv_files = list(folder_path.glob("*.csv"))
        
        if not csv_files:
            continue
        
        for csv_file in csv_files:
            try:
                df = pd.read_csv(csv_file, encoding='utf-8')
                
                # カラム名を正規化
                if 'message' in df.columns:
                    df.rename(columns={'message': 'comment'}, inplace=True)
                
                if 'comment' not in df.columns:
                    continue
                
                # メタデータを追加
                df['match'] = match
                df['stream_source'] = csv_file.stem
                df['tier'] = metadata['tier']
                df['importance_score'] = metadata['importance_score']
                
                all_streams.append(df)
            except Exception as e:
                print(f"⚠️ {csv_file.name}: 読み込みエラー - {e}")
                continue
    
    if not all_streams:
        return None
    
    combined_df = pd.concat(all_streams, ignore_index=True)
    return combined_df

def calculate_stream_metrics(df):
    """
    配信レベルのエンゲージメント指標を計算
    
    Parameters:
    -----------
    df : pd.DataFrame
        配信データ
        
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
    cpm = total_comments / duration_minutes if duration_minutes > 0 else np.nan
    
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
        entropy = np.nan
    
    return {
        'cpm': cpm,
        'avg_comment_length': avg_length,
        'emoji_rate': emoji_rate,
        'entropy': entropy,
        'total_comments': total_comments,
        'duration_minutes': duration_minutes
    }

def identify_streamer_profiles(stream_metrics_df):
    """
    配信者のプロファイルを特定
    
    Parameters:
    -----------
    stream_metrics_df : pd.DataFrame
        配信レベルの指標
        
    Returns:
    --------
    pd.DataFrame : 配信者プロファイル
    """
    print("\n" + "="*80)
    print("配信者プロファイルの特定...")
    print("="*80)
    
    # 複数試合に出現する配信者
    streamer_counts = stream_metrics_df['stream_source'].value_counts()
    multi_match_streamers = streamer_counts[streamer_counts > 1].index.tolist()
    
    print(f"\n✅ 複数試合に出現する配信者: {len(multi_match_streamers)}名")
    
    if multi_match_streamers:
        print("\n配信者別の平均指標:")
        for streamer in multi_match_streamers:
            streamer_data = stream_metrics_df[stream_metrics_df['stream_source'] == streamer]
            print(f"\n  {streamer}:")
            print(f"    出現試合数: {len(streamer_data)}")
            print(f"    平均CPM: {streamer_data['cpm'].mean():.2f}")
            print(f"    平均コメント長: {streamer_data['avg_comment_length'].mean():.1f}")
            print(f"    平均絵文字率: {streamer_data['emoji_rate'].mean():.1f}%")
    
    # 配信者の平均プロファイルを計算
    streamer_profiles = stream_metrics_df.groupby('stream_source').agg({
        'cpm': 'mean',
        'avg_comment_length': 'mean',
        'emoji_rate': 'mean',
        'entropy': 'mean',
        'total_comments': 'sum'
    }).reset_index()
    
    streamer_profiles['appearance_count'] = stream_metrics_df.groupby('stream_source').size().values
    
    return streamer_profiles

def fit_mixed_effects_models(stream_metrics_df):
    """
    混合効果モデルをフィット
    
    Parameters:
    -----------
    stream_metrics_df : pd.DataFrame
        配信レベルの指標
        
    Returns:
    --------
    dict : モデル結果
    """
    if not STATSMODELS_AVAILABLE:
        print("\n⚠️ statsmodelsがインストールされていません")
        return {}
    
    print("\n" + "="*80)
    print("混合効果モデルのフィット...")
    print("="*80)
    
    # 配信者を変量効果、試合重要度を固定効果とする
    results = {}
    
    dependent_vars = ['cpm', 'avg_comment_length', 'emoji_rate', 'entropy']
    
    for dep_var in dependent_vars:
        print(f"\n📊 従属変数: {dep_var}")
        
        # 欠損値を除外
        model_data = stream_metrics_df[['stream_source', 'importance_score', dep_var]].dropna()
        
        if len(model_data) < 10:
            print(f"  ⚠️ サンプル数不足: N={len(model_data)}")
            continue
        
        try:
            # 混合効果モデル: 従属変数 ~ 重要度 + (1 | 配信者)
            model = MixedLM.from_formula(
                f'{dep_var} ~ importance_score',
                data=model_data,
                groups=model_data['stream_source']
            )
            
            result = model.fit(reml=False)  # ML推定
            
            print(f"\n  固定効果（重要度の影響）:")
            print(f"    係数: {result.params['importance_score']:.4f}")
            print(f"    p値: {result.pvalues['importance_score']:.4f}")
            
            print(f"\n  変量効果（配信者のばらつき）:")
            print(f"    σ²_配信者: {result.cov_re.values[0][0]:.4f}")
            print(f"    σ²_残差: {result.scale:.4f}")
            
            # ICC（級内相関係数）- 配信者効果の大きさ
            icc = result.cov_re.values[0][0] / (result.cov_re.values[0][0] + result.scale)
            print(f"    ICC: {icc:.4f} ({icc*100:.1f}%が配信者による)")
            
            results[dep_var] = {
                'fixed_effect': result.params['importance_score'],
                'fixed_pvalue': result.pvalues['importance_score'],
                'random_var': result.cov_re.values[0][0],
                'residual_var': result.scale,
                'icc': icc,
                'aic': result.aic,
                'bic': result.bic
            }
            
        except Exception as e:
            print(f"  ⚠️ モデルフィットエラー: {e}")
            continue
    
    return results

def compare_controlled_vs_uncontrolled(stream_metrics_df):
    """
    配信者効果を制御した場合としない場合の比較
    
    Parameters:
    -----------
    stream_metrics_df : pd.DataFrame
        配信レベルの指標
        
    Returns:
    --------
    dict : 比較結果
    """
    print("\n" + "="*80)
    print("配信者効果の制御前後の比較...")
    print("="*80)
    
    results = {}
    
    dependent_vars = ['cpm', 'avg_comment_length', 'emoji_rate', 'entropy']
    
    for dep_var in dependent_vars:
        print(f"\n📊 {dep_var}:")
        
        model_data = stream_metrics_df[['importance_score', dep_var]].dropna()
        
        if len(model_data) < 10:
            continue
        
        # 1. 単純な相関（配信者効果を制御しない）
        corr, p_corr = stats.spearmanr(model_data['importance_score'], model_data[dep_var])
        print(f"\n  配信者効果を制御しない:")
        print(f"    Spearman相関: ρ={corr:.3f}, p={p_corr:.4f}")
        
        # 2. 配信者内での相関（配信者効果を制御）
        within_streamer_corrs = []
        
        for streamer in stream_metrics_df['stream_source'].unique():
            streamer_data = stream_metrics_df[stream_metrics_df['stream_source'] == streamer]
            
            if len(streamer_data) < 2:  # 最低2試合必要
                continue
            
            streamer_corr, _ = stats.spearmanr(
                streamer_data['importance_score'], 
                streamer_data[dep_var]
            )
            
            if not np.isnan(streamer_corr):
                within_streamer_corrs.append(streamer_corr)
        
        if within_streamer_corrs:
            mean_within_corr = np.mean(within_streamer_corrs)
            print(f"\n  配信者効果を制御:")
            print(f"    平均配信者内相関: ρ={mean_within_corr:.3f}")
            print(f"    N={len(within_streamer_corrs)}名の配信者")
        else:
            mean_within_corr = np.nan
            print(f"\n  ⚠️ 配信者内相関を計算できません（複数試合出演の配信者不足）")
        
        results[dep_var] = {
            'uncontrolled_corr': corr,
            'uncontrolled_pvalue': p_corr,
            'controlled_corr': mean_within_corr,
            'n_streamers': len(within_streamer_corrs) if within_streamer_corrs else 0
        }
    
    return results

def create_visualizations(stream_metrics_df, mixed_results, comparison_results):
    """
    配信者効果の可視化
    
    Parameters:
    -----------
    stream_metrics_df : pd.DataFrame
        配信レベルの指標
    mixed_results : dict
        混合効果モデル結果
    comparison_results : dict
        制御前後の比較結果
    """
    print("\n" + "="*80)
    print("可視化作成中...")
    print("="*80)
    
    # 1. ICCの可視化（配信者効果の大きさ）
    if mixed_results:
        fig, ax = plt.subplots(figsize=(10, 6))
        
        metrics = list(mixed_results.keys())
        iccs = [mixed_results[m]['icc'] for m in metrics]
        
        colors = ['#FF6B6B' if icc > 0.5 else '#4ECDC4' for icc in iccs]
        bars = ax.barh(metrics, iccs, color=colors, alpha=0.7, edgecolor='black')
        
        ax.axvline(0.5, color='red', linestyle='--', linewidth=1.5, 
                   label='ICC=0.5 (50% threshold)', alpha=0.7)
        
        ax.set_xlabel('ICC (Intraclass Correlation Coefficient)', fontsize=12, fontweight='bold')
        ax.set_title('配信者効果の大きさ\nStreamer Effect Magnitude (ICC)', 
                     fontsize=14, fontweight='bold')
        ax.set_xlim(0, 1)
        ax.legend(loc='lower right')
        ax.grid(True, alpha=0.3, axis='x')
        
        # 値をバーに表示
        for i, (metric, icc) in enumerate(zip(metrics, iccs)):
            ax.text(icc + 0.02, i, f'{icc*100:.1f}%', va='center', fontsize=10, fontweight='bold')
        
        plt.tight_layout()
        output_path = OUTPUT_DIR / "streamer_effect_icc.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"  ✓ ICC可視化保存: {output_path.name}")
        plt.close()
    
    # 2. 配信者別の散布図
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('配信者別のエンゲージメント指標\nEngagement Metrics by Streamer', 
                 fontsize=16, fontweight='bold')
    
    metrics_to_plot = [
        ('cpm', 'Comments Per Minute (CPM)', axes[0, 0]),
        ('avg_comment_length', 'Average Comment Length (characters)', axes[0, 1]),
        ('emoji_rate', 'Emoji Usage Rate (%)', axes[1, 0]),
        ('entropy', 'Comment Diversity (Entropy)', axes[1, 1])
    ]
    
    # 配信者ごとに色を割り当て
    unique_streamers = stream_metrics_df['stream_source'].unique()
    colors = sns.color_palette('husl', len(unique_streamers))
    streamer_colors = dict(zip(unique_streamers, colors))
    
    for metric, title, ax in metrics_to_plot:
        for streamer in unique_streamers:
            streamer_data = stream_metrics_df[stream_metrics_df['stream_source'] == streamer]
            
            if len(streamer_data) < 1:
                continue
            
            ax.scatter(
                streamer_data['importance_score'], 
                streamer_data[metric],
                color=streamer_colors[streamer],
                alpha=0.6,
                s=100,
                edgecolors='black',
                linewidth=0.5,
                label=streamer if len(streamer_data) > 1 else ''
            )
            
            # 複数試合出演の配信者は線で結ぶ
            if len(streamer_data) > 1:
                streamer_data_sorted = streamer_data.sort_values('importance_score')
                ax.plot(
                    streamer_data_sorted['importance_score'],
                    streamer_data_sorted[metric],
                    color=streamer_colors[streamer],
                    alpha=0.3,
                    linewidth=1
                )
        
        ax.set_xlabel('Match Importance Score', fontsize=10, fontweight='bold')
        ax.set_ylabel(title.split('(')[0].strip(), fontsize=10, fontweight='bold')
        ax.set_title(title, fontsize=11, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        # 凡例は表示しない（配信者が多すぎる場合があるため）
    
    plt.tight_layout()
    output_path = OUTPUT_DIR / "streamer_effect_scatter.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  ✓ 散布図保存: {output_path.name}")
    plt.close()

def main():
    """メイン処理"""
    print("="*80)
    print("配信者効果の分離 - Streamer Effect Separation")
    print("="*80)
    
    print("\n🚀 分析開始\n")
    
    # 全配信データを読み込み
    print("📂 データ読み込み中...")
    all_data = load_all_streams()
    
    if all_data is None:
        print("\n❌ データが読み込めませんでした")
        return
    
    print(f"✓ {len(all_data):,} コメント読み込み完了")
    print(f"  試合数: {all_data['match'].nunique()}")
    print(f"  配信数: {all_data['stream_source'].nunique()}")
    
    # 配信レベルの指標を計算
    print("\n" + "="*80)
    print("配信レベルの指標計算...")
    print("="*80)
    
    stream_metrics = []
    
    for (match, stream), group in all_data.groupby(['match', 'stream_source']):
        metrics = calculate_stream_metrics(group)
        metrics['match'] = match
        metrics['stream_source'] = stream
        metrics['tier'] = group['tier'].iloc[0]
        metrics['importance_score'] = group['importance_score'].iloc[0]
        stream_metrics.append(metrics)
    
    stream_metrics_df = pd.DataFrame(stream_metrics)
    
    # 欠損値を除外
    stream_metrics_df = stream_metrics_df.dropna(subset=['cpm', 'avg_comment_length', 'emoji_rate', 'entropy'])
    
    print(f"\n✓ {len(stream_metrics_df)} 配信の指標計算完了")
    
    # 結果を保存
    output_csv = OUTPUT_DIR / "stream_metrics_with_match_info.csv"
    stream_metrics_df.to_csv(output_csv, index=False, encoding='utf-8-sig')
    print(f"✓ 配信指標保存: {output_csv}")
    
    # 配信者プロファイルの特定
    streamer_profiles = identify_streamer_profiles(stream_metrics_df)
    
    # 配信者プロファイルを保存
    profile_csv = OUTPUT_DIR / "streamer_profiles.csv"
    streamer_profiles.to_csv(profile_csv, index=False, encoding='utf-8-sig')
    print(f"\n✓ 配信者プロファイル保存: {profile_csv}")
    
    # 混合効果モデルのフィット
    mixed_results = fit_mixed_effects_models(stream_metrics_df)
    
    # 制御前後の比較
    comparison_results = compare_controlled_vs_uncontrolled(stream_metrics_df)
    
    # 可視化
    create_visualizations(stream_metrics_df, mixed_results, comparison_results)
    
    # サマリーレポート作成
    create_summary_report(stream_metrics_df, mixed_results, comparison_results, streamer_profiles)
    
    print("\n" + "="*80)
    print("✅ 配信者効果の分離 完了")
    print("="*80)

def create_summary_report(stream_metrics_df, mixed_results, comparison_results, streamer_profiles):
    """サマリーレポートを作成"""
    report = []
    report.append("# 配信者効果の分離 - Streamer Effect Separation Report\n")
    report.append(f"**分析日時**: {pd.Timestamp.now().strftime('%Y年%m月%d日 %H:%M')}\n")
    report.append(f"**方法**: 混合効果モデル（配信者を変量効果として制御）\n")
    report.append("---\n\n")
    
    # データ概要
    report.append("## 📊 データ概要\n\n")
    report.append(f"- **総配信数**: {len(stream_metrics_df)}\n")
    report.append(f"- **試合数**: {stream_metrics_df['match'].nunique()}\n")
    report.append(f"- **配信者数**: {stream_metrics_df['stream_source'].nunique()}\n")
    report.append(f"- **複数試合出演配信者**: {len(streamer_profiles[streamer_profiles['appearance_count'] > 1])}名\n\n")
    
    # 混合効果モデル結果
    if mixed_results:
        report.append("## 🎯 混合効果モデル結果\n\n")
        report.append("配信者を変量効果として制御し、試合重要度の純粋な効果を推定\n\n")
        
        report.append("| 指標 | 重要度係数 | p値 | ICC | 配信者効果(%) |\n")
        report.append("|------|-----------|-----|-----|-------------|\n")
        
        for metric, result in mixed_results.items():
            sig_mark = "**有意**" if result['fixed_pvalue'] < 0.05 else "非有意"
            report.append(f"| {metric} | {result['fixed_effect']:.4f} | "
                         f"{result['fixed_pvalue']:.4f} ({sig_mark}) | "
                         f"{result['icc']:.3f} | {result['icc']*100:.1f}% |\n")
        
        report.append("\n**ICC (Intraclass Correlation)**: 全体のばらつきのうち配信者による部分\n\n")
    
    # 制御前後の比較
    if comparison_results:
        report.append("## 📈 配信者効果の制御前後の比較\n\n")
        
        report.append("| 指標 | 制御なし相関 | 制御あり相関 | 差 |\n")
        report.append("|------|-------------|-------------|----|\n")
        
        for metric, result in comparison_results.items():
            diff = result['uncontrolled_corr'] - result['controlled_corr']
            diff_str = f"{diff:+.3f}" if not np.isnan(diff) else "N/A"
            controlled_str = f"{result['controlled_corr']:.3f}" if not np.isnan(result['controlled_corr']) else "N/A"
            
            report.append(f"| {metric} | {result['uncontrolled_corr']:.3f} | "
                         f"{controlled_str} | {diff_str} |\n")
        
        report.append("\n")
    
    # 配信者プロファイル
    report.append("## 👥 配信者プロファイル（上位10名）\n\n")
    
    top_streamers = streamer_profiles.nlargest(10, 'total_comments')
    
    report.append("| 配信者 | 出現回数 | 平均CPM | 平均コメント長 | 絵文字率(%) |\n")
    report.append("|--------|---------|---------|---------------|------------|\n")
    
    for _, streamer in top_streamers.iterrows():
        report.append(f"| {streamer['stream_source']} | {streamer['appearance_count']:.0f} | "
                     f"{streamer['cpm']:.1f} | {streamer['avg_comment_length']:.1f} | "
                     f"{streamer['emoji_rate']:.1f} |\n")
    
    report.append("\n")
    
    # 主要な発見
    report.append("## 🔍 主要な発見\n\n")
    
    if mixed_results:
        # ICC最大の指標
        max_icc_metric = max(mixed_results.items(), key=lambda x: x[1]['icc'])
        report.append(f"### 配信者効果が最も大きい指標\n\n")
        report.append(f"**{max_icc_metric[0]}**: ICC={max_icc_metric[1]['icc']:.3f} ")
        report.append(f"({max_icc_metric[1]['icc']*100:.1f}%が配信者による)\n\n")
        
        # 有意な固定効果
        sig_effects = [m for m, r in mixed_results.items() if r['fixed_pvalue'] < 0.05]
        if sig_effects:
            report.append(f"### 配信者効果を制御しても有意な試合重要度の効果\n\n")
            for metric in sig_effects:
                result = mixed_results[metric]
                report.append(f"- **{metric}**: 係数={result['fixed_effect']:.4f}, p={result['fixed_pvalue']:.4f}\n")
            report.append("\n")
    
    # 方法論的意義
    report.append("## 🔬 方法論的意義\n\n")
    report.append("### 混交変数の問題\n")
    report.append("- 配信者によって視聴者層、配信スタイル、言語が異なる\n")
    report.append("- 試合重要度と配信者の選択が交絡している可能性\n")
    report.append("- 単純な比較では試合効果と配信者効果を分離できない\n\n")
    
    report.append("### 本手法の利点\n")
    report.append("- **混合効果モデル**: 配信者を変量効果として階層的にモデル化\n")
    report.append("- **ICC**: 配信者効果の大きさを定量化\n")
    report.append("- **純粋な試合効果**: 配信者のばらつきを制御した推定\n\n")
    
    # 今後の展開
    report.append("## 🚀 今後の展開\n\n")
    report.append("1. **より複雑な階層モデル**\n")
    report.append("   - 試合内に配信者がネストされた3レベルモデル\n")
    report.append("   - 時間変動を考慮した縦断的混合モデル\n\n")
    
    report.append("2. **配信者特性の詳細分析**\n")
    report.append("   - 配信スタイル（実況型 vs 解説型）の分類\n")
    report.append("   - 視聴者層（カジュアル vs ハードコア）の推定\n\n")
    
    report.append("3. **交互作用効果**\n")
    report.append("   - 試合重要度 × 配信者スタイルの交互作用\n")
    report.append("   - 配信者によって異なる試合重要度の効果\n\n")
    
    # ファイル保存
    report_path = OUTPUT_DIR / "STREAMER_EFFECT_ANALYSIS_SUMMARY.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.writelines(report)
    
    print(f"\n✓ サマリーレポート保存: {report_path}")

if __name__ == "__main__":
    main()
