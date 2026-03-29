"""
strategy.py — autoquant 實驗文件

實驗 #3: Donchian 通道突破 (海龜交易法)
來源: Richard Dennis / Turtle Traders
"""

import numpy as np
import pandas as pd

# ============== 策略參數 ==============
PARAMS = {
    'position_size': 0.25,
    
    # Donchian 參數（更長）
    'entry_period': 40,       # 加長到 40 根 4H (6.7天)
    'exit_period': 20,        # 加長到 20 根 4H
    
    # 趨勢過濾
    'use_trend_filter': False,  # 關閉趨勢過濾
    'trend_period': 50,       # EMA50 過濾
    
    # 出場（放寬止損）
    'sl_atr_mult': 2.5,
    
    'cooldown_bars': 2,
}

# ============== 內部狀態 ==============
_last_exit_idx = -999
_entry_price = 0
_entry_idx = 0
_sl_price = 0


def reset_state():
    global _last_exit_idx, _entry_price, _entry_idx, _sl_price
    _last_exit_idx = -999
    _entry_price = 0
    _entry_idx = 0
    _sl_price = 0


def generate_signal(df: pd.DataFrame, idx: int, position: int, params: dict, check_exit: bool = False) -> int:
    global _last_exit_idx, _entry_price, _entry_idx, _sl_price
    
    entry_period = params.get('entry_period', 20)
    exit_period = params.get('exit_period', 10)
    
    if idx < max(entry_period, exit_period) + 1:
        return 0
    
    row = df.iloc[idx]
    close = row['close']
    high = row['high']
    low = row['low']
    atr = row['atr']
    
    # Donchian 通道
    entry_high = df.iloc[idx-entry_period:idx]['high'].max()
    entry_low = df.iloc[idx-entry_period:idx]['low'].min()
    exit_high = df.iloc[idx-exit_period:idx]['high'].max()
    exit_low = df.iloc[idx-exit_period:idx]['low'].min()
    
    # ===== 出場檢查 =====
    if check_exit and position != 0:
        sl_mult = params.get('sl_atr_mult', 2.0)
        
        if position == 1:
            # 止損
            if low <= _sl_price:
                _last_exit_idx = idx
                return True
            # Donchian 出場 (跌破 exit_period 低點)
            if close < exit_low:
                _last_exit_idx = idx
                return True
        else:
            # 止損
            if high >= _sl_price:
                _last_exit_idx = idx
                return True
            # Donchian 出場 (突破 exit_period 高點)
            if close > exit_high:
                _last_exit_idx = idx
                return True
        return False
    
    # ===== 冷卻期 =====
    if idx - _last_exit_idx < params.get('cooldown_bars', 2):
        return 0
    
    if position != 0:
        return 0
    
    # ===== 趨勢過濾 =====
    if params.get('use_trend_filter', True):
        ema = row['ema50']
        # 只在趨勢方向交易
        if close > ema:
            allow_long = True
            allow_short = False
        else:
            allow_long = False
            allow_short = True
    else:
        allow_long = True
        allow_short = True
    
    # ===== RSI 動量過濾 =====
    rsi = row['rsi']
    
    # ===== ADX 趨勢強度過濾 =====
    adx = row['adx']
    if adx < 15:  # ADX < 15 = 無趨勢，不交易（放寬）
        return 0
    
    # ===== Donchian 突破 =====
    sl_mult = params.get('sl_atr_mult', 2.0)
    
    # 突破 entry_period 高點做多（RSI > 50 確認動量）
    if allow_long and high > entry_high and rsi > 50:
        _entry_price = close
        _entry_idx = idx
        _sl_price = close - sl_mult * atr
        return 1
    
    # 跌破 entry_period 低點做空（RSI < 50 確認動量）
    if allow_short and low < entry_low and rsi < 50:
        _entry_price = close
        _entry_idx = idx
        _sl_price = close + sl_mult * atr
        return -1
    
    return 0
