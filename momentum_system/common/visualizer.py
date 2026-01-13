import pandas as pd
import polars as pl
import matplotlib.pyplot as plt
import mplfinance as mpf
from pathlib import Path
from typing import Dict, Union
from .config import BASE_DIR
from .logger_setup import setup_logger, measure_latency

logger = setup_logger(name=__name__)

class TradeVisualizer:
    """
    Generates professional trade setups using mplfinance.
    """
    
    def __init__(self, output_dir: str = "charts"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
    @measure_latency
    def plot_trade(self, ticker: str, df: Union[pd.DataFrame, pl.DataFrame], trade_details: Dict):
        """
        Plots a candlestick chart with overlays for a specific trade.
        """
        # Handle Polars Input
        if isinstance(df, pl.DataFrame):
            df = df.to_pandas()
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'])
                df.set_index('Date', inplace=True)

        entry_date = trade_details['Entry Date']
        exit_date = trade_details['Exit Date']
        
        # Buffer around trade
        start_idx = df.index.get_loc(entry_date) - 50
        end_idx = df.index.get_loc(exit_date) + 20
        start_idx = max(0, start_idx)
        end_idx = min(len(df), end_idx)
        
        plot_df = df.iloc[start_idx:end_idx]
        
        # Add Overlays with labels - more vibrant colors
        apds = [
            mpf.make_addplot(plot_df['SMA_50'], color='#2E86DE', width=2.0, label='SMA 50'),    # Bright blue
            mpf.make_addplot(plot_df['SMA_150'], color='#FF9F43', width=2.0, label='SMA 150'),  # Orange
            mpf.make_addplot(plot_df['SMA_200'], color='#EE5A6F', width=2.0, label='SMA 200'),  # Pink-red
        ]
        
        # Chart Style - improved readability
        s = mpf.make_mpf_style(
            base_mpf_style='charles',
            rc={
                'font.size': 11,
                'axes.labelsize': 12,
                'axes.titlesize': 14,
                'xtick.labelsize': 10,
                'ytick.labelsize': 10,
            },
            gridstyle='--',
            gridcolor='#E8E8E8',
            gridaxis='both'
        )
        
        filename = self.output_dir / f"{ticker}_{entry_date.strftime('%Y%m%d')}_trade.png"
        
        # Format P&L with color
        pnl = trade_details['PnL']
        pnl_str = f"+${pnl:,.0f}" if pnl >= 0 else f"-${abs(pnl):,.0f}"
        return_pct = trade_details.get('Return %', 0) * 100
        
        title = f"{ticker} Trade | Entry: {entry_date.strftime('%Y-%m-%d')} @ ${trade_details['Entry Price']:.2f} | P&L: {pnl_str} ({return_pct:+.1f}%)"
        
        try:
            fig, axes = mpf.plot(
                plot_df, 
                type='candle', 
                style=s,
                title=title,
                addplot=apds,
                volume=True,
                returnfig=True,
                figsize=(14, 8),
                vlines=dict(
                    vlines=[entry_date, exit_date], 
                    linewidths=2, 
                    linestyle='--', 
                    colors=['#27AE60', '#E74C3C'],  # Green for entry, red for exit
                    alpha=0.7
                )
            )
            
            # Enhanced legend with background
            legend = axes[0].legend(
                loc='upper left', 
                fontsize=10,
                framealpha=0.9,
                edgecolor='gray',
                fancybox=True,
                shadow=True
            )
            
            # Add entry/exit annotations
            axes[0].text(0.02, 0.02, f'Entry ↑', transform=axes[0].transAxes, 
                        fontsize=9, color='#27AE60', weight='bold', 
                        bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.8))
            axes[0].text(0.12, 0.02, f'Exit ↓', transform=axes[0].transAxes, 
                        fontsize=9, color='#E74C3C', weight='bold',
                        bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.8))
            
            # Save with higher quality
            fig.savefig(filename, dpi=200, bbox_inches='tight', facecolor='white')
            plt.close(fig)
            
            logger.info(f"Chart saved to {filename}")
        except Exception as e:
            logger.error(f"Failed to plot trade for {ticker}: {e}")
