
from .config import RISK_PARAMS
from .logger_setup import setup_logger

logger = setup_logger(name="RiskManager")

class RiskManager:
    """
    Enforces risk constraints and calculates position sizing.
    Differentiation: Swappable logic and strict ATR checks.
    """
    
    def __init__(self, account_size: float = 100000.0):
        self.account_size = account_size
        self.risk_per_trade_pct = RISK_PARAMS["RISK_PER_TRADE_PERCENT"]
        self.max_stop_atr_mult = RISK_PARAMS["STOP_LOSS_ATR_MULTIPLIER"]

    def validate_trade_setup(self, entry_price: float, stop_loss: float, atr: float, ticker: str = "") -> bool:
        """
        Validates if the trade meets the strict risk criteria.
        Rule: Stop Distance <= 1.0 * ATR
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
        Risk Amount = Account Size * Risk%
        Shares = Risk Amount / (Entry - Stop)
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
