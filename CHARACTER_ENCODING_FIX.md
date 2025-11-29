# 文字化け問題の解決方法

## 問題の原因

Windows PowerShellでPythonスクリプトを実行した際、日本語出力が文字化けする問題が発生しました。

```
邵ｦ譁ｭ逧�豈碑ｼ�蛻�譫� → 縦断的比較分析
```

これは、PowerShellのデフォルトコンソール出力エンコーディングが **Shift-JIS (CP932)** であり、PythonのUTF-8出力と不一致だったためです。

## 解決方法

### 方法1: Pythonスクリプト内で出力エンコーディングを設定

各スクリプトの冒頭に以下を追加：

```python
import sys
import io

# Windows PowerShellの文字化け対策
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
```

**メリット**:
- スクリプト側で完結
- 他の環境でも動作

**適用済みスクリプト**:
- ✅ `analyze_language_refined.py`
- ✅ `analyze_longitudinal_real_madrid.py`
- ✅ `analyze_streamer_effects.py`

### 方法2: PowerShellのコードページをUTF-8に変更

ターミナルで実行前に：

```powershell
chcp 65001
```

または、環境変数を設定：

```powershell
$env:PYTHONIOENCODING='utf-8'
```

**メリット**:
- システムレベルで解決
- 全てのPythonスクリプトに適用

**デメリット**:
- 毎回設定が必要（または.profileに追加）

### 方法3: VSCodeの統合ターミナル設定

`settings.json`に追加：

```json
{
  "terminal.integrated.env.windows": {
    "PYTHONIOENCODING": "utf-8"
  }
}
```

## 実装状況

### 現在の実行コマンド

```powershell
$env:PYTHONIOENCODING='utf-8'; conda run -n base python scripts\analyze_language_refined.py
```

これにより：
1. 環境変数で UTF-8 を指定
2. スクリプト内でも UTF-8 出力を設定
3. 二重の対策で確実に文字化けを防止

## 文字化けの例と修正後

### Before (文字化け)

```
================================================================================
邵ｦ譁ｭ逧�豈碑ｼ�蛻�譫� - 繝ｬ繧｢繝ｫ繝槭ラ繝ｪ繝ｼ繝�3隧ｦ蜷�
Longitudinal Comparison Analysis - Real Madrid 3 Matches
================================================================================

噫 蛻�譫宣幕蟋�

唐 Real_Madrid_vs_Barcelona
   蟇ｾ謌ｦ逶ｸ謇�: Barcelona
   驥崎ｦ∝ｺｦ: Tier 1 (Ultra-High)
   譁�閼�: El Clasico - 譛鬮伜ｳｰ縺ｮ荳謌ｦ
```

### After (修正後)

```
================================================================================
縦断的比較分析 - レアルマドリード3試合
Longitudinal Comparison Analysis - Real Madrid 3 Matches
================================================================================

🚀 分析開始

📂 Real_Madrid_vs_Barcelona
   対戦相手: Barcelona
   重要度: Tier 1 (Ultra-High)
   文脈: El Clasico - 最高峰の一戦
```

## トラブルシューティング

### 1. まだ文字化けする場合

PowerShellを再起動して、以下を実行：

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

### 2. 絵文字が表示されない場合

Windows Terminalの使用を推奨：

```powershell
# Windows Terminal で開く
wt
```

### 3. conda環境での問題

conda環境のPython自体のエンコーディング設定：

```powershell
conda activate base
python -c "import sys; print(sys.stdout.encoding)"
# 出力: utf-8 であるべき
```

## 今後の対策

### 恒久的な設定

PowerShellのプロファイルに追加（`$PROFILE`）：

```powershell
# UTF-8 設定
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
```

設定後、プロファイルを再読み込み：

```powershell
. $PROFILE
```

## 参考情報

- **PowerShellのデフォルトエンコーディング**: Shift-JIS (CP932)
- **Pythonのデフォルトエンコーディング**: UTF-8
- **Code Page 65001**: UTF-8のWindows識別子
- **推奨ターミナル**: Windows Terminal (UTF-8ネイティブサポート)

---

**作成日時**: 2025年11月23日 22:15  
**ステータス**: 対策完了 ✓
