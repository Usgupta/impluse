
import pandas as pd
import numpy as np
from typing import Tuple

def calculate_sma(series: pd.Series, window: int) -> pd.Series:
    """Calculates Simple Moving Average."""
    return series.rolling(window=window).mean()

def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
    """
    Calculates Average True Range (ATR).
    TR = Max(High-Low, |High-PrevClose|, |Low-PrevClose|)
    ATR = Smoothed TR
    """
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Wilder's Smoothing (pandas ewm with alpha=1/window is close approximation)
    # Using simple rolling mean for standard ATR definition or EWM
    # Wilder's smoothing: ATR = (Prev ATR * (n-1) + TR) / n
    # This is equivalent to pandas ewm(alpha=1/n, adjust=False)
    atr = tr.ewm(alpha=1/window, adjust=False).mean()
    return atr

def detect_consolidation(
    high: pd.Series, 
    close: pd.Series, 
    lookback_peak: int = 63,
    min_days: int = 4, 
    max_days: int = 40, 
    tolerance: float = 0.15
) -> pd.Series:
    """
    Detects if price is in a 'Tread' / Consolidation state.
    
    Logic:
    1. Identify the Peak High over the last `lookback_peak` days.
    2. Calculate Drawdown from that Peak.
    3. Check if Drawdown has remained within `tolerance` (e.g., 15%) 
       for at least `min_days` and is currently within that window.
    
    Args:
        high: High price series.
        close: Close price series.
        lookback_peak: Lookback window to find the reference peak (e.g. 63 days).
        min_days: Minimum days the price must be stable.
        max_days: Maximum days for consideration (implicit in usage, but can filter length).
        tolerance: Max allowed drawdown from peak (e.g. 0.15 for 15%).
        
    Returns:
        pd.Series: Boolean series indicating if the day is part of a valid consolidation.
    """
    # 1. Rolling Max High
    rolling_peak = high.rolling(window=lookback_peak, min_periods=1).max()
    
    # 2. Drawdown from Peak (using Close price to avoid intraday wicks disqualifying valid bases)
    # Use Close or High? VCP usually implies tight closes. Let's use Close relative to Peak High.
    drawdown_pct = (rolling_peak - close) / rolling_peak
    
    # 3. Is price TIGHT? (Within tolerance)
    is_tight = drawdown_pct <= tolerance
    
    # 4. Has it been tight for at least min_days?
    # We use a rolling sum of the boolean 'is_tight'. 
    # If rolling_sum(is_tight, window=min_days) == min_days, then we have been tight for at least min_days.
    stable_period = is_tight.rolling(window=min_days, min_periods=1).sum() == min_days
    
    return stable_period

def calculate_roc(series: pd.Series, window: int) -> pd.Series:
    """Rate of Change Percentage."""
    return series.pct_change(periods=window) * 100
