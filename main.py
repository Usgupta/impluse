
import pandas as pd
from momentum_system.config import UNIVERSE, BACKTEST_PARAMS
from momentum_system.data_loader import DataLoader
from momentum_system.backtester import VectorizedBacktester
from momentum_system.visualizer import TradeVisualizer
from momentum_system.logger_setup import setup_logger

logger = setup_logger("Main")

def main():
    logger.info("Initializing System Backtest...")
    
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
    
    # 4. Save Trades to CSV
    if not trades.empty:
        trades.to_csv("trades_log.csv", index=False)
        print("Trades saved to trades_log.csv")
    
    # 5. Visual Proof (Optional)
    # visualizer = TradeVisualizer()
    # ... logic here if needed, but keeping main simple ...

if __name__ == "__main__":
    main()

