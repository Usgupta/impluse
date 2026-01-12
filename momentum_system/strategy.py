
import polars as pl
import numpy as np
from .common.config import STRATEGY_PARAMS
from .common.indicators import calculate_sma, calculate_atr, calculate_roc
from .screener import Screener
from .signaller import Signaller
from .common.logger_setup import setup_logger, measure_latency

logger = setup_logger(name=__name__)

class MomentumStrategy:
    """
    Orchestrates the three-phase trading system:
    1. Screener: Applies liquidity and trend filters
    2. Signaller: Detects momentum patterns and generates signals
    3. Executor: Handles risk management and trade execution (used by backtester)
    
    This class maintains backward compatibility by providing the prepare_data() method
    expected by the backtester.
    """
    
    def __init__(self, params: dict = STRATEGY_PARAMS):
        self.params = params
        self.screener = Screener(params)
        self.signaller = Signaller(params)

    @measure_latency
    def prepare_data(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Calculates all indicators and signal flags using the three-module architecture.
        Returns df with added columns.
        
        Flow:
        1. Calculate base technical indicators (SMA, ATR, ROC)
        2. Apply Screener filters (liquidity, trend)
        3. Generate Signaller signals (Riser, Tread, entry trigger)
        """
        # --- Step 1: Calculate Base Indicators ---
        sma_fast_window = self.params['SMA_FAST']
        sma_medium_window = self.params['SMA_MEDIUM']
        sma_slow_window = self.params['SMA_SLOW']
        rs_lookback = self.params['RS_LOOKBACK']
        
        df = df.with_columns([
            calculate_sma(pl.col('Close'), sma_fast_window).alias('SMA_50'),
            calculate_sma(pl.col('Close'), sma_medium_window).alias('SMA_150'),
            calculate_sma(pl.col('Close'), sma_slow_window).alias('SMA_200'),
            calculate_sma(pl.col('Close'), 10).alias('SMA_10'),  # For Trailing Stop (Executor)
            calculate_sma(pl.col('Volume'), 50).alias('Volume_SMA_50'), # For Liquidity Filter (Screener)
            calculate_atr(pl.col('High'), pl.col('Low'), pl.col('Close'), window=14).alias('ATR'),  # For Risk (Executor)
            calculate_roc(pl.col('Close'), rs_lookback).alias('RS_Rating')  # For Riser detection (Signaller)
        ])
        
        # --- Step 2: Apply Screener Filters (Phase II) ---
        df = self.screener.apply_filters(df)
        
        # --- Step 3: Generate Signals (Phase III) ---
        df = self.signaller.generate_signals(df)
        
        return df
