"""
Signaller Package - Phase III: The Signaller

Detects momentum setups (Riser + Tread) and generates entry signals.
Per Technical Test Requirements:
- The Riser (Impulse): Price increased >= 30% in recent 63 trading days
- The Tread (Consolidation): Stabilized for 4-40 days, < 25% retracement
- Entry Trigger: BUY when price breaks above consolidation high (Pivot)
"""

from .signals import Signaller

__all__ = ['Signaller']
