"""
evaluate.py — 量化策略評估指標
固定文件，不可修改
"""

import numpy as np
from scipy import stats
from typing import List, Dict, Tuple

def calculate_metrics(trades: List[Dict], equity_curve: np.ndarray, n_trials: int = 1) -> Dict:
    """
    計算所有評估指標
    
    Args:
        trades: 交易列表 [{'pnl': float, 'return': float, 'duration': int}, ...]
        equity_curve: 權益曲線 (daily/4h returns)
        n_trials: 實驗次數（用於 DSR 計算）
    
    Returns:
        Dict with PF, Sharpe, MaxDD, POB, DSR
    """
    if len(trades) == 0:
        return {
            'pf': 0.0,
            'sharpe': 0.0,
            'maxdd': 1.0,
            'pob': 0.0,
            'dsr': -999.0,
            'n_trades': 0,
            'total_return': 0.0
        }
    
    # 提取 PnL
    pnls = np.array([t['pnl'] for t in trades])
    returns = np.array([t['return'] for t in trades])
    
    # Profit Factor
    gross_profit = np.sum(pnls[pnls > 0])
    gross_loss = abs(np.sum(pnls[pnls < 0]))
    pf = gross_profit / gross_loss if gross_loss > 0 else 999.0
    
    # POB (Probability of Breakeven / Win Rate)
    pob = np.sum(pnls > 0) / len(pnls)
    
    # Sharpe Ratio (trade-level，年化)
    # 使用交易收益計算，更準確
    trade_returns = np.array([t['return'] for t in trades])
    if len(trade_returns) < 2:
        sharpe = 0.0
    else:
        # 估算年化交易次數
        trades_per_year = len(trades) / (len(equity_curve) / 2190) if len(equity_curve) > 0 else 100
        mean_trade_return = np.mean(trade_returns)
        std_trade_return = np.std(trade_returns)
        # 年化 Sharpe = mean * sqrt(N) / std
        sharpe = (mean_trade_return * np.sqrt(trades_per_year)) / std_trade_return if std_trade_return > 0 else 0.0
    
    # Max Drawdown
    cumulative = np.cumprod(1 + equity_curve)
    running_max = np.maximum.accumulate(cumulative)
    drawdown = (running_max - cumulative) / running_max
    maxdd = np.max(drawdown)
    
    # DSR (Deflated Sharpe Ratio)
    dsr = calculate_dsr(returns, sharpe, n_trials)
    
    # Total Return
    total_return = np.prod(1 + returns) - 1
    
    return {
        'pf': round(pf, 2),
        'sharpe': round(sharpe, 2),
        'maxdd': round(maxdd, 4),
        'pob': round(pob, 4),
        'dsr': round(dsr, 4),
        'n_trades': len(trades),
        'total_return': round(total_return, 4)
    }


def calculate_dsr(returns: np.ndarray, sharpe: float, n_trials: int) -> float:
    """
    計算 Deflated Sharpe Ratio
    
    基於 Marcos López de Prado 的論文：
    "The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality"
    
    DSR 懲罰：
    1. 非正態分布（偏度、峰度）
    2. 多重測試（實驗次數越多，懲罰越大）
    """
    if len(returns) < 10 or sharpe <= 0:
        return -999.0
    
    n = len(returns)
    
    # 偏度和峰度
    skewness = stats.skew(returns)
    kurtosis = stats.kurtosis(returns)  # excess kurtosis
    
    # Sharpe Ratio 的標準誤差
    se_sharpe = np.sqrt((1 + 0.5 * sharpe**2 - skewness * sharpe + (kurtosis / 4) * sharpe**2) / n)
    
    # 多重測試校正 (Bonferroni-like)
    # E[max(SR)] ≈ (1 - γ) × Φ^(-1)(1 - 1/N) where γ ≈ 0.5772
    if n_trials > 1:
        gamma = 0.5772  # Euler-Mascheroni constant
        expected_max_sr = (1 - gamma) * stats.norm.ppf(1 - 1 / n_trials)  # 修復：不乘 se_sharpe
    else:
        expected_max_sr = 0
    
    # Deflated Sharpe Ratio
    # DSR = (SR - E[max(SR)]) / se(SR)
    dsr = (sharpe - expected_max_sr) / se_sharpe if se_sharpe > 0 else 0
    
    # 轉換為類似 Sharpe 的尺度（可選）
    # 這裡直接返回 DSR 的 p-value 概念
    # 正值 = 策略顯著優於隨機
    
    return dsr


def calculate_sortino(returns: np.ndarray, target: float = 0) -> float:
    """
    計算 Sortino Ratio（只考慮下行風險）
    """
    excess_returns = returns - target
    downside_returns = returns[returns < target]
    
    if len(downside_returns) == 0:
        return 999.0
    
    downside_std = np.std(downside_returns)
    periods_per_year = 2190
    
    sortino = (np.mean(excess_returns) * periods_per_year) / (downside_std * np.sqrt(periods_per_year))
    return sortino


def calculate_calmar(total_return: float, maxdd: float, years: float) -> float:
    """
    計算 Calmar Ratio（年化收益 / 最大回撤）
    """
    if maxdd == 0 or years == 0:
        return 0.0
    
    annual_return = (1 + total_return) ** (1 / years) - 1
    calmar = annual_return / maxdd
    return calmar


def format_results(metrics: Dict) -> str:
    """
    格式化輸出結果，供 grep 解析
    """
    return f"""
---
RESULT:pf={metrics['pf']}
RESULT:sharpe={metrics['sharpe']}
RESULT:maxdd={metrics['maxdd']}
RESULT:pob={metrics['pob']}
RESULT:dsr={metrics['dsr']}
RESULT:n_trades={metrics['n_trades']}
RESULT:total_return={metrics['total_return']}
---
"""


if __name__ == "__main__":
    # 測試
    np.random.seed(42)
    test_returns = np.random.normal(0.001, 0.02, 500)
    test_trades = [{'pnl': r * 1000, 'return': r, 'duration': 4} for r in test_returns]
    
    metrics = calculate_metrics(test_trades, test_returns, n_trials=1)
    print(format_results(metrics))
