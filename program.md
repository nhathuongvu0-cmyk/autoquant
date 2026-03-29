# autoquant

量化策略自動優化器 — 借鑑 Karpathy's autoresearch 理念，專為交易策略設計。

## 核心理念

讓 AI agent 自主探索策略空間，overnight 跑 100+ 回測實驗，找到最優因子組合。

## 文件結構

```
backtest.py   — 固定回測引擎，不能改
strategy.py   — AI 修改這個文件（因子、參數、入場/出場規則）
evaluate.py   — 計算指標（PF, Sharpe, MaxDD, POB, DSR）
data/         — BTC/ETH 歷史數據
results.tsv   — 實驗記錄
```

## Setup

開始新實驗前：

1. **同意一個 tag**：例如 `mar29`
2. **創建分支**：`git checkout -b autoquant/<tag>`
3. **讀取文件**：理解 strategy.py 當前狀態
4. **確認數據存在**：`data/btc_4h.csv` 和 `data/eth_4h.csv`
5. **跑 baseline**：`python backtest.py` 建立基準
6. **開始實驗**

## 實驗循環

LOOP FOREVER:

1. **想一個改進點**：新因子、參數調整、入場條件、出場規則
2. **修改 strategy.py**
3. **git commit**：`git add strategy.py && git commit -m "experiment: <description>"`
4. **跑回測**：`python backtest.py > run.log 2>&1`
5. **讀取結果**：`grep "^RESULT:" run.log`
6. **記錄到 results.tsv**
7. **判斷**：
   - 如果 DSR 提升 → `git commit --amend` 保留
   - 如果 DSR 下降 → `git reset --hard` 丟棄
8. **重複**

## 評估指標

| 指標 | 說明 | 目標 |
|------|------|------|
| **PF** | Profit Factor（毛利/毛損） | > 1.5 |
| **Sharpe** | 年化收益/年化波動 | > 1.0 |
| **MaxDD** | 最大回撤 | < 10% |
| **POB** | Probability of Breakeven（獲利交易比例） | > 45% |
| **DSR** | Deflated Sharpe Ratio（考慮過擬合） | **主要指標** |

## DSR (Deflated Sharpe Ratio)

DSR 是 Marcos López de Prado 提出的，解決多重測試過擬合問題：

```
DSR = Sharpe × √(1 - skewness × Sharpe / 3 + (kurtosis - 3) × Sharpe² / 24)
     × (1 - (N_trials - 1) / (2 × N_observations))
```

**為什麼用 DSR？**
- 傳統 Sharpe 容易被「挑參數」刷高
- DSR 會懲罰過多實驗次數
- DSR 高 = 真正穩定的策略

## 可修改範圍（strategy.py）

**可以改：**
- 入場因子（RSI, MACD, BB, OBV, ADX...）
- 出場規則（TP/SL 比例、trailing stop）
- 持倉時間、冷卻期
- 因子權重、閾值
- 倉位管理

**不能改：**
- 回測引擎 (backtest.py)
- 評估函數 (evaluate.py)
- 數據文件 (data/)
- 手續費設定（固定 0.1%）

## 實驗規則

1. **時間預算**：每次回測 < 2 分鐘（數據量小）
2. **簡潔優先**：同等效果，代碼越少越好
3. **防過擬合**：用 2018-2023 訓練，2024-2026 驗證
4. **不要停**：用戶可能在睡覺，自己跑到被打斷

## 記錄格式 (results.tsv)

```
commit	pf	sharpe	maxdd	pob	dsr	status	description
383abb4	1.85	1.23	0.08	0.52	0.95	keep	baseline MR strategy
909dd59	1.92	1.31	0.07	0.54	1.02	keep	add RSI filter
4161af3	1.78	1.18	0.09	0.48	0.88	discard	OBV divergence (worse)
```

## 開始

準備好後，說：「開始 autoquant 實驗」

我會自主迭代，直到你打斷我。
