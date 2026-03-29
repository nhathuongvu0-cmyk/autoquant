"""
strategy.py — 策略定義文件
這是 AI agent 修改的文件！

Baseline: 簡單 EMA 交叉策略（先確保引擎正常）
"""

import numpy as np
import pandas as pd

# ============== 策略參數 ==============
PARAMS = {
    'position_size': 0.25,
    'fast_ema': 8,
    'slow_ema': 21,
    'tp_pct': 0.02,   # 2% TP
    'sl_pct': 0.01,   # 1% SL
    'cooldown_bars': 3,
}

# ============== 內部狀態 ==============
_last_exit_idx = -999
_entry_price = 0


def reset_state():
    global _last_exit_idx, _entry_price
    _last_exit_idx = -999
    _entry_price = 0


def generate_signal(df: pd.DataFrame, idx: int, position: int, params: dict, check_exit: bool = False) -> int:
    global _last_exit_idx, _entry_price
    
    if idx < 2:
        return 0
    
    row = df.iloc[idx]
    prev = df.iloc[idx - 1]
    
    # 出場檢查
    if check_exit and position != 0:
        close = row['close']
        high = row['high']
        low = row['low']
        tp = params.get('tp_pct', 0.02)
        sl = params.get('sl_pct', 0.01)
        
        if position == 1:
            if high >= _entry_price * (1 + tp) or low <= _entry_price * (1 - sl):
                _last_exit_idx = idx
                return True
        else:
            if low <= _entry_price * (1 - tp) or high >= _entry_price * (1 + sl):
                _last_exit_idx = idx
                return True
        return False
    
    # 冷卻期
    if idx - _last_exit_idx < params.get('cooldown_bars', 3):
        return 0
    
    if position != 0:
        return 0
    
    # EMA 交叉
    fast = row['ema8']
    slow = row['ema21']
    prev_fast = prev['ema8']
    prev_slow = prev['ema21']
    
    # 金叉做多
    if prev_fast <= prev_slow and fast > slow:
        _entry_price = row['close']
        return 1
    
    # 死叉做空
    if prev_fast >= prev_slow and fast < slow:
        _entry_price = row['close']
        return -1
    
    return 0
