import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

# Set Japanese font
plt.rcParams['font.sans-serif'] = ['Meiryo', 'Yu Gothic', 'MS Gothic']
plt.rcParams['axes.unicode_minus'] = False

# Load data
df = pd.read_csv('output/event_to_event_pairs.csv')

# Calculate baseline scores for comparison
baseline_scores = (df['embedding_similarity'] * 0.40 + 
                   df['topic_jaccard'] * 0.40 + 
                   df['lexical_similarity'] * 0.20)

phase2_scores = (df['embedding_similarity'] * 0.30 + 
                 df['topic_jaccard'] * 0.55 + 
                 df['lexical_similarity'] * 0.15)

phase3_scores = df['combined_score']

print('Creating paper-ready visualizations...')

# Figure 1: Weight Optimization Progress
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# Subplot 1: Weight distribution across phases
phases = ['Phase 1.6\n(Baseline)', 'Phase 2\n(Failed)', 'Phase 3\n(Success)']
embedding_weights = [0.40, 0.30, 0.70]
topic_weights = [0.40, 0.55, 0.20]
lexical_weights = [0.20, 0.15, 0.10]

x = np.arange(len(phases))
width = 0.25

bars1 = ax1.bar(x - width, embedding_weights, width, label='Embedding', color='#2E86AB')
bars2 = ax1.bar(x, topic_weights, width, label='Topic', color='#A23B72')
bars3 = ax1.bar(x + width, lexical_weights, width, label='Lexical', color='#F18F01')

ax1.set_ylabel('Weight', fontsize=12)
ax1.set_title('(a) Weight Distribution Across Phases', fontsize=13, fontweight='bold')
ax1.set_xticks(x)
ax1.set_xticklabels(phases)
ax1.legend(loc='upper left')
ax1.set_ylim(0, 0.8)
ax1.grid(axis='y', alpha=0.3)

# Add value labels on bars
for bars in [bars1, bars2, bars3]:
    for bar in bars:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.2f}', ha='center', va='bottom', fontsize=9)

# Subplot 2: Average score progression
scores_by_phase = [baseline_scores.mean(), phase2_scores.mean(), phase3_scores.mean()]
colors = ['#4CAF50', '#F44336', '#2196F3']
bars = ax2.bar(phases, scores_by_phase, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)

ax2.axhline(y=0.350, color='red', linestyle='--', linewidth=2, label='November Goal (0.350)')
ax2.set_ylabel('Average Combined Score', fontsize=12)
ax2.set_title('(b) Performance Progression', fontsize=13, fontweight='bold')
ax2.set_ylim(0, 0.4)
ax2.legend()
ax2.grid(axis='y', alpha=0.3)

# Add value labels and change indicators
for i, (bar, score) in enumerate(zip(bars, scores_by_phase)):
    height = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2., height + 0.01,
            f'{score:.3f}', ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    if i > 0:
        change = score - scores_by_phase[i-1]
        symbol = '↑' if change > 0 else '↓'
        color = 'green' if change > 0 else 'red'
        ax2.text(bar.get_x() + bar.get_width()/2., 0.05,
                f'{symbol}{abs(change):.3f}', ha='center', fontsize=9, color=color, fontweight='bold')

plt.tight_layout()
plt.savefig('output/paper_figure1_optimization_progress.png', dpi=300, bbox_inches='tight')
print('✅ Figure 1 saved: output/paper_figure1_optimization_progress.png')
plt.close()

# Figure 2: Component Contribution Analysis
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# Subplot 1: Pie chart of score contribution
emb_contrib = df['embedding_similarity'].mean() * 0.70
top_contrib = df['topic_jaccard'].mean() * 0.20
lex_contrib = df['lexical_similarity'].mean() * 0.10
total = emb_contrib + top_contrib + lex_contrib

contributions = [emb_contrib, top_contrib, lex_contrib]
labels = ['Embedding\n(70% weight)', 'Topic\n(20% weight)', 'Lexical\n(10% weight)']
colors = ['#2E86AB', '#A23B72', '#F18F01']
explode = (0.05, 0, 0)

wedges, texts, autotexts = ax1.pie(contributions, labels=labels, autopct='%1.1f%%',
                                     colors=colors, explode=explode, startangle=90,
                                     textprops={'fontsize': 11})

for autotext in autotexts:
    autotext.set_color('white')
    autotext.set_fontweight('bold')
    autotext.set_fontsize(12)

ax1.set_title('(a) Component Contribution to Final Score', fontsize=13, fontweight='bold')

