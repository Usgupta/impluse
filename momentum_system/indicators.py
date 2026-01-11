import polars as pl
from .logger_setup import measure_latency, setup_logger

logger = setup_logger(name=__name__)

@measure_latency
def calculate_sma(expr: pl.Expr, window: int) -> pl.Expr:
    """Calculates Simple Moving Average."""
    return expr.rolling_mean(window_size=window)

@measure_latency
def calculate_atr(high: pl.Expr, low: pl.Expr, close: pl.Expr, window: int = 14) -> pl.Expr:
    """
    Calculates Average True Range (ATR).
    TR = Max(High-Low, |High-PrevClose|, |Low-PrevClose|)
    ATR = Smoothed TR
    """
    prev_close = close.shift(1)
    
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    
    # Max of the three
    tr = pl.max_horizontal(tr1, tr2, tr3)
    
    # Wilder's Smoothing: ewm(alpha=1/window, adjust=False)
    # Polars ewm_mean supports this directly
    return tr.ewm_mean(alpha=1/window, adjust=False, min_periods=window)

@measure_latency
def detect_consolidation(
    high: pl.Expr, 
    close: pl.Expr, 
    lookback_peak: int = 63,
    min_days: int = 4, 
    max_days: int = 40, 
    tolerance: float = 0.25
) -> pl.Expr:
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
    rolling_peak = high.rolling_max(window_size=lookback_peak, min_periods=1)
    
    # 2. Drawdown from Peak (using Close price to avoid intraday wicks disqualifying valid bases)
    # Use Close or High? VCP usually implies tight closes. Let's use Close relative to Peak High.
    drawdown_pct = (rolling_peak - close) / rolling_peak
    
    # 3. Is price TIGHT? (Within tolerance)
    is_tight = drawdown_pct <= tolerance
    
    # 4. Has it been tight for at least min_days?
    # Rolling sum of booleans (treated as 0/1)
    # cast to integer (0/1) then rolling_sum
    stable_period = is_tight.cast(pl.Int8).rolling_sum(window_size=min_days, min_periods=1) == min_days
    
    return stable_period

@measure_latency
def calculate_roc(expr: pl.Expr, window: int) -> pl.Expr:
    """Rate of Change Percentage."""
    # (Price / Price.shift(n)) - 1
    # or pct_change logic
    return (expr / expr.shift(window) - 1.0) * 100.0
