
from ..common.config import RISK_PARAMS
from ..common.logger_setup import setup_logger

logger = setup_logger(name="Executor")

class Executor:
    """
    Phase IV: The Executor
    Handles risk management, position sizing, and trade execution logic.
    
    Per Technical Test Requirements:
    - Risk Management: Fixed Risk - Limit 2% of account equity per trade
    - Stop Loss Placement: LOD of trigger candle, constraint: (Entry - Stop) <= 1.0 × ATR(14)
    - Exit Logic: Trailing Stop using 10-day SMA
    """
    
    def __init__(self, account_size: float = 100000.0):
        self.account_size = account_size
        self.risk_per_trade_pct = RISK_PARAMS["RISK_PER_TRADE_PERCENT"]
        self.max_stop_atr_mult = RISK_PARAMS["STOP_LOSS_ATR_MULTIPLIER"]

    def validate_trade_setup(self, entry_price: float, stop_loss: float, atr: float, ticker: str = "") -> bool:
        """
        Validates if the trade meets the strict risk criteria.
        Rule: Stop Distance <= 1.0 × ATR
        
        Args:
            entry_price: Proposed entry price
            stop_loss: Proposed stop loss price (LOD of signal candle)
            atr: Current ATR(14) value
            ticker: Stock ticker for logging
            
        Returns:
            True if trade setup is valid, False otherwise
        """
        if entry_price <= 0 or stop_loss <= 0 or atr <= 0:
            logger.warning(f"Invalid inputs for {ticker}: Entry={entry_price}, Stop={stop_loss}, ATR={atr}")
            return False

        if stop_loss >= entry_price:
            logger.warning(f"Stop loss {stop_loss} must be below entry {entry_price} for long trade.")
            return False

        stop_distance = entry_price - stop_loss
        max_allowed_distance = atr * self.max_stop_atr_mult
        
        if stop_distance > max_allowed_distance:
            logger.info(
                f"REJECT {ticker}: Stop Distance ({stop_distance:.2f}) > "
                f"{self.max_stop_atr_mult}x ATR ({max_allowed_distance:.2f}). "
                "Too volatile/loose."
            )
            return False
            
        return True

    def calculate_position_size(self, entry_price: float, stop_loss: float) -> int:
        """
        Calculates number of shares based on Fixed Fractional Risk.
        Risk Amount = Account Size × Risk%
        Shares = Risk Amount / (Entry - Stop)
        
        Args:
            entry_price: Entry price per share
            stop_loss: Stop loss price per share
            
        Returns:
            Number of shares to purchase
        """
        risk_amount = self.account_size * self.risk_per_trade_pct
        risk_per_share = entry_price - stop_loss
        
        if risk_per_share <= 0:
            return 0
            
        shares = int(risk_amount / risk_per_share)
        
        # Additional safeguards if needed (e.g. max 20% of equity in one stock)
        # cost = shares * entry_price
        # if cost > self.account_size * 0.25:
        #    shares = int((self.account_size * 0.25) / entry_price)
        
        return shares

    def check_exit_signal(self, current_price: float, sma_10: float) -> bool:
        """
        Checks if exit condition is met (Trailing Stop).
        Exit Rule: Close price falls below 10-day SMA
        
        Args:
            current_price: Current closing price
            sma_10: 10-day Simple Moving Average
            
        Returns:
            True if should exit, False otherwise
        """
        if sma_10 <= 0:
            return False
            
        return current_price < sma_10
