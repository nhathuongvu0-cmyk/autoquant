# autoquant — 量化策略自動優化器 v2.0

> 借鑑 Karpathy's autoresearch，自主探索策略空間，**嚴格防止過擬合**。

---

## 🎯 核心功能

1. **自主策略探索** — AI 自動嘗試 100+ 因子組合
2. **嚴格三段驗證** — Train/Val/Test 分割，防止過擬合
3. **真實 DSR 計算** — 修正後的 Deflated Sharpe Ratio
4. **真實出場價格** — 使用實際 SL/TP 觸發價

---

## ⚠️ 重要改進 (v2.0)

| 問題 | v1.0 | v2.0 修復 |
|------|------|-----------|
| DSR 公式 | ❌ 虛高 | ✅ 正確 |
| Sharpe | bar-level | trade-level |
| 數據分割 | 只驗證 | Train/Val/Test |
| 出場價格 | next open | 實際觸發價 |

---

## 📊 數據分割

```
Train:  2018-01 → 2022-12  (策略開發)
Val:    2023-01 → 2024-12  (參數調整)
Test:   2025-01 → 至今     (最終驗證)
```

**規則：只有 Test 集盈利才算通過！**

---

## 🔬 過擬合檢查

每次實驗必須檢查：

```
如果 val_dsr > 2 但 test_dsr < 0 → 過擬合！
如果 val_pf > 1.3 但 test_pf < 1.0 → 過擬合！
```

**只有 Test 集表現穩定的策略才能用於實盤。**

---

## 🚀 使用方法

```
用戶: 開始 autoquant 實驗
AI: [自動進入實驗循環，會報告 Train/Val/Test 三段結果]
```

---

## 📈 評估標準

| 指標 | 要求 | 說明 |
|------|------|------|
| test_pf | > 1.2 | 測試集盈利因子 |
| test_dsr | > 1.5 | 測試集統計顯著 |
| val vs test | 差異 < 30% | 穩定性檢查 |

---

## 🏆 示例結果

```
Donchian 32/16 + RSI + ADX (v2.0 檢驗)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Train: PF=1.29, DSR=9.57 ✅
Val:   PF=1.77, DSR=6.74 ✅
Test:  PF=0.86, DSR=-999 ❌ 過擬合！

結論：此策略不適合實盤
```

---

## 📁 文件結構

```
~/.openclaw/skills/autoquant/
├── SKILL.md        ← 使用說明
├── backtest.py     ← 回測引擎 (v2.0)
├── evaluate.py     ← 評估指標 (修正DSR)
├── strategy.py     ← 策略文件
└── data/           ← 數據
```