# Subplot 2: Component mean values
components = ['Embedding\nSimilarity', 'Topic\nJaccard', 'Lexical\nSimilarity']
means = [df['embedding_similarity'].mean(), 
         df['topic_jaccard'].mean(), 
         df['lexical_similarity'].mean()]

bars = ax2.bar(components, means, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)
ax2.set_ylabel('Mean Value', fontsize=12)
ax2.set_title('(b) Component Mean Values (Before Weighting)', fontsize=13, fontweight='bold')
ax2.set_ylim(0, 0.6)
ax2.grid(axis='y', alpha=0.3)

# Add value labels
for bar, mean in zip(bars, means):
    height = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2., height + 0.01,
            f'{mean:.3f}', ha='center', va='bottom', fontsize=11, fontweight='bold')

plt.tight_layout()
plt.savefig('output/paper_figure2_component_analysis.png', dpi=300, bbox_inches='tight')
print('✅ Figure 2 saved: output/paper_figure2_component_analysis.png')
plt.close()

# Figure 3: Score Distribution Comparison
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# Subplot 1: Histogram comparison
ax1 = axes[0, 0]
ax1.hist(baseline_scores, bins=15, alpha=0.5, label='Phase 1.6 (Baseline)', color='#4CAF50', edgecolor='black')
ax1.hist(phase3_scores, bins=15, alpha=0.5, label='Phase 3 (Optimized)', color='#2196F3', edgecolor='black')
ax1.axvline(baseline_scores.mean(), color='#4CAF50', linestyle='--', linewidth=2, label=f'Baseline Mean: {baseline_scores.mean():.3f}')
ax1.axvline(phase3_scores.mean(), color='#2196F3', linestyle='--', linewidth=2, label=f'Phase 3 Mean: {phase3_scores.mean():.3f}')
ax1.axvline(0.350, color='red', linestyle=':', linewidth=2, label='Goal: 0.350')
ax1.set_xlabel('Combined Score', fontsize=11)
ax1.set_ylabel('Frequency', fontsize=11)
ax1.set_title('(a) Score Distribution: Baseline vs. Phase 3', fontsize=12, fontweight='bold')
ax1.legend(fontsize=9)
ax1.grid(alpha=0.3)

# Subplot 2: Box plot comparison
ax2 = axes[0, 1]
data_to_plot = [baseline_scores, phase2_scores, phase3_scores]
bp = ax2.boxplot(data_to_plot, labels=['Phase 1.6', 'Phase 2', 'Phase 3'],
                 patch_artist=True, widths=0.6)

colors_box = ['#4CAF50', '#F44336', '#2196F3']
for patch, color in zip(bp['boxes'], colors_box):
    patch.set_facecolor(color)
    patch.set_alpha(0.6)

ax2.axhline(y=0.350, color='red', linestyle='--', linewidth=2, label='Goal')
ax2.set_ylabel('Combined Score', fontsize=11)
ax2.set_title('(b) Score Distribution by Phase', fontsize=12, fontweight='bold')
ax2.legend()
ax2.grid(axis='y', alpha=0.3)

# Subplot 3: Cumulative distribution
ax3 = axes[1, 0]
sorted_baseline = np.sort(baseline_scores)
sorted_phase3 = np.sort(phase3_scores)
cumulative_baseline = np.arange(1, len(sorted_baseline) + 1) / len(sorted_baseline)
cumulative_phase3 = np.arange(1, len(sorted_phase3) + 1) / len(sorted_phase3)

ax3.plot(sorted_baseline, cumulative_baseline, label='Phase 1.6', color='#4CAF50', linewidth=2)
ax3.plot(sorted_phase3, cumulative_phase3, label='Phase 3', color='#2196F3', linewidth=2)
ax3.axvline(0.350, color='red', linestyle='--', linewidth=2, label='Goal')
ax3.set_xlabel('Combined Score', fontsize=11)
ax3.set_ylabel('Cumulative Probability', fontsize=11)
ax3.set_title('(c) Cumulative Distribution Function', fontsize=12, fontweight='bold')
ax3.legend()
ax3.grid(alpha=0.3)

# Subplot 4: Quality category distribution
ax4 = axes[1, 1]
categories = ['High\n(≥0.7)', 'Mid\n(0.5-0.7)', 'Low\n(<0.5)']

baseline_high = len(baseline_scores[baseline_scores >= 0.7])
baseline_mid = len(baseline_scores[(baseline_scores >= 0.5) & (baseline_scores < 0.7)])
baseline_low = len(baseline_scores[baseline_scores < 0.5])

phase3_high = len(phase3_scores[phase3_scores >= 0.7])
phase3_mid = len(phase3_scores[(phase3_scores >= 0.5) & (phase3_scores < 0.7)])
phase3_low = len(phase3_scores[phase3_scores < 0.5])

