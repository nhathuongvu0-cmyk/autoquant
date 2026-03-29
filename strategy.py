"""
autoquant v2.0 实验 #8
策略：极简动量（25天）
"""
import numpy as np
import pandas as pd

PARAMS = {
    'position_size': 1.0,
    'momentum_days': 25,
    'threshold': 0.05,
    'cooldown_bars': 5,
}

_last_exit_idx = -999
_entry_price = 0

def reset_state():
    global _last_exit_idx, _entry_price
    _last_exit_idx = -999
    _entry_price = 0

def generate_signal(df, idx, position, params, check_exit=False):
    global _last_exit_idx, _entry_price
    
    lb = params['momentum_days'] * 6
    if idx < lb + 1:
        return 0
    
    row = df.iloc[idx]
    close = row['close']
    past_close = df.iloc[idx - lb]['close']
    momentum = (close - past_close) / past_close
    
    if check_exit and position != 0:
        if position == 1 and momentum < 0:
            _last_exit_idx = idx
            return True
        if position == -1 and momentum > 0:
            _last_exit_idx = idx
            return True
        return False
    
    if idx - _last_exit_idx < params['cooldown_bars']:
        return 0
    if position != 0:
        return 0
    
    th = params['threshold']
    if momentum > th:
        _entry_price = close
        return 1
    elif momentum < -th:
        _entry_price = close
        return -1
    
    return 0
