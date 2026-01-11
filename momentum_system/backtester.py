
import polars as pl
import pandas as pd
import numpy as np
from typing import Dict, List
from .config import BACKTEST_PARAMS, RISK_PARAMS
from .logger_setup import setup_logger, measure_latency
from .risk_manager import RiskManager
from .strategy import MomentumStrategy

logger = setup_logger(name=__name__)

class VectorizedBacktester:
    """
    Orchestrates the backtest. 
    Uses vectorized signals from Strategy, but iterates dates 
    to manage Portfolio State (Cash, Positions) correctly.
    """
    
    def __init__(self, initial_capital: float = BACKTEST_PARAMS["INITIAL_CAPITAL"]):
        self.initial_capital = initial_capital
        self.risk_manager = RiskManager(account_size=initial_capital)
        self.strategy = MomentumStrategy()
        
    @measure_latency
    def run(self, data_map: Dict[str, pl.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Runs the backtest across the universe.
        Returns: (metrics_df, trade_log_df)
        """
        logger.info(f"Starting Backtest on {len(data_map)} tickers...")
        
        # 1. Prepare Data & Signals (Hybrid: Polars Calc -> Pandas Execution)
        processed_data = {}
        for ticker, df_polars in data_map.items():
            # Run Strategy in Polars (Fast)
            processed_polars = self.strategy.prepare_data(df_polars)
            
            # Convert to Pandas for iteration (Legacy Compatibility)
            # Ensure Date column becomes Index
            df_pandas = processed_polars.to_pandas()
            if 'Date' in df_pandas.columns:
                df_pandas['Date'] = pd.to_datetime(df_pandas['Date'])
                df_pandas.set_index('Date', inplace=True)
            
            processed_data[ticker] = df_pandas
            
        # 2. Portfolio Loop
        # We need a unified timeline
        all_dates = sorted(list(set().union(*[df.index for df in processed_data.values()])))
        
        cash = self.initial_capital
        positions = {} # {ticker: {'shares': int, 'entry_price': float, 'stop_loss': float}}
        trade_history = []
        equity_curve = []
        
        # Pre-convert to list of dicts for faster iteration if needed, 
        # but re-indexing is easier for alignment.
        # Ideally, we iterate day by day.
        
        for date in all_dates:
            # Update Equity
            current_equity = cash
            for t, pos in positions.items():
                if date in processed_data[t].index:
                    price = processed_data[t].loc[date, 'Close']
                    current_equity += pos['shares'] * price
                else:
                    # Use last known equity if data missing (gap)
                    # For simplicity, assume price didn't change (or handle gaps)
                    pass 
                    
            equity_curve.append({'Date': date, 'Equity': current_equity})
            self.risk_manager.account_size = current_equity # Dynamic compounding
            
            # --- Process Exits First ---
            # Exits: Stop Loss or Trailing Stop
            # We need to loop over specific tickers held
            cols_to_drop = []
            for ticker, pos in positions.items():
                if date not in processed_data[ticker].index:
                    continue
                    
                row = processed_data[ticker].loc[date]
                low = row['Low']
                high = row['High']
                close = row['Close']
                atr = row['ATR']
                
                # Check Stop Loss (Hit Low)
                if low <= pos['stop_loss']:
                    # Exited at Stop (Slippage modeled as execution at Stop Price)
                    exit_price = pos['stop_loss'] 
                    pnl = (exit_price - pos['entry_price']) * pos['shares']
                    cash += pos['shares'] * exit_price
                    
                    trade_history.append({
                        'Ticker': ticker,
                        'Entry Date': pos['entry_date'],
                        'Exit Date': date,
                        'Entry Price': pos['entry_price'],
                        'Exit Price': exit_price,
                        'Shares': pos['shares'],
                        'PnL': pnl,
                        'Return %': (exit_price / pos['entry_price']) - 1,
                        'Exit Reason': 'Stop Loss'
                    })
                    cols_to_drop.append(ticker)
                    continue
                    
                # Update Trailing Stop
                # Requirement: Exit entirely if price closes below 10-day SMA (or intraday breach?)
                # "Implement a simple Trailing Stop using the 10-day SMA to exit the entire position"
                # Usually means if Low < SMA_10 (intraday) or Close < SMA_10.
                # Let's assume Intraday Breach for safety (Low < SMA_10).
                # But since SMA_10 is dynamic, we can just check against the daily SMA_10.
                
                sma_10 = row['SMA_10']
                
                # Check Trailing Stop (Dynamic SMA 10)
                # If Low drops below SMA_10, we exit.
                # However, we must respect the hard initial stop too. 
                # Ideally, the Stop Price becomes max(Initial_Stop, SMA_10).
                
                # Update current effective stop
                if sma_10 > pos['stop_loss']:
                   pos['stop_loss'] = sma_10
            
            for t in cols_to_drop:
                del positions[t]
                
            # --- Process Entries ---
            for ticker, df in processed_data.items():
                if date not in df.index:
                    continue
                
                # Check for Signal
                # Note: 'Buy_Signal' is calculated based on Close.
                # In real backtest, we might buy on Close or Next Open.
                # Assuming Buy on Close for simplicity (Signal Day)
                
                row = df.loc[date]
                if row['Buy_Signal'] and ticker not in positions:
                    
                    # Define Risk-Based Stop
                    # Initial Stop = Low of Day (or Low of Setup) - Buffer?
                    # VCP Stop: Low of the breakout day is a common tight stop.
                    # Or Low of previous candle.
                    initial_stop = row['Low']
                    entry_price = row['Close']
                    atr = row['ATR']
                    
                    # Validate Risk
                    valid = self.risk_manager.validate_trade_setup(entry_price, initial_stop, atr, ticker)
                    if valid:
                        shares = self.risk_manager.calculate_position_size(entry_price, initial_stop)
                        cost = shares * entry_price
                        
                        if shares > 0 and cash >= cost:
                            cash -= cost
                            positions[ticker] = {
                                'shares': shares,
                                'entry_price': entry_price,
                                'stop_loss': initial_stop,
                                'entry_date': date
                            }
                            logger.debug(f"BUY {ticker} at {entry_price} on {date}")
        
        # End of Loop
        trades_df = pd.DataFrame(trade_history)
        equity_df = pd.DataFrame(equity_curve).set_index('Date')
        
        metrics = self._calculate_metrics(equity_df, trades_df)
        return metrics, trades_df
        
    def _calculate_metrics(self, equity_df: pd.DataFrame, trades_df: pd.DataFrame) -> pd.DataFrame:
        """ Calculates Shape, Sortino, Calmar, MaxDD. """
        if equity_df.empty:
            return pd.DataFrame()
            
        equity_df['Returns'] = equity_df['Equity'].pct_change()
        
        total_return = (equity_df['Equity'].iloc[-1] / self.initial_capital) - 1
        cagr = ((1 + total_return) ** (252 / len(equity_df))) - 1
        
        # Max Drawdown
        rolling_max = equity_df['Equity'].cummax()
        drawdown = (equity_df['Equity'] - rolling_max) / rolling_max
        max_dd = drawdown.min()
        
        # Sharpe
        risk_free_rate = 0.04 # 4% assumption
        excess_returns = equity_df['Returns'] - (risk_free_rate/252)
        sharpe = np.sqrt(252) * (excess_returns.mean() / excess_returns.std())
        
        # Sortino (Downside deviation)
        downside_returns = excess_returns[excess_returns < 0]
        sortino = np.sqrt(252) * (excess_returns.mean() / downside_returns.std())
        
        # Calmar
        calmar = cagr / abs(max_dd) if max_dd != 0 else 0
        
        stats = {
            "Total Return": f"{total_return:.2%}",
            "CAGR": f"{cagr:.2%}",
            "Max Drawdown": f"{max_dd:.2%}",
            "Sharpe Ratio": f"{sharpe:.2f}",
            "Sortino Ratio": f"{sortino:.2f}",
            "Calmar Ratio": f"{calmar:.2f}",
            "Total Trades": len(trades_df),
            "Win Rate": f"{len(trades_df[trades_df['PnL']>0]) / len(trades_df):.2%}" if not trades_df.empty else "0%"
        }
        
        return pd.DataFrame([stats])
