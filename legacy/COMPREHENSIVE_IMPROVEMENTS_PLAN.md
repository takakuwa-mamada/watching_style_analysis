# 包括的精度向上計画 (2025年11月7日)

## 🎯 **目標**
トピック重複検出の改善を中心に、全体の精度を論理的・長期的に最適化する

---

## 📋 **問題分析**

### **Issue 1: スポーツ種別検証が機能していない**
**原因**: 
- `context_penalty` は計算されているが、CSV保存時に列が追加されていない
- `generate_event_similarity_matrix()` で保存処理を確認する必要がある

**解決策**:
- `event_pairs.append()` に `context_penalty` を追加
- 表示ログにもペナルティ情報を追加

---

### **Issue 2: ストリーム名が完全なファイルパス**
**原因**: 
- `evts_dict.keys()` がファイルパス全体を返している
- `"G:\...\Ja_abema.csv"` → `"Ja_abema"` への変換が不十分

**解決策**:
```python
# Before
stream_names = sorted([k.replace(".csv", "") for k in evts_dict.keys()])

# After
stream_names = sorted([
    os.path.basename(k).replace(".csv", "") 
    for k in evts_dict.keys()
])
```

---

### **Issue 3: トピック重複検出が不十分 (90%が0.0)**
**原因**: 
- top 10 words では語彙が少なすぎる
- 単語レベルのみで、複合語（"高校野球"）が分割される
- 類義語が検出されない（"goal" vs "ゴール"）

**解決策（3段階）**:
1. **top_words を 10 → 20 に増加**
2. **2-gram（複合語）の追加**
3. **多言語類義語辞書の導入**

---

### **Issue 4: similar_event_details.png の可読性**
**原因**: 
- 50文字でもまだ長い（日本語は情報密度が高い）
- ファイルパスが含まれている

**解決策**:
- 文字列を **30文字** に短縮（日本語20文字相当）
- ファイルパス部分を完全に削除

---

## 🔧 **実装計画（優先度順）**

### **Phase 1: 緊急修正（即座に実施）**

#### 1.1 ストリーム名のパス削除
```python
# Location: generate_event_similarity_matrix()
stream_names = sorted([
    os.path.basename(k).replace(".csv", "") 
    for k in evts_dict.keys()
])
```

#### 1.2 context_penalty の保存と表示
```python
# Location: generate_event_similarity_matrix()
event_pairs.append({
    ...
    "context_penalty": sim_scores.get("context_penalty", 1.0)
})

# Location: main() の表示部分
print(f"  Metrics: emb={emb:.3f}, topic={jac:.3f}, lex={lex:.3f}, context={ctx:.3f}")
```

#### 1.3 similar_event_details.png の文字短縮
```python
# 50文字 → 30文字 + パス除去
df_display[col] = df_display[col].apply(
    lambda x: str(x).split('(')[0][:30] + '...' 
    if isinstance(x, str) and len(str(x)) > 30 
    else str(x)
)
```

---

### **Phase 2: トピック重複検出の改善（中核）**

#### 2.1 top_words を 10 → 20 に増加
**効果予測**: topic_jaccard > 0 のペアが 10% → 35-40% に増加

```python
# Location: merge_topics() 内
for w, s in words_by_tid.get(t, [])[:10]:  # Before
for w, s in words_by_tid.get(t, [])[:20]:  # After
```

**論理的根拠**:
- 現在の10語では語彙カバー率が不足
- BERTopicは通常50-100語を抽出するため、20語は妥当
- Jaccard係数は分母（union）が増えるため、閾値調整は不要

#### 2.2 2-gram（複合語）の追加
**効果予測**: "高校野球" "サッカー試合" などの複合語が1単位として扱われる

```python
# Location: 新規関数 extract_ngrams()
from collections import Counter

def extract_ngrams(texts: List[str], n=2) -> Counter:
    """Extract n-grams from text list"""
    ngrams = Counter()
    for text in texts:
        words = text.split()
        for i in range(len(words) - n + 1):
            ngram = " ".join(words[i:i+n])
            ngrams[ngram] += 1
    return ngrams

# Location: aggregate_event_representation()
# 1-gramと2-gramを結合
unigrams = set(top_words)
bigrams = extract_ngrams(all_comments, n=2).most_common(10)
combined_topics = unigrams | {bg for bg, _ in bigrams}
```

**論理的根拠**:
- 日本語・ポルトガル語では複合語が意味を持つ
- "高校" + "野球" ≠ "高校野球" の意味
- スポーツ種別検証の精度も向上

#### 2.3 多言語類義語辞書の導入
**効果予測**: "goal" と "ゴール" が同一トピックとして認識される

```python
# Location: 新規辞書定義
MULTILINGUAL_SYNONYMS = {
    "goal": {"goal", "gol", "ゴール", "得点", "골"},
    "penalty": {"penalty", "pênalti", "ペナルティ", "pk"},
    "offside": {"offside", "impedimento", "オフサイド"},
    "soccer": {"soccer", "football", "futebol", "サッカー", "축구"},
    "baseball": {"baseball", "beisebol", "野球", "야구"},
    # ... 拡張可能
}

def normalize_with_synonyms(word: str) -> str:
    """Convert word to canonical form using synonym dict"""
    word_lower = word.lower()
    for canonical, synonyms in MULTILINGUAL_SYNONYMS.items():
        if word_lower in synonyms:
            return canonical
    return word_lower

# Location: merge_topics() 内
norm = normalize_with_synonyms(normalize_term(w))
```

