
import pandas as pd
import numpy as np
from .config import STRATEGY_PARAMS
from .indicators import calculate_sma, calculate_atr, detect_consolidation, calculate_roc
from .logger_setup import setup_logger

logger = setup_logger(name="MomentumStrategy")

class MomentumStrategy:
    """
    Implements Minervini-style Trend & VCP Logic.
    """
    
    def __init__(self, params: dict = STRATEGY_PARAMS):
        self.params = params

    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates all indicators and signal flags. 
        Returns df with added columns.
        """
        df = df.copy()
        
        # --- Indicators ---
        df['SMA_50'] = calculate_sma(df['Close'], self.params['SMA_FAST'])
        df['SMA_150'] = calculate_sma(df['Close'], self.params['SMA_MEDIUM'])
        df['SMA_200'] = calculate_sma(df['Close'], self.params['SMA_SLOW'])
        df['ATR'] = calculate_atr(df['High'], df['Low'], df['Close'], window=14)
        
        # Relative Strength (Proxy: ROC 63 days)
        df['RS_Rating'] = calculate_roc(df['Close'], self.params['RS_LOOKBACK'])
        
        # --- Trend Template Rules (Boolean) ---
        # 1. Price > SMA 50 > SMA 150 > SMA 200 (Ideal trend alignment)
        # Note: Making it a bit looser for demo: Price > 150 > 200 is strict enough foundation.
        
        trend_cond = (
            (df['Close'] > df['SMA_50']) &
            (df['SMA_50'] > df['SMA_150']) &
            (df['SMA_150'] > df['SMA_200'])
        )
        
        # 52-Week High/Low Logic (Approximation)
        rolling_52w_low = df['Low'].rolling(window=252).min()
        rolling_52w_high = df['High'].rolling(window=252).max()
        
        # Within 25% of High, > 25% off Low
        prox_cond = (
            (df['Close'] > rolling_52w_low * 1.25) & 
            (df['Close'] > rolling_52w_high * 0.75)
        )
        
        df['In_Uptrend'] = trend_cond & prox_cond
        
        # --- VCP / Consolidation Setup ---
        # "Tread": Stabilized for 4-40 days
        df['Is_Tight'] = detect_consolidation(
            df['High'], 
            df['Close'], 
            lookback_peak=self.params['LOOKBACK_PEAK'],
            min_days=self.params['CONSOLIDATION_MIN_DAYS'],
            tolerance=self.params['CONSOLIDATION_TOLERANCE']
        )
        
        # --- Signal Generation ---
        # Setup: Uptrend + Tightness
        df['Setup'] = df['In_Uptrend'] & df['Is_Tight']
        
        # Trigger: Breakout from the consolidation.
        # Logic: If we were in a Setup yesterday (or recently), and today we break above the 
        # local resistance (Rolling Max of the consolidation window), that's a buy.
        
        # Identify the resistance level (Rolling Max High of recent tight period)
        # We use a 20-day lookback for the local pivot point usually.
        df['Pivot'] = df['High'].rolling(20).max().shift(1)
        
        # Signal: Yesterday was Setup, Today Close > Pivot
        # Using shift(1) for 'Setup' because we trade on the day *after* setup is confirmed/ongoing
        # or if we are IN the setup and break out.
        
        df['Buy_Signal'] = (
            (df['Setup'].shift(1) == True) & 
            (df['Close'] > df['Pivot'])
        )
        
        return df
