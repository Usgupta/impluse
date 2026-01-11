
import polars as pl
import numpy as np
from .config import STRATEGY_PARAMS
from .indicators import calculate_sma, calculate_atr, detect_consolidation, calculate_roc
from .logger_setup import setup_logger, measure_latency

logger = setup_logger(name=__name__)

class MomentumStrategy:
    """
    Implements Minervini-style Trend & VCP Logic.
    """
    
    def __init__(self, params: dict = STRATEGY_PARAMS):
        self.params = params

    @measure_latency
    def prepare_data(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Calculates all indicators and signal flags. 
        Returns df with added columns.
        """
        # Polars DataFrames are immutable-like when adding columns, creating new DF or lazy
        # Since I'm in eager mode (DataFrame), with_columns returns new DF
        
        # --- Indicators ---
        # We can construct a list of expressions to execute in parallel
        
        sma_fast_window = self.params['SMA_FAST']
        sma_medium_window = self.params['SMA_MEDIUM']
        sma_slow_window = self.params['SMA_SLOW']
        rs_lookback = self.params['RS_LOOKBACK']
        
        df = df.with_columns([
            calculate_sma(pl.col('Close'), sma_fast_window).alias('SMA_50'),
            calculate_sma(pl.col('Close'), sma_medium_window).alias('SMA_150'),
            calculate_sma(pl.col('Close'), sma_slow_window).alias('SMA_200'),
            calculate_atr(pl.col('High'), pl.col('Low'), pl.col('Close'), window=14).alias('ATR'),
            calculate_roc(pl.col('Close'), rs_lookback).alias('RS_Rating')
        ])
        
        # --- Trend Template Rules (Boolean) ---
        # 1. Price > SMA 50 > SMA 150 > SMA 200 (Ideal trend alignment)
        
        trend_cond = (
            (pl.col('Close') > pl.col('SMA_50')) &
            (pl.col('SMA_50') > pl.col('SMA_150')) &
            (pl.col('SMA_150') > pl.col('SMA_200'))
        )
        
        # 52-Week High/Low Logic (Approximation)
        rolling_52w_low = pl.col('Low').rolling_min(window_size=252)
        rolling_52w_high = pl.col('High').rolling_max(window_size=252)
        
        # Within 25% of High, > 25% off Low
        prox_cond = (
            (pl.col('Close') > rolling_52w_low * 1.25) & 
            (pl.col('Close') > rolling_52w_high * 0.75)
        )
        
        # --- VCP / Consolidation Setup ---
        # "Tread": Stabilized for 4-40 days
        is_tight_expr = detect_consolidation(
            pl.col('High'), 
            pl.col('Close'), 
            lookback_peak=self.params['LOOKBACK_PEAK'],
            min_days=self.params['CONSOLIDATION_MIN_DAYS'],
            tolerance=self.params['CONSOLIDATION_TOLERANCE']
        )
        
        df = df.with_columns([
            (trend_cond & prox_cond).alias('In_Uptrend'),
            is_tight_expr.alias('Is_Tight')
        ])
        
        # --- Signal Generation ---
        # Setup: Uptrend + Tightness
        df = df.with_columns(
            (pl.col('In_Uptrend') & pl.col('Is_Tight')).alias('Setup')
        )
        
        # Trigger: Breakout from the consolidation.
        # Logic: If we were in a Setup yesterday (or recently), and today we break above the 
        # local resistance (Rolling Max of the consolidation window), that's a buy.
        
        # Identify the resistance level (Rolling Max High of recent tight period)
        # We use a 20-day lookback for the local pivot point usually.
        df = df.with_columns([
            pl.col('High').rolling_max(window_size=20).shift(1).alias('Pivot')
        ])
        
        # Signal: Yesterday was Setup, Today Close > Pivot
        # Using shift(1) for 'Setup' because we trade on the day *after* setup is confirmed/ongoing
        # or if we are IN the setup and break out.
        
        df = df.with_columns(
            (
                (pl.col('Setup').shift(1)) & 
                (pl.col('Close') > pl.col('Pivot'))
            ).alias('Buy_Signal')
        )

        # Clean up Nulls that might propagate from rolling windows
        # Strategy usually needs full history, but signals at the start will be null.
        # Fill null booleans with False to be safe?
        df = df.with_columns([
            pl.col('Buy_Signal').fill_null(False),
            pl.col('Setup').fill_null(False)
        ])
        
        return df