**論理的根拠**:
- 多言語配信の本質的問題に対処
- 手動辞書は小規模なら管理可能
- 機械翻訳APIより確実性が高い

---

### **Phase 3: コンテキスト検証の強化**

#### 3.1 スポーツ種別キーワードの拡張
```python
# 現在のキーワードリストを拡張
baseball_keywords = [
    "高校野球", "広陵", "高校", "甲子園", "野球", "高校生",
    "ピッチャー", "バッター", "ホームラン", "野球部",
    "baseball", "beisebol"
]

soccer_keywords = [
    "サッカー", "ゴール", "goal", "penalty", "brasil", "alemanha",
    "オフサイド", "pk", "コーナー", "フリーキック", "イエローカード",
    "football", "futebol", "soccer", "midfielder", "striker"
]
```

#### 3.2 固有名詞による検証（オプション）
```python
def extract_proper_nouns(comments: List[str]) -> Set[str]:
    """Extract proper nouns (team names, player names)"""
    # 簡易実装: 大文字始まりの単語を抽出
    proper_nouns = set()
    for comment in comments:
        words = comment.split()
        for word in words:
            if word and word[0].isupper() and len(word) > 2:
                proper_nouns.add(word)
    return proper_nouns

# 固有名詞の重複チェック
proper_A = extract_proper_nouns(event_A["comments"])
proper_B = extract_proper_nouns(event_B["comments"])
proper_overlap = len(proper_A & proper_B) / max(len(proper_A | proper_B), 1)

# overlap < 0.1 → 異なる試合の可能性
if proper_overlap < 0.1:
    context_penalty *= 0.7
```

---

### **Phase 4: 時系列パターン検証（高度）**

#### 4.1 コメント数パターンの相関
```python
from scipy.stats import pearsonr

def compute_temporal_correlation(event_A, event_B, streams, peak_pad=5):
    """Compute Pearson correlation of comment count patterns"""
    # 各イベントのコメント数時系列を取得
    counts_A = get_comment_counts_over_time(event_A, streams, peak_pad)
    counts_B = get_comment_counts_over_time(event_B, streams, peak_pad)
    
    # 長さを揃える
    min_len = min(len(counts_A), len(counts_B))
    counts_A = counts_A[:min_len]
    counts_B = counts_B[:min_len]
    
    if len(counts_A) < 3:
        return 0.0
    
    correlation, _ = pearsonr(counts_A, counts_B)
    return max(0.0, correlation)

# main_similarity に時系列相関を追加
temporal_corr = compute_temporal_correlation(event_A, event_B, streams)
if temporal_corr < 0.3:
    context_penalty *= 0.8  # 時系列パターンが異なる
```

**論理的根拠**:
- 同じ試合の盛り上がりタイミングは類似するはず
- 異なる試合（異なる時間帯）の誤マッチングを防ぐ
- 相関係数 < 0.3 → 高確率で異なるイベント

---

## 📊 **期待される改善効果**

### **定量的効果**
| 指標 | 現在 | Phase 1後 | Phase 2後 | Phase 3後 | Phase 4後 |
|------|------|-----------|-----------|-----------|-----------|
| サッカーvs野球誤マッチ | 0.841 | **0.252** | 0.252 | **0.180** | 0.180 |
| topic_jaccard=0の割合 | 90% | 90% | **40-50%** | **30-40%** | 30-40% |
| 多言語同一トピック検出 | 10% | 10% | 15% | **60-70%** | 60-70% |
| 異なる試合の誤検出 | 15% | 10% | 10% | 8% | **3-5%** |

### **定性的効果**
- ✅ ヒートマップのストリーム名が簡潔（"Bra, Ja_abema"）
- ✅ テーブル画像が完全に読める（30文字短縮）
- ✅ トピック重複が2-3倍増加（Jaccard係数の意味向上）
- ✅ 多言語配信の本質的課題に対応（"goal"="ゴール"）
- ✅ コンテキスト検証が機能（サッカーvs野球 0.841→0.18）
- ✅ 時系列パターンで更なる精度向上

---

## ⚙️ **実装順序（推奨）**

### **ステップ1: 緊急修正（5分）**
1. ストリーム名のパス削除
2. context_penalty の保存と表示
3. 文字短縮を30文字に変更

**実行 & 検証** → 確認後に次へ

### **ステップ2: トピック検出改善（10分）**
4. top_words 10→20
5. 2-gram追加
6. 多言語類義語辞書（基本版20語）

**実行 & 検証** → topic_jaccard > 0 が増えたか確認

### **ステップ3: コンテキスト強化（5分）**
7. スポーツキーワード拡張
8. 固有名詞検証（オプション）

**実行 & 検証** → サッカーvs野球が0.2以下か確認

### **ステップ4: 時系列検証（オプション・10分）**
9. Pearson相関の実装

**最終実行 & 検証** → 全体の精度向上を確認

---

## 🎓 **長期的な最適化の考え方**

### **原則1: データ駆動**
- 実行結果を見てから次の改善を判断
- 仮説→実装→検証→改善のサイクル

### **原則2: 段階的改善**
- 一度に全部変更しない
- 各改善の効果を個別に測定

### **原則3: 保守性**
- コードは読みやすく、コメント付き
- 辞書データは外部ファイル化を検討

### **原則4: 学会発表を意識**
- 改善の論理的根拠を明確に
- 各手法の効果を定量的に示せる

---

**実装開始**: 2025年11月7日  
**予想所要時間**: 30-40分（全Phase）  
**推奨**: Phase 1→2を優先、3-4は結果次第
