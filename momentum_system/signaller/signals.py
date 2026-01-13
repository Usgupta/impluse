
import polars as pl
from ..common.config import STRATEGY_PARAMS
from ..common.indicators import detect_consolidation, calculate_roc
from ..common.logger_setup import setup_logger, measure_latency

logger = setup_logger(name=__name__)

class Signaller:
    """
    Phase III: The Signaller
    Detects momentum setups (Riser + Tread) and generates entry signals.
    
    Per Technical Test Requirements:
    - The Riser (Impulse): Price increased >= 30% in recent 63 trading days
    - The Tread (Consolidation): Stabilized for 4-40 days, < 25% retracement
    - Entry Trigger: BUY when price breaks above consolidation high (Pivot)
    """
    
    def __init__(self, params: dict = STRATEGY_PARAMS):
        self.params = params

    @measure_latency
    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Generates buy signals based on Riser + Tread + Breakout logic.
        Adds columns: Has_Riser, Has_Tread, Setup, Buy_Signal
        
        Args:
            df: DataFrame with OHLCV data, indicators, and screening results
            
        Returns:
            DataFrame with added signal columns
        """
        # --- Riser (Impulse) Condition ---
        # Price must have increased by >= 30% in last 63 trading days
        # RS_Rating is ROC over RS_LOOKBACK period (63 days)
        riser_cond = pl.col('RS_Rating') >= 30.0
        
        # --- VCP / Consolidation (Tread) Setup ---
        # Stabilized for 4-40 days with < 25% retracement
        is_tight_expr = detect_consolidation(
            pl.col('High'), 
            pl.col('Close'), 
            lookback_peak=self.params['LOOKBACK_PEAK'],
            min_days=self.params['CONSOLIDATION_MIN_DAYS'],
            tolerance=self.params['CONSOLIDATION_TOLERANCE']
        )
        
        # Add intermediate columns
        df = df.with_columns([
            riser_cond.alias('Has_Riser'),
            is_tight_expr.alias('Has_Tread')
        ])
        
        # --- Setup: Valid Screen + Riser + Tread ---
        # Stock must pass screening AND show momentum pattern
        df = df.with_columns(
            (pl.col('Passes_Screen') & pl.col('Has_Riser') & pl.col('Has_Tread')).alias('Setup')
        )
        
        # --- Entry Trigger: Breakout from Consolidation ---
        # Per requirement line 39: "Signal a BUY when the price breaks above the High 
        # of the consolidation range (the peak price achieved during the last 63 trading days)"
        # 
        # INTERPRETATION: The parenthetical phrase defines the consolidation range high
        # as the 63-day peak (which is also the reference peak used in Riser/Tread logic).
        # This means entry requires full recovery to the 63-day high.
        #
        # NOTE: This differs from standard VCP methodology where entry would occur at
        # the consolidation high (may be lower than the impulse high). However, the
        # literal requirement specifies "the peak price achieved during the last 63 trading days."
        df = df.with_columns([
            pl.col('High').rolling_max(window_size=63).shift(1).alias('Pivot')
        ])
        
        # Signal: Yesterday was Setup, Today Close > Pivot (Breakout)
        # Using shift(1) for Setup ensures we don't look ahead
        df = df.with_columns(
            (
                (pl.col('Setup').shift(1)) & 
                (pl.col('Close') > pl.col('Pivot'))
            ).alias('Buy_Signal')
        )

        # Clean up Nulls from rolling windows
        df = df.with_columns([
            pl.col('Buy_Signal').fill_null(False),
            pl.col('Setup').fill_null(False)
        ])
        
        return df
