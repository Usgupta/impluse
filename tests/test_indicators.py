
import pytest
import pandas as pd
import numpy as np
from momentum_system.indicators import calculate_sma, calculate_atr, detect_consolidation, calculate_roc

@pytest.fixture
def sample_data():
    """Generates sample OHLC data."""
    dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
    # Simulate a trend up then consolidation
    close = np.linspace(100, 150, 60).tolist() + [145, 146, 144, 145, 147] * 8
    # Ensure length is 100
    close = close[:100]
    
    df = pd.DataFrame({
        "Close": close,
        "High": [c + 2 for c in close],
        "Low": [c - 2 for c in close],
        "Open": close, # Simplify
    }, index=dates)
    return df

def test_sma_calculation(sample_data):
    sma = calculate_sma(sample_data["Close"], window=10)
    assert not sma.empty
    assert np.isnan(sma.iloc[0]) # First values should be NaN
    assert not np.isnan(sma.iloc[10])
    
def test_atr_calculation(sample_data):
    atr = calculate_atr(sample_data["High"], sample_data["Low"], sample_data["Close"], window=14)
    assert not atr.empty
    # ATR should be positive roughly around (High-Low) which is 4 in our fixture (shifted)
    # Note: Our fixture has constant range High-Low=4, Gap=0.
    # So ATR should converge to 4.
    assert atr.iloc[-1] > 0

def test_detect_consolidation_logic():
    # Create synthetic data: 100 days
    # Days 0-50: Rising to peak 200
    # Days 50-80: Consolidating between 190 and 200 (within 5-10% tolerance)
    # Days 80+: Crashing
    
    dates = pd.date_range(start="2023-01-01", periods=100)
    close = np.concatenate([
        np.linspace(100, 200, 50),       # Rise
        np.random.uniform(190, 200, 30), # Consolidate
        np.linspace(190, 150, 20)        # Crash
    ])
    high = close + 1 # Simple high
    
    high_series = pd.Series(high, index=dates)
    close_series = pd.Series(close, index=dates)
    
    is_consolidating = detect_consolidation(
        high_series, 
        close_series, 
        lookback_peak=63, 
        min_days=4, 
        tolerance=0.10 # 10%
    )
    
    # Check middle period (approx index 60-70) should be True
    assert is_consolidating.iloc[60] == True
    
    # Check start (not enough history)
    assert is_consolidating.iloc[0] == False
    
    # Check end (crash > 10% from peak 200) -> 150 is 25% drop
    assert is_consolidating.iloc[-1] == False
