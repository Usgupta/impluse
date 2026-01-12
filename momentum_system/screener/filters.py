
import polars as pl
from ..common.config import STRATEGY_PARAMS
from ..common.indicators import calculate_sma
from ..common.logger_setup import setup_logger, measure_latency

logger = setup_logger(name=__name__)

class Screener:
    """
    Phase II: The Screener
    Applies liquidity and trend filters to identify candidate stocks.
    
    Per Technical Test Requirements:
    - Liquidity Filter: Price >= $3.00 AND 50-day Avg Volume >= 300,000
    - Trend Filter: Current Price must be above its 50-day SMA
    """
    
    def __init__(self, params: dict = STRATEGY_PARAMS):
        self.params = params

    @measure_latency
    def apply_filters(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Applies screening filters to the DataFrame.
        Adds columns: passes_liquidity, passes_trend, passes_screen
        
        Args:
            df: DataFrame with OHLCV data and pre-calculated indicators
            
        Returns:
            DataFrame with added screening columns
        """
        # --- Liquidity Filter ---
        # Price >= 3.00 AND 50-day Avg Volume >= 300,000
        liquidity_cond = (
            (pl.col('Close') >= 3.00) &
            (pl.col('Volume_SMA_50') >= 300000)
        )
        
        # --- Trend Template Rules ---
        # Price > SMA 50 > SMA 150 > SMA 200 (Ideal trend alignment)
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
        
        # Combined screen: All conditions must pass
        df = df.with_columns([
            liquidity_cond.alias('Passes_Liquidity'),
            (trend_cond & prox_cond).alias('Passes_Trend'),
            (liquidity_cond & trend_cond & prox_cond).alias('Passes_Screen')
        ])
        
        return df
