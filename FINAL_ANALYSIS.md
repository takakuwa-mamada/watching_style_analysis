# 最終分析結果 (2025年11月7日)

## 🔍 **Context Penalty の動作状況**

### ✅ **成功事例（11ペアで0.3適用）**
```
Event 55 vs 77: 0.193 (context=0.3) ← 70%削減成功
Event 74 vs 77: 0.172 (context=0.3) ← 70%削減成功
Event 33 vs 77: 0.096 (context=0.3) ← 70%削減成功
...11ペア全てで適用
```

### ❌ **失敗事例（10ペアで1.0のまま）**
```
Event 54 vs 77: 0.841 (context=1.0) ← ペナルティ未適用！
Event 58 vs 77: 0.724 (context=1.0) ← ペナルティ未適用！
...10ペア
```

---

## 🎯 **根本原因の仮説**

### **仮説1: Event 54/58/59 は両方のスポーツキーワードを含む**
```python
is_baseball_A = True  # comments に "野球" "甲子園" などが含まれる
is_soccer_A = True    # comments に "サッカー" "ゴール" などが含まれる
is_baseball_B = True  # Event 77 は完全に野球
is_soccer_B = False

# この場合
if (is_baseball_A and is_soccer_B) or (is_soccer_A and is_baseball_B):
    # (True and False) or (True and True) = False or True = True
    # → ペナルティ適用される...はず
```

→ **論理的にはペナルティが適用されるべき**

### **仮説2: Event 54/58 が両方 True の場合、条件式が機能していない**
```python
# 現在のコード
if (is_baseball_A and is_soccer_B) or (is_soccer_A and is_baseball_B):
    context_penalty = 0.3

# Event 54 vs 77 の場合
# A: Baseball=True, Soccer=True
# B: Baseball=True, Soccer=False

# 評価
(True and False) or (True and True) = False or True = True

# → context_penalty = 0.3 になるはず！
```

→ **ロジックは正しい**

### **仮説3: Event 54 が "純粋なサッカー" と判定されている**
```python
# デバッグ出力に "Event 54 vs 77" が出ていない
# → Event 54 vs 77 の組み合わせでは条件式が False になっている

# 可能性
# A: Baseball=False, Soccer=True  ← 純粋にサッカー
# B: Baseball=True, Soccer=False  ← 純粋に野球

# 評価
(False and False) or (True and True) = False or True = True
# → ペナルティ適用されるはず...
```

→ **これも適用されるはず**

---

## 💡 **真の原因（推定）**

### **Event 54 と Event 77 の両方が "両方のスポーツ" と判定されている**
```python
# Event 54 (サッカー)
is_baseball_A = True  # comments に "野球" が含まれる？
is_soccer_A = True    # サッカーイベント

# Event 77 (野球)
is_baseball_B = True  # 野球イベント
is_soccer_B = True   # comments に "サッカー" が含まれる？

# 評価
(True and True) or (True and True) = True or True = True
# → ペナルティ適用される...はずだが

# **条件式の問題**
# 両方が両方のスポーツを含む場合、"異なるスポーツ" とは言えない
```

---

## 🔧 **解決策**

### **Option 1: 条件式の修正（推奨）**
```python
# 現在（両方のスポーツを含む場合を考慮していない）
if (is_baseball_A and is_soccer_B) or (is_soccer_A and is_baseball_B):
    context_penalty = 0.3

# 修正案（より厳密な判定）
# 「片方が純粋に野球、もう片方が純粋にサッカー」の場合のみペナルティ
if (is_baseball_A and not is_soccer_A and is_soccer_B and not is_baseball_B) or \
   (is_soccer_A and not is_baseball_A and is_baseball_B and not is_soccer_B):
    context_penalty = 0.3
```

### **Option 2: 優勢スポーツの判定（より柔軟）**
```python
# comments 内のキーワード出現回数をカウント
baseball_count_A = sum(1 for kw in baseball_keywords if kw in full_text_A)
soccer_count_A = sum(1 for kw in soccer_keywords if kw in full_text_A)

baseball_count_B = sum(1 for kw in baseball_keywords if kw in full_text_B)
soccer_count_B = sum(1 for kw in soccer_keywords if kw in full_text_B)

# 優勢スポーツを判定（出現回数が多い方）
dominant_A = "baseball" if baseball_count_A > soccer_count_A else "soccer"
dominant_B = "baseball" if baseball_count_B > soccer_count_B else "soccer"

# 優勢スポーツが異なる場合のみペナルティ
if dominant_A != dominant_B:
    context_penalty = 0.3
```

### **Option 3: キーワードの更なる精密化**
```python
# "野球" だけでなく、より具体的なキーワードのみ使用
baseball_keywords = [
    "高校野球", "広陵", "甲子園", "野球部", "野球選手",
    "ピッチャー", "バッター", "ホームラン", "投手", "打者", "守備",
    "baseball", "beisebol", "pitcher", "homerun"
]
# "野球" 単体を削除（サッカーの文脈でも使われる）

soccer_keywords = [
    "サッカー選手", "サッカー日本代表", "ゴール", "goal", "penalty",
    "オフサイド", "pk", "コーナーキック", "フリーキック",
    "football", "futebol", "soccer", "offside", "midfielder", "striker"
]
# "サッカー" 単体を削除
```

---

## 📊 **現在の状況まとめ**

### **実装済み**
- ✅ ストリーム名の簡潔化（Ja_abema, UK など）
- ✅ 不要画像4つの削除
- ✅ テーブル文字短縮（30文字）
- ✅ top_words 10→20語に増加
- ✅ 多言語類義語辞書（25語）
- ✅ スポーツキーワード拡張
- ✅ context_penalty の基本実装

### **部分的成功**
- ⚠️ context_penalty: 11/21ペアで機能（52%成功率）
- ⚠️ Event 54 vs 77 など主要ペアで未適用

### **未解決**
- ❌ topic_jaccard 依然として 90% が 0.0
- ❌ 両方のスポーツキーワードを含むイベントの扱い

---

## 🎯 **推奨される次のアクション**

### **優先度1: Option 2 の実装（優勢スポーツ判定）**
- 理由: 両方のスポーツが言及されても、主題は判別可能
- 効果: Event 54 vs 77 が正しく検出される
- 所要時間: 10分

### **優先度2: キーワードの更なる精密化**
- "野球" → "野球選手", "野球部" など具体的に
- "サッカー" → "サッカー日本代表", "サッカー選手" など具体的に
- 所要時間: 5分

### **優先度3: topic_jaccard 改善（別タスク）**
- 2-gram の導入
- 類義語辞書のさらなる拡充
- 所要時間: 15分

---

**作成日**: 2025年11月7日
**状態**: context_penalty 部分的成功、更なる改善が必要
