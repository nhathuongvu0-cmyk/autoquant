# autoquant — 量化策略自動優化器

> 借鑑 Karpathy's autoresearch 理念，讓 AI agent 自主探索策略空間，overnight 跑 100+ 回測實驗。

---

## 🎯 這個 Skill 能幹什麼？

### 核心功能

1. **自主策略探索** — AI 自動修改 strategy.py，嘗試不同因子/參數組合
2. **快速回測迭代** — 每次回測 < 2 分鐘，一小時可跑 30+ 實驗
3. **防過擬合評估** — 使用 DSR (Deflated Sharpe Ratio) 防止參數過擬合
4. **自動保留/丟棄** — 好的策略 git commit 保留，差的 git reset 丟棄
5. **完整實驗記錄** — 所有實驗記錄在 results.tsv

### 評估指標

| 指標 | 全名 | 說明 |
|------|------|------|
| **PF** | Profit Factor | 毛利/毛損，>1.3 為佳 |
| **Sharpe** | Sharpe Ratio | 風險調整收益，>1.0 為佳 |
| **MaxDD** | Max Drawdown | 最大回撤，<15% 為佳 |
| **POB** | Win Rate | 勝率，>40% 為佳 |
| **DSR** | Deflated Sharpe | 防過擬合夏普，>1.5 為佳 |

### 可探索的因子

- **趨勢**: Donchian, Keltner, EMA 交叉
- **動量**: RSI, MACD, TSMOM
- **波動率**: ATR 突破, BB 收縮
- **成交量**: OBV, 相對成交量
- **複合**: 多因子組合

---

## 🚀 如何使用

### 啟動實驗

```
用戶: 開始 autoquant 實驗
AI: [自動進入實驗循環]
```

### 指定方向

```
用戶: 用 autoquant 探索動量因子
AI: [專注測試 RSI, MACD, TSMOM 等]
```

### 停止實驗

```
用戶: 停止 autoquant
AI: [保存當前最佳，退出循環]
```

---

## 📁 文件結構

```
~/.openclaw/skills/autoquant/
├── SKILL.md        ← 使用說明
├── program.md      ← AI agent 實驗指令
├── backtest.py     ← 固定回測引擎（不改）
├── evaluate.py     ← 評估指標計算（不改）
├── strategy.py     ← AI 修改的策略文件
├── results.tsv     ← 實驗記錄
└── data/
    └── btc_4h.csv  ← BTC 4H 歷史數據
```

---

## 📊 示例結果

使用此 skill 找到的最佳策略：

```
Donchian 32/16 + RSI + ADX

驗證集結果 (2024-2026):
- PF:     1.31
- Sharpe: 4.49
- MaxDD:  5.07%
- DSR:    6.53
- Return: +14.48%
```

---

## ⚠️ 注意事項

1. **數據要求**: 需要至少 2000+ 根 K 線
2. **不是實盤**: 這是回測工具，實盤需要額外驗證
3. **防過擬合**: 始終關注 DSR，不只是 PF/Sharpe

---

## 🔗 來源

- [Karpathy's autoresearch](https://github.com/karpathy/autoresearch)
- López de Prado, "The Deflated Sharpe Ratio"
