#!/usr/bin/env python3
"""
backtest.py — 固定回測引擎
不可修改！

這個文件執行回測邏輯，調用 strategy.py 中的策略函數。
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import time
import json

from evaluate import calculate_metrics, format_results

# ============== 固定參數 ==============
FEE = 0.001  # 0.1% 單邊手續費
SLIPPAGE = 0.0005  # 0.05% 滑點
INITIAL_CAPITAL = 10000
DATA_DIR = Path(__file__).parent / "data"

# 訓練/驗證/測試分割
TRAIN_END = "2022-12-31"      # 訓練集結束
VAL_START = "2023-01-01"      # 驗證集開始
VAL_END = "2024-12-31"        # 驗證集結束
TEST_START = "2025-01-01"     # 測試集開始

# ============== 數據加載 ==============
def load_data(symbol: str = "btc") -> pd.DataFrame:
    """加載歷史數據"""
    data_file = DATA_DIR / f"{symbol}_4h.csv"
    
    if not data_file.exists():
        raise FileNotFoundError(f"數據文件不存在: {data_file}")
    
    df = pd.read_csv(data_file, parse_dates=['time'])
    df = df.sort_values('time').reset_index(drop=True)
    
    # 確保必要欄位存在
    required = ['time', 'open', 'high', 'low', 'close', 'volume']
    for col in required:
        if col not in df.columns:
            raise ValueError(f"缺少必要欄位: {col}")
    
    return df


def prepare_data(df: pd.DataFrame) -> pd.DataFrame:
    """計算基礎技術指標"""
    df = df.copy()
    
    # 基礎指標
    df['returns'] = df['close'].pct_change()
    
    # EMA
    for period in [8, 13, 21, 50, 100, 200]:
        df[f'ema{period}'] = df['close'].ewm(span=period, adjust=False).mean()
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # MACD
    ema12 = df['close'].ewm(span=12, adjust=False).mean()
    ema26 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = ema12 - ema26
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    
    # Bollinger Bands
    df['bb_mid'] = df['close'].rolling(20).mean()
    df['bb_std'] = df['close'].rolling(20).std()
    df['bb_upper'] = df['bb_mid'] + 2 * df['bb_std']
    df['bb_lower'] = df['bb_mid'] - 2 * df['bb_std']
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_mid']
    df['bb_pct'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
    
    # ATR
    high_low = df['high'] - df['low']
    high_close = abs(df['high'] - df['close'].shift())
    low_close = abs(df['low'] - df['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean()
    df['atr_pct'] = df['atr'] / df['close']
    
    # OBV
    df['obv'] = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()
    df['obv_ema'] = df['obv'].ewm(span=20, adjust=False).mean()
    
    # ADX
    df['adx'], df['di_plus'], df['di_minus'] = calculate_adx(df)
    
    return df


def calculate_adx(df: pd.DataFrame, period: int = 14) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """計算 ADX"""
    high = df['high']
    low = df['low']
    close = df['close']
    
    plus_dm = high.diff()
    minus_dm = low.diff().abs() * -1
    
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0
    minus_dm = minus_dm.abs()
    
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    
    atr = tr.rolling(period).mean()
    plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(period).mean() / atr)
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(period).mean()
    
    return adx, plus_di, minus_di


# ============== 回測引擎 ==============
def run_backtest(df: pd.DataFrame, strategy_func, params: dict = None) -> Tuple[List[Dict], np.ndarray]:
    """
    執行回測
    
    Args:
        df: 帶指標的數據
        strategy_func: 策略函數，返回信號 (1=買, -1=賣, 0=無)
        params: 策略參數
    
    Returns:
        trades: 交易列表
        equity_curve: 權益曲線
    """
    trades = []
    equity = [INITIAL_CAPITAL]
    position = 0  # 0=無, 1=多, -1=空
    entry_price = 0
    entry_idx = 0
    
    params = params or {}
    
    # 預熱期
    warmup = 200
    
    for i in range(warmup, len(df) - 1):
        row = df.iloc[i]
        next_row = df.iloc[i + 1]
        
        # 獲取信號
        signal = strategy_func(df, i, position, params)
        
        # 執行交易（用下一根 K 線的 open）
        exec_price = next_row['open'] * (1 + SLIPPAGE * np.sign(signal)) if signal != 0 else 0
        
        if position == 0 and signal != 0:
            # 開倉
            position = signal
            entry_price = exec_price * (1 + FEE)
            entry_idx = i + 1
            
        elif position != 0:
            # 檢查是否需要平倉
            close_signal = strategy_func(df, i, position, params, check_exit=True)
            
            if close_signal or signal == -position:
                # 平倉 - 使用實際觸發價格
                # 優先檢查 SL/TP 是否在當前 bar 觸發
                sl_price = getattr(strategy_func, '_sl_price', None) or params.get('_sl_price', 0)
                tp_price = getattr(strategy_func, '_tp_price', None) or params.get('_tp_price', 0)
                
                if position == 1:  # 多單
                    if row['low'] <= sl_price and sl_price > 0:
                        exit_price = sl_price * (1 - FEE)  # SL 觸發
                    elif row['high'] >= tp_price and tp_price > 0:
                        exit_price = tp_price * (1 - FEE)  # TP 觸發
                    else:
                        exit_price = next_row['open'] * (1 - FEE)  # 其他出場
                else:  # 空單
                    if row['high'] >= sl_price and sl_price > 0:
                        exit_price = sl_price * (1 + FEE)  # SL 觸發
                    elif row['low'] <= tp_price and tp_price > 0:
                        exit_price = tp_price * (1 + FEE)  # TP 觸發
                    else:
                        exit_price = next_row['open'] * (1 + FEE)  # 其他出場
                
                pnl_pct = (exit_price / entry_price - 1) * position
                pnl = equity[-1] * pnl_pct * params.get('position_size', 0.25)
                
                trades.append({
                    'entry_idx': entry_idx,
                    'exit_idx': i + 1,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'direction': position,
                    'pnl': pnl,
                    'return': pnl_pct * params.get('position_size', 0.25),
                    'duration': i + 1 - entry_idx
                })
                
                equity.append(equity[-1] + pnl)
                position = 0
                
                # 冷卻期
                # （由策略控制）
        
        # 如果沒有交易，權益不變
        if len(equity) == len(trades) + 1:
            pass  # 已添加
        elif position == 0:
            equity.append(equity[-1])
    
    # 確保 equity_curve 長度正確
    returns = np.diff(equity) / equity[:-1] if len(equity) > 1 else np.array([0])
    
    return trades, returns


# ============== 主程序 ==============
def main():
    start_time = time.time()
    
    print("=" * 50)
    print("autoquant backtest engine")
    print("=" * 50)
    
    # 加載數據
    print("\n[1/4] Loading data...")
    df_btc = load_data("btc")
    df_btc = prepare_data(df_btc)
    print(f"  BTC: {len(df_btc)} bars ({df_btc['time'].min()} to {df_btc['time'].max()})")
    
    # 分割訓練/驗證/測試
    train_df = df_btc[df_btc['time'] <= TRAIN_END].copy().reset_index(drop=True)
    val_df = df_btc[(df_btc['time'] >= VAL_START) & (df_btc['time'] <= VAL_END)].copy().reset_index(drop=True)
    test_df = df_btc[df_btc['time'] >= TEST_START].copy().reset_index(drop=True)
    print(f"  Train: {len(train_df)} | Val: {len(val_df)} | Test: {len(test_df)} bars")
    
    # 導入策略
    print("\n[2/4] Loading strategy...")
    try:
        from strategy import generate_signal, PARAMS, reset_state
        print(f"  Strategy loaded with params: {PARAMS}")
    except ImportError as e:
        print(f"  ERROR: Cannot import strategy: {e}")
        return
    
    # 訓練集回測
    print("\n[3/4] Running backtest (train)...")
    reset_state()
    train_trades, train_returns = run_backtest(train_df, generate_signal, PARAMS)
    train_metrics = calculate_metrics(train_trades, train_returns, n_trials=1)
    print(f"  Train: {train_metrics['n_trades']} trades, PF={train_metrics['pf']}, DSR={train_metrics['dsr']}")
    
    # 驗證集回測
    print("\n[4/5] Running backtest (validation)...")
    reset_state()
    val_trades, val_returns = run_backtest(val_df, generate_signal, PARAMS)
    val_metrics = calculate_metrics(val_trades, val_returns, n_trials=1)
    print(f"  Val: {val_metrics['n_trades']} trades, PF={val_metrics['pf']}, DSR={val_metrics['dsr']}")
    
    # 測試集回測
    print("\n[5/5] Running backtest (test)...")
    reset_state()
    test_trades, test_returns = run_backtest(test_df, generate_signal, PARAMS)
    test_metrics = calculate_metrics(test_trades, test_returns, n_trials=1)
    print(f"  Test: {test_metrics['n_trades']} trades, PF={test_metrics['pf']}, DSR={test_metrics['dsr']}")
    
    # 輸出結果
    elapsed = time.time() - start_time
    print("\n" + "=" * 50)
    print(f"Completed in {elapsed:.1f}s")
    print("=" * 50)
    
    # 格式化輸出（供 grep 解析）
    print("\n--- TRAIN RESULTS ---")
    print(f"RESULT:train_pf={train_metrics['pf']}")
    print(f"RESULT:train_sharpe={train_metrics['sharpe']}")
    print(f"RESULT:train_maxdd={train_metrics['maxdd']}")
    print(f"RESULT:train_pob={train_metrics['pob']}")
    print(f"RESULT:train_dsr={train_metrics['dsr']}")
    print(f"RESULT:train_trades={train_metrics['n_trades']}")
    
    print("\n--- VALIDATION RESULTS ---")
    print(f"RESULT:val_pf={val_metrics['pf']}")
    print(f"RESULT:val_sharpe={val_metrics['sharpe']}")
    print(f"RESULT:val_maxdd={val_metrics['maxdd']}")
    print(f"RESULT:val_pob={val_metrics['pob']}")
    print(f"RESULT:val_dsr={val_metrics['dsr']}")
    print(f"RESULT:val_trades={val_metrics['n_trades']}")
    print(f"RESULT:val_return={val_metrics['total_return']}")
    
    print("\n--- TEST RESULTS ---")
    print(f"RESULT:test_pf={test_metrics['pf']}")
    print(f"RESULT:test_sharpe={test_metrics['sharpe']}")
    print(f"RESULT:test_maxdd={test_metrics['maxdd']}")
    print(f"RESULT:test_dsr={test_metrics['dsr']}")
    print(f"RESULT:test_trades={test_metrics['n_trades']}")
    print(f"RESULT:test_return={test_metrics['total_return']}")
    
    # 綜合評分（主要看測試集 DSR）
    print(f"\n>>> PRIMARY METRIC: test_dsr = {test_metrics['dsr']} <<<")
    print(f">>> 過擬合檢查: val_dsr={val_metrics['dsr']:.2f} vs test_dsr={test_metrics['dsr']:.2f} <<<")


if __name__ == "__main__":
    main()
