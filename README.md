# Cross-Cultural Sports Fan Engagement Analysis on SNS

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Research](https://img.shields.io/badge/Status-Research%20Complete-success)](https://github.com/takakuwa-mamada/watching_style_analysis)

A comprehensive research project analyzing cross-cultural differences in sports fan engagement styles on live streaming platforms using Natural Language Processing and BERTopic modeling.

## 📊 Research Overview

This project analyzes **42,556 multilingual comments** from **9 live streams** across **4 countries** (Spain, Japan, UK, France) during El Clásico (Real Madrid vs. Barcelona) to identify distinct cultural engagement patterns in online sports viewing.

### Key Findings

We identified **4 distinct cultural engagement styles**:

- 🇯🇵 **Japan**: Social-Casual Style (32.95% in greeting topics, sustained engagement)
- 🇪🇸 **Spain**: Traditional Chanting Style (18.28% in team chants, strong first-half focus)
- 🇬🇧 **UK**: Analytical & Controversy-Focused Style (highest in penalty/offside debates)
- 🇫🇷 **France**: Emotional & Emoji-Heavy Style (10.99% emoji reactions, early spike pattern)

## 🏗️ Project Structure

```
watching_style_analysis/
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── .gitignore               # Git ignore rules
│
├── data/                    # Raw data (not included in repo)
│   ├── chat/               # Live stream chat data
│   └── football/           # Football-specific datasets
│
├── scripts/                # Analysis scripts
│   ├── analyze_topics_bertopic_football_only.py     # BERTopic topic extraction
│   ├── analyze_temporal_patterns_football_only.py   # Temporal burst detection
│   ├── analyze_translation_impact.py                # Translation analysis
│   └── event_comparison.py                          # Event comparison
│
├── output/                 # Analysis results
│   ├── bertopic_analysis/  # BERTopic results (263 topics)
│   │   ├── topic_details.csv
│   │   ├── country_topic_distribution.csv
│   │   └── *.png           # Visualizations
│   │
│   └── temporal_analysis/  # Temporal pattern results
│       ├── burst_details.csv
│       ├── emotion_timeline.csv
│       └── *.png           # Visualizations
│
├── docs/                   # Documentation
│   └── INTEGRATED_ANALYSIS_REPORT.md  # Comprehensive analysis report
│
├── utils/                  # Utility modules
│   ├── noise_filter.py
│   └── translation_bridge.py
│
├── tests/                  # Unit tests
│   └── test_translation_bridge.py
│
├── archived/               # Archived experimental scripts
└── legacy/                 # Legacy code (for reference only)
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- 8GB+ RAM (for BERTopic analysis)
- GPU optional (speeds up embedding generation)

### Installation

```bash
# Clone the repository
git clone https://github.com/takakuwa-mamada/watching_style_analysis.git
cd watching_style_analysis

# Install dependencies
pip install -r requirements.txt
```

### Running Analysis

#### 1. BERTopic Analysis (Topic Extraction)

```bash
python scripts/analyze_topics_bertopic_football_only.py
```

**Output**: 
- `output/bertopic_analysis/topic_details.csv` - 263 topics with keywords
- `output/bertopic_analysis/country_topic_distribution.csv` - Country×Topic matrix
- Visualizations (.png files)

**Expected Runtime**: ~15 minutes (CPU), ~5 minutes (GPU)

#### 2. Temporal Pattern Analysis

```bash
python scripts/analyze_temporal_patterns_football_only.py
```

**Output**:
- `output/temporal_analysis/burst_details.csv` - 4 major engagement bursts
- `output/temporal_analysis/emotion_timeline.csv` - Emotion markers over time
- Visualizations (.png files)

**Expected Runtime**: ~2-3 minutes

## 📈 Key Results

### Topic Analysis (BERTopic)

- **263 topics extracted** from multilingual comments
- **74.9% coverage** (31,892/42,556 comments)
- **Top 5 topics** account for 32.8% of all comments

**Topic Distribution by Country:**

| Topic Category | Top Country | % | Example Keywords |
|----------------|-------------|---|------------------|
| Social/Casual | Japan | 32.95% | "こんばんは" (Good evening), greetings |
| Team Chants | Spain | 18.28% | "HALA MADRID", "Visca Barça" |
| Emoji Reactions | France | 10.99% | 😜, 💖, 🔥 |
| Penalty Debates | UK | 3.73% | "clear pen", "offside", "robbed" |
| Player Analysis | UK | 3.69% | "Lamine", "age 17", "too young" |

### Temporal Analysis

**4 Major Engagement Bursts Detected:**

| Burst | Time | Peak Height | Sample Comments | Interpretation |
|-------|------|-------------|-----------------|----------------|
| #1 | 19% (~80min) | 1,158 | "HALA MADRID", "vamos" | Goal/Major event |
| #2 | 24% (~101min) | 1,282 | "😜💖", "madrid push hard" | Emotional reactions |
| #3 | 28% (~118min) | 1,257 | "Barcelona 💩", "HALA MADRID" | Team criticism |
| **#4** | **31% (~131min)** | **1,363** ⭐ | "vuhuuuu", "🤍🔥🔥" | **Match end/Victory** |

### Cultural Temporal Patterns

| Country | Pattern Type | Peak Phase | Characteristic |
|---------|--------------|------------|----------------|
| **France** | Early-Spike | 0-9% | Intense early, then dropout |
| **Japan** | Sustained | 10-19% | Most consistent engagement |
| **Spain** | First-Half | 0-9% | Strong play focus, halftime drop |
| **UK** | Gradual-Build | 4-9% | Analytical attention throughout |

## 🛠️ Technologies Used

### Core Libraries

- **BERTopic** (v0.16+) - Topic modeling
- **sentence-transformers** - Multilingual embeddings
  - Model: `paraphrase-multilingual-MiniLM-L12-v2`
- **UMAP** - Dimensionality reduction (384→5 dimensions)
- **HDBSCAN** - Clustering (min_cluster_size=30)
- **pandas**, **numpy** - Data processing
- **matplotlib**, **seaborn** - Visualization
- **scipy** - Statistical analysis

### Analysis Pipeline

```
Raw Comments (42,556)
    ↓
Preprocessing & Filtering
    ↓
Embedding Generation (sentence-transformers)
    ↓
Dimensionality Reduction (UMAP: 384→5 dims)
    ↓
Clustering (HDBSCAN)
    ↓
Topic Representation (c-TF-IDF)
    ↓
BERTopic Topics (263 topics)
    +
Temporal Analysis (Burst Detection, Emotion Timeline)
    ↓
Cultural Pattern Analysis
```

## 📊 Dataset Description

**Source**: El Clásico Live Stream Comments  
**Event**: Real Madrid vs. FC Barcelona  
**Total Comments**: 42,556  
**Languages**: Spanish, English, Japanese, Hindi/Urdu, French

**Country Distribution:**
- **Spain**: 9,715 comments (2 streams)
- **Japan**: 9,276 comments (2 streams)
- **UK**: 19,651 comments (4 streams)
- **France**: 3,914 comments (1 stream)

**Time Range**: ~7 hours of recording time

**Data Format** (CSV):
```csv
timestamp,comment,country,stream_id
2024-10-26 21:00:05,HALA MADRID,Spain,Spain_1
2024-10-26 21:00:12,こんばんは,Japan,Japan_1
2024-10-26 21:00:18,Clear pen!,UK,UK_1
...
```

> **Note**: Raw data is not included in this repository due to privacy considerations and platform terms of service. For research collaboration or data access requests, please contact the authors.

## 📖 Documentation

### Main Documentation

- **[Integrated Analysis Report](docs/INTEGRATED_ANALYSIS_REPORT.md)** 
  - Comprehensive findings (6,500+ words)
  - Detailed topic interpretations
  - Temporal pattern analysis
  - Academic implications
  - Statistical summaries

### Key Sections

1. **Part 1**: Topic-Based Cultural Analysis
   - 4 distinct cultural styles
   - Top 20 topic interpretations
   - Country-specific patterns

2. **Part 2**: Temporal Pattern Analysis
   - 4 major engagement bursts
   - Emotion timeline patterns
   - Country temporal heatmaps

3. **Part 3**: Integrated Cultural-Temporal Findings
   - Style-timing correlations
   - Cultural convergence during peaks

4. **Part 4**: Research Plan Fulfillment
   - All requirements achieved (100%)
   - Multi-lingual topic extraction validated

5. **Part 5**: Academic Implications
   - Theoretical contributions
   - Methodological innovations
   - Citation opportunities

## 🔬 Academic Context

### Theoretical Contributions

1. **Cultural Technology Adoption Theory**
   - Cultural values shape digital behavior more than platform affordances
   - Same technology → Different usage patterns

2. **Sports Fan Identity Theory**
   - Stadium culture transfers online (Spain's chanting)
   - New digital-native styles emerge (Japan's social, France's emoji)

3. **Temporal Engagement Theory**
   - Cultural attention patterns differ (patient vs. impulsive)
   - Platform design should accommodate diverse temporal styles

### Methodological Contributions

1. **Multilingual Topic Modeling**
   - Successfully applied sentence-transformers to code-switching environment
   - 263 topics capture granular semantic differences across 5 languages

2. **Integrated Temporal-Topic Analysis**
   - Combined BERTopic (content) + Burst Detection (timing) + Emotion Timeline (sentiment)
   - Provides holistic view of cultural engagement

## 🧪 Testing

```bash
# Run unit tests
python -m pytest tests/

# Run specific test
python -m pytest tests/test_translation_bridge.py -v
```

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 code style
- Add docstrings to all functions
- Include type hints where applicable
- Write unit tests for new features
- Update documentation for API changes

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Authors

- **Takakuwa Mamada** - *Initial work* - [takakuwa-mamada](https://github.com/takakuwa-mamada)

## 🙏 Acknowledgments

- YouTube live stream hosts for providing public comment data
- Helsinki-NLP for OPUS-MT translation models
- BERTopic community for the excellent topic modeling framework
- sentence-transformers team for multilingual embedding models

## 📧 Contact

For questions, collaboration inquiries, or data access requests:

- **GitHub Issues**: [Create an issue](https://github.com/takakuwa-mamada/watching_style_analysis/issues)
- **GitHub**: [@takakuwa-mamada](https://github.com/takakuwa-mamada)
- **Email**: [Contact via GitHub profile]

## 📚 Citation

If you use this work in your research, please cite:

```bibtex
@misc{mamada2024crosscultural,
  author = {Mamada, Takakuwa},
  title = {Cross-Cultural Sports Fan Engagement Analysis on SNS: 
           A BERTopic-Based Study of El Clásico Live Stream Comments},
  year = {2024},
  publisher = {GitHub},
  journal = {GitHub repository},
  howpublished = {\url{https://github.com/takakuwa-mamada/watching_style_analysis}},
  note = {Research in Progress}
}
```

## 🔮 Future Work

### Immediate Plans
- [ ] Statistical significance testing (Chi-square, ANOVA)
- [ ] Paper writing (Results Sections 4.4-4.5)
- [ ] Conference submission preparation

### Long-term Extensions
- [ ] Expand to other sports (MLB, NBA, NFL)
- [ ] Real-time burst detection system
- [ ] Deeper sentiment analysis (sarcasm, irony detection)
- [ ] Network analysis of user interactions
- [ ] Comparison with offline stadium engagement patterns
- [ ] Streamer influence analysis

## ⚠️ Limitations & Considerations

### Data Limitations
1. **Single Match**: Analysis based on one El Clásico match (high-stakes rivalry)
2. **Stream Confound**: Each stream represents one country (can't separate country from streamer effects)
3. **Language Proxy**: Assumes stream language approximates viewer nationality
4. **Temporal Alignment**: Exact match event timestamps not available

### Methodological Limitations
1. **Topic Granularity**: 263 topics may be overly fine-grained (many <50 comments)
2. **Outlier Rate**: 25.1% of comments classified as outliers by HDBSCAN
3. **Code-Switching**: Mixed-language topics (e.g., Topic 0) challenge interpretation

### Generalizability
- Results specific to:
  - Football (soccer) context
  - High-stakes rivalry matches
  - 2020-2023 time period
  - YouTube/Twitch platform norms

## 📊 Repository Statistics

- **Total Comments Analyzed**: 42,556
- **Topics Extracted**: 263
- **Countries**: 4
- **Streams**: 9
- **Languages**: 5 (Spanish, English, Japanese, Hindi/Urdu, French)
- **Code Files**: 15+ analysis scripts
- **Output Visualizations**: 13 figures (8 temporal + 5 topic)
- **Documentation**: 6,500+ words

---

**Last Updated**: November 23, 2025  
**Project Status**: ✅ Analysis Complete | 📝 Paper in Progress  
**Submission Target**: January 20, 2026

---

<p align="center">
  <i>This research demonstrates that cultural values fundamentally shape how people engage with the same digital platform, providing empirical evidence for culture-specific design considerations in global live streaming services.</i>
</p>
