
import os
from pathlib import Path

# --- Project Paths ---
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_CACHE_DIR = BASE_DIR / "data_cache"
LOG_DIR = BASE_DIR / "logs"

# Ensure directories exist
os.makedirs(DATA_CACHE_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# --- Universe ---
# Selected high-momentum large cap tech & growth stocks for demonstration
UNIVERSE = [
    "NVDA", "TSLA", "META", "AMD", "AMZN", "MSFT", "GOOGL", 
    "PLTR", "COIN", "MSTR", "SMCI", "ARM"
]

# --- Risk Management ---
RISK_PARAMS = {
    "RISK_PER_TRADE_PERCENT": 0.01,       # 1% equity risk per trade
    "MAX_ACCOUNT_RISK_PERCENT": 0.06,     # Max 6% total open risk (e.g., 6 trades)
    "STOP_LOSS_ATR_MULTIPLIER": 1.0,      # Strict VCP requirement (Low of Day / 1 ATR)
    "TRAILING_STOP_ATR_MULTIPLIER": 3.0,  # Let winners run
    "MIN_STOP_DISTANCE_PERCENT": 0.02,    # Minimum 2% stop to avoid noise
    "MAX_STOP_DISTANCE_PERCENT": 0.10,    # Max 10% stop (Rule of thumb: never risk more than 10-12%)
}

# --- Strategy Parameters (Minervini / High Tight Flag) ---
STRATEGY_PARAMS = {
    # Trend Template
    "SMA_FAST": 50,
    "SMA_MEDIUM": 150,
    "SMA_SLOW": 200,
    "RS_LOOKBACK": 63,                   # ~1 Quarter Relative Strength
    
    # High Tight Flag / VCP
    "LOOKBACK_PEAK": 63,                 # Look for peak in last 63 days
    "CONSOLIDATION_MIN_DAYS": 4,         # "Stabilized for 4..."
    "CONSOLIDATION_MAX_DAYS": 40,        # "...to 40 days"
    "CONSOLIDATION_TOLERANCE": 0.15,     # Tighter consolidation (15% depth) for Tread
    "VOLUME_SMA": 50,
}

# --- Backtest Configuration ---
BACKTEST_PARAMS = {
    "START_DATE": "2020-01-01",
    "END_DATE": "2024-01-01",
    "INITIAL_CAPITAL": 100000.0,
    "COMMISSION_RATE": 0.0005,           # 0.05% per trade (approx institutional rate)
}
