
import logging
import polars as pl
import pandas as pd
import yfinance as yf
from pathlib import Path
from typing import Dict, List, Optional
from .config import DATA_CACHE_DIR
from .logger_setup import setup_logger, measure_latency

logger = setup_logger(name=__name__)

class DataLoader:
    """
    Robust Data Loader with Local Caching and Validation.
    Fetches data from yfinance and caches it to CSV to minimize API calls.
    Returns Polars DataFrames.
    """

    def __init__(self, cache_dir: Path = DATA_CACHE_DIR):
        self.cache_dir = cache_dir
        if not self.cache_dir.exists():
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    @measure_latency
    def fetch_data(
        self, 
        tickers: List[str], 
        start_date: str, 
        end_date: str, 
        use_cache: bool = True
    ) -> Dict[str, pl.DataFrame]:
        """
        Fetch historical data for a list of tickers.
        
        Args:
            tickers (List[str]): List of ticker symbols.
            start_date (str): Start date (YYYY-MM-DD).
            end_date (str): End date (YYYY-MM-DD).
            use_cache (bool): Whether to use local CSV cache.
            
        Returns:
            Dict[str, pl.DataFrame]: Dictionary mapping ticker to Polars DataFrame.
        """
        data_map = {}
        
        for ticker in tickers:
            df = self._get_single_ticker_data(ticker, start_date, end_date, use_cache)
            if df is not None and not df.is_empty():
                data_map[ticker] = df
                logger.info(f"Successfully loaded data for {ticker}: {len(df)} rows.")
            else:
                logger.warning(f"No valid data found for {ticker}.")
                
        return data_map

    def _get_single_ticker_data(
        self, 
        ticker: str, 
        start_date: str, 
        end_date: str, 
        use_cache: bool
    ) -> Optional[pl.DataFrame]:
        """
        Helper to fetch data for a single ticker with caching logic.
        """
        cache_file = self.cache_dir / f"{ticker}.csv"
        
        # 1. Try Cache
        if use_cache and cache_file.exists():
            try:
                logger.debug(f"Loading {ticker} from cache: {cache_file}")
                # Polars read_csv is very fast
                df = pl.read_csv(cache_file, try_parse_dates=True)
                
                # Check for Date column (Polars doesn't implicitly index by Date)
                if 'Date' in df.columns:
                    # Filter by date range
                    # Ensure Date is Date type (read_csv might infer Datetime)
                    df = df.filter(
                        (pl.col("Date") >= pl.lit(start_date).str.to_date()) & 
                        (pl.col("Date") <= pl.lit(end_date).str.to_date())
                    )
                    # Sort by Date just in case
                    df = df.sort("Date")
                else:
                     logger.warning(f"Cache for {ticker} missing Date column.")

                if self._validate_data(df, ticker):
                    return df
                else:
                    logger.warning(f"Cached data for {ticker} invalid. Re-fetching.")
            except Exception as e:
                logger.error(f"Error reading cache for {ticker}: {e}")

        # 2. Fetch from API (Returns Pandas)
        logger.info(f"Fetching {ticker} from yfinance...")
        try:
            # yfinance returns Pandas DataFrame
            pd_df = yf.download(ticker, start=start_date, end=end_date, progress=False, auto_adjust=True)
            
            # Reset index to make Date a column (Polars prefers no index)
            pd_df = pd_df.reset_index()

            # yfinance MultiIndex handling
            if isinstance(pd_df.columns, pd.MultiIndex):
                # Flatten or drop levels if needed, but reset_index usually handles the Ticker level issue somewhat
                # Better: just convert to Polars and clean up
                pd_df.columns = [c[0] if isinstance(c, tuple) else c for c in pd_df.columns]

            # Convert to Polars
            df = pl.from_pandas(pd_df)
            
            # Ensure Date column is proper Date type (yfinance might give Datetime)
            if 'Date' in df.columns:
                df = df.with_columns(pl.col("Date").cast(pl.Date))

            # 3. Clean and Validate
            df = self._clean_data(df)
            
            if self._validate_data(df, ticker):
                # 4. Save to Cache
                df.write_csv(cache_file)
                logger.debug(f"Saved {ticker} to cache.")
                return df
            
        except Exception as e:
            logger.error(f"Failed to fetch data for {ticker}: {e}")
            
        return None

    def _clean_data(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Clean raw data: remove zero volume, handle Nulls.
        """
        # Remove rows with zero volume
        if 'Volume' in df.columns:
            df = df.filter(pl.col('Volume') > 0)
        
        # Remove rows with any Null values
        df = df.drop_nulls()
        
        return df

    def _validate_data(self, df: pl.DataFrame, ticker: str) -> bool:
        """
        Check data quality.
        """
        if df.is_empty():
            logger.warning(f"Validation failed for {ticker}: DataFrame is empty.")
            return False
            
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        missing_cols = [c for c in required_cols if c not in df.columns]
        
        if missing_cols:
            logger.warning(f"Validation failed for {ticker}: Missing columns {missing_cols}")
            return False
            
        if len(df) < 50:
            logger.warning(f"Validation warning for {ticker}: Only {len(df)} rows (might be insufficient for indicators).")
        
        return True

