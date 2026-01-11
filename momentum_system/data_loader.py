
import logging
import pandas as pd
import yfinance as yf
from pathlib import Path
from typing import Dict, List, Optional
from .config import DATA_CACHE_DIR
from .logger_setup import setup_logger

logger = setup_logger(name="DataLoader")

class DataLoader:
    """
    Robust Data Loader with Local Caching and Validation.
    Fetches data from yfinance and caches it to CSV to minimize API calls.
    """

    def __init__(self, cache_dir: Path = DATA_CACHE_DIR):
        self.cache_dir = cache_dir
        if not self.cache_dir.exists():
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def fetch_data(
        self, 
        tickers: List[str], 
        start_date: str, 
        end_date: str, 
        use_cache: bool = True
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch historical data for a list of tickers.
        
        Args:
            tickers (List[str]): List of ticker symbols.
            start_date (str): Start date (YYYY-MM-DD).
            end_date (str): End date (YYYY-MM-DD).
            use_cache (bool): Whether to use local CSV cache.
            
        Returns:
            Dict[str, pd.DataFrame]: Dictionary mapping ticker to DataFrame.
        """
        data_map = {}
        
        for ticker in tickers:
            df = self._get_single_ticker_data(ticker, start_date, end_date, use_cache)
            if df is not None and not df.empty:
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
    ) -> Optional[pd.DataFrame]:
        """
        Helper to fetch data for a single ticker with caching logic.
        """
        cache_file = self.cache_dir / f"{ticker}.csv"
        
        # 1. Try Cache
        if use_cache and cache_file.exists():
            try:
                logger.debug(f"Loading {ticker} from cache: {cache_file}")
                df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
                
                # Filter by date range (naive filter implementation for simplicity)
                df = df[(df.index >= start_date) & (df.index <= end_date)]
                
                if self._validate_data(df, ticker):
                    return df
                else:
                    logger.warning(f"Cached data for {ticker} invalid. Re-fetching.")
            except Exception as e:
                logger.error(f"Error reading cache for {ticker}: {e}")

        # 2. Fetch from API
        logger.info(f"Fetching {ticker} from yfinance...")
        try:
            # auto_adjust=True handles splits/dividends nicely
            df = yf.download(ticker, start=start_date, end=end_date, progress=False, auto_adjust=True)
            
            # yfinance returns MultiIndex columns if multiple tickers, but we are doing one by one.
            # Flatten just in case.
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1) # Drop Ticker level if present

            # 3. Clean and Validate
            df = self._clean_data(df)
            
            if self._validate_data(df, ticker):
                # 4. Save to Cache
                df.to_csv(cache_file)
                logger.debug(f"Saved {ticker} to cache.")
                return df
            
        except Exception as e:
            logger.error(f"Failed to fetch data for {ticker}: {e}")
            
        return None

    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean raw data: remove zero volume, handle NaNs.
        """
        # Remove rows with zero volume (non-trading days)
        if 'Volume' in df.columns:
            df = df[df['Volume'] > 0]
        
        # Remove rows with any NaN values
        df = df.dropna()
        
        return df

    def _validate_data(self, df: pd.DataFrame, ticker: str) -> bool:
        """
        Check data quality.
        """
        if df.empty:
            logger.warning(f"Validation failed for {ticker}: DataFrame is empty.")
            return False
            
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        missing_cols = [c for c in required_cols if c not in df.columns]
        
        if missing_cols:
            logger.warning(f"Validation failed for {ticker}: Missing columns {missing_cols}")
            return False
            
        # Check for sufficient data length (arbitrary minimum for SMA calc)
        # Ideally should check against config lookbacks, but keeping simple here.
        if len(df) < 50:
            logger.warning(f"Validation warning for {ticker}: Only {len(df)} rows (might be insufficient for indicators).")
        
        return True