x = np.arange(len(categories))
width = 0.35

bars1 = ax4.bar(x - width/2, [baseline_high, baseline_mid, baseline_low], width, 
                label='Phase 1.6', color='#4CAF50', alpha=0.7, edgecolor='black')
bars2 = ax4.bar(x + width/2, [phase3_high, phase3_mid, phase3_low], width,
                label='Phase 3', color='#2196F3', alpha=0.7, edgecolor='black')

ax4.set_ylabel('Number of Pairs', fontsize=11)
ax4.set_title('(d) Quality Category Distribution', fontsize=12, fontweight='bold')
ax4.set_xticks(x)
ax4.set_xticklabels(categories)
ax4.legend()
ax4.grid(axis='y', alpha=0.3)

# Add value labels
for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        if height > 0:
            ax4.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}', ha='center', va='bottom', fontsize=9)

plt.tight_layout()
plt.savefig('output/paper_figure3_distribution_analysis.png', dpi=300, bbox_inches='tight')
print('✅ Figure 3 saved: output/paper_figure3_distribution_analysis.png')
plt.close()

# Figure 4: Topic Coverage Analysis
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# Subplot 1: Topic coverage pie chart
topic_zero = len(df[df['topic_jaccard'] == 0])
topic_low = len(df[(df['topic_jaccard'] > 0) & (df['topic_jaccard'] <= 0.3)])
topic_mid = len(df[(df['topic_jaccard'] > 0.3) & (df['topic_jaccard'] <= 0.7)])
topic_high = len(df[df['topic_jaccard'] > 0.7])

sizes = [topic_zero, topic_low, topic_mid, topic_high]
labels = [f'No Overlap\n(jaccard=0)\n{topic_zero} pairs', 
          f'Low\n(0<j≤0.3)\n{topic_low} pairs',
          f'Mid\n(0.3<j≤0.7)\n{topic_mid} pairs',
          f'High\n(j>0.7)\n{topic_high} pairs']
colors = ['#E0E0E0', '#FFC107', '#FF9800', '#4CAF50']
explode = (0.1, 0, 0, 0.05)

wedges, texts, autotexts = ax1.pie(sizes, labels=labels, autopct='%1.1f%%',
                                     colors=colors, explode=explode, startangle=90,
                                     textprops={'fontsize': 10})

for autotext in autotexts:
    autotext.set_color('white')
    autotext.set_fontweight('bold')

ax1.set_title('(a) Topic Overlap Distribution\n(Data Limitation: 82.1% Zero Overlap)', 
              fontsize=12, fontweight='bold')

# Subplot 2: Scatter plot - embedding vs topic
ax2.scatter(df['embedding_similarity'], df['topic_jaccard'], 
           c=df['combined_score'], cmap='viridis', s=100, alpha=0.7, edgecolors='black')
ax2.set_xlabel('Embedding Similarity', fontsize=11)
ax2.set_ylabel('Topic Jaccard', fontsize=11)
ax2.set_title('(b) Embedding vs. Topic Similarity\n(Color: Combined Score)', 
              fontsize=12, fontweight='bold')
ax2.grid(alpha=0.3)

# Add colorbar
cbar = plt.colorbar(ax2.collections[0], ax=ax2)
cbar.set_label('Combined Score', fontsize=10)

# Highlight Event 56<->59 (perfect topic match)
event_56_59 = df[((df['event_A_id']==56) & (df['event_B_id']==59)) | 
                 ((df['event_A_id']==59) & (df['event_B_id']==56))]
if len(event_56_59) > 0:
    row = event_56_59.iloc[0]
    ax2.scatter(row['embedding_similarity'], row['topic_jaccard'],
               s=300, facecolors='none', edgecolors='red', linewidths=3, 
               label='Event 56↔59\n(Perfect Match)')
    ax2.legend(loc='lower right')

plt.tight_layout()
plt.savefig('output/paper_figure4_topic_analysis.png', dpi=300, bbox_inches='tight')
print('✅ Figure 4 saved: output/paper_figure4_topic_analysis.png')
plt.close()

print('\n' + '='*80)
print('All paper-ready figures created successfully!')
print('='*80)
print('\nFigure Summary:')
print('  1. paper_figure1_optimization_progress.png - Weight & performance evolution')
print('  2. paper_figure2_component_analysis.png - Component contributions')
print('  3. paper_figure3_distribution_analysis.png - Score distributions')
print('  4. paper_figure4_topic_analysis.png - Topic coverage & limitation')
print('\nAll figures saved to: output/')
print('='*80)
