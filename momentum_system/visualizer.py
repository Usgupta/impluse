
import pandas as pd
import mplfinance as mpf
from pathlib import Path
from typing import Dict
from .logger_setup import setup_logger

logger = setup_logger(name="TradeVisualizer")

class TradeVisualizer:
    """
    Generates professional trade setups using mplfinance.
    """
    
    def __init__(self, output_dir: str = "charts"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
    def plot_trade(self, ticker: str, df: pd.DataFrame, trade_details: Dict):
        """
        Plots a candlestick chart with overlays for a specific trade.
        """
        entry_date = trade_details['Entry Date']
        exit_date = trade_details['Exit Date']
        
        # Buffer around trade
        start_idx = df.index.get_loc(entry_date) - 50
        end_idx = df.index.get_loc(exit_date) + 20
        start_idx = max(0, start_idx)
        end_idx = min(len(df), end_idx)
        
        plot_df = df.iloc[start_idx:end_idx]
        
        # Add Overlays
        apds = [
            mpf.make_addplot(plot_df['SMA_50'], color='blue', width=1.5),
            mpf.make_addplot(plot_df['SMA_150'], color='orange', width=1.5),
            mpf.make_addplot(plot_df['SMA_200'], color='red', width=1.5),
        ]
        
        # Entry Marker
        if entry_date in plot_df.index:
            entry_price = trade_details['Entry Price']
            # We can't plot single points easily with make_addplot unless we make a series
            # So simpler: just title annotation or use vlines
            
        # Chart Style
        s = mpf.make_mpf_style(base_mpf_style='charles', rc={'font.size': 10})
        
        filename = self.output_dir / f"{ticker}_{entry_date.strftime('%Y%m%d')}_trade.png"
        
        title = f"{ticker} Trade | Entry: {entry_date.date()} @ {trade_details['Entry Price']:.2f} | PnL: {trade_details['PnL']:.2f}"
        
        try:
            mpf.plot(
                plot_df, 
                type='candle', 
                style=s,
                title=title,
                addplot=apds,
                volume=True,
                savefig=filename,
                tight_layout=True,
                vlines=dict(vlines=[entry_date, exit_date], linewidths=1, linestyle='-.', colors='grey')
            )
            logger.info(f"Chart saved to {filename}")
        except Exception as e:
            logger.error(f"Failed to plot trade for {ticker}: {e}")
