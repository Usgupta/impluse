"""
Screener Package - Phase II: The Screener

Applies liquidity and trend filters to identify candidate stocks.
Per Technical Test Requirements:
- Liquidity Filter: Price >= $3.00 AND 50-day Avg Volume >= 300,000
- Trend Filter: Current Price must be above its 50-day SMA
"""

from .filters import Screener

__all__ = ['Screener']
