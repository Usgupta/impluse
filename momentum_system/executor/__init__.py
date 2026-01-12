"""
Executor Package - Phase IV: The Executor

Handles risk management, position sizing, and trade execution logic.
Per Technical Test Requirements:
- Risk Management: Fixed Risk - Limit 2% of account equity per trade
- Stop Loss Placement: LOD of trigger candle, constraint: (Entry - Stop) <= 1.0 × ATR(14)
- Exit Logic: Trailing Stop using 10-day SMA
"""

from .risk import Executor

__all__ = ['Executor']
