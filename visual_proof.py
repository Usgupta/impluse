
import pandas as pd
from momentum_system.common.config import UNIVERSE, BACKTEST_PARAMS
from momentum_system.common.data_loader import DataLoader
from momentum_system.backtester import VectorizedBacktester
from momentum_system.common.visualizer import TradeVisualizer
from momentum_system.common.logger_setup import setup_logger

logger = setup_logger("VisualProof")

def main():
    logger.info("Initializing System Demonstration...")
    
    # 1. Fetch Data
    loader = DataLoader()
    data_map = loader.fetch_data(
        tickers=UNIVERSE, 
        start_date=BACKTEST_PARAMS["START_DATE"], 
        end_date=BACKTEST_PARAMS["END_DATE"]
    )
    
    # 2. Run Backtest
    backtester = VectorizedBacktester()
    metrics, trades = backtester.run(data_map)
    
    # 3. Output Metrics
    print("\n" + "="*40)
    print("SYSTEM PERFORMANCE METRICS (Institutional)")
    print("="*40)
    if not metrics.empty:
        print(metrics.T)
    else:
        print("No trades generated.")
    print("="*40 + "\n")
    
    # 4. Generate Visual Proof (Best Trade)
    if not trades.empty:
        # Find best trade by PnL
        best_trade = trades.loc[trades['PnL'].idxmax()]
        ticker = best_trade['Ticker']
        
        logger.info(f"Generating visual proof for best trade: {ticker} on {best_trade['Entry Date']}")
        
        visualizer = TradeVisualizer()
        
        # We need the processed DF for that ticker to plot indicators
        # Re-running prepare_data is cheap
        df = backtester.strategy.prepare_data(data_map[ticker])
        
        visualizer.plot_trade(ticker, df, best_trade.to_dict())
        print(f"\n[Artifact Created] Visual proof chart saved to 'charts/' directory.")
    else:
        logger.warning("No trades to visualize.")

if __name__ == "__main__":
    main()
