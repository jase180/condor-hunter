"""Iron Condor spread data model."""

from dataclasses import dataclass
from datetime import date

from .option import Option


@dataclass(frozen=True)
class IronCondor:
    """Represents a complete iron condor position.

    Structure:
        - Bull put spread (short put + long put below it)
        - Bear call spread (short call + long call above it)

    Convention:
        - All legs same expiration
        - Short strikes closer to ATM, long strikes further OTM
        - Net credit trade (receive premium upfront)
    """

    ticker: str
    expiration: date

    # Put side (bull put spread)
    short_put: Option
    long_put: Option

    # Call side (bear call spread)
    short_call: Option
    long_call: Option

    def __post_init__(self) -> None:
        """Validate iron condor structure."""
        # All options same ticker and expiration
        if not all(leg.ticker == self.ticker for leg in [self.short_put, self.long_put, self.short_call, self.long_call]):
            raise ValueError("All legs must have same ticker")
        if not all(leg.expiration == self.expiration for leg in [self.short_put, self.long_put, self.short_call, self.long_call]):
            raise ValueError("All legs must have same expiration")

        # Validate put side
        if self.short_put.option_type != "put" or self.long_put.option_type != "put":
            raise ValueError("Put side must contain put options")
        if self.short_put.strike <= self.long_put.strike:
            raise ValueError("Short put strike must be above long put strike")

        # Validate call side
        if self.short_call.option_type != "call" or self.long_call.option_type != "call":
            raise ValueError("Call side must contain call options")
        if self.short_call.strike >= self.long_call.strike:
            raise ValueError("Short call strike must be below long call strike")

        # Validate no overlap (short call should be above short put)
        if self.short_call.strike <= self.short_put.strike:
            raise ValueError("Short call strike must be above short put strike")

    @property
    def net_credit(self) -> float:
        """Total premium collected (before commissions).

        Returns:
            Net credit in dollars (positive value)
        """
        put_spread_credit = self.short_put.mid - self.long_put.mid
        call_spread_credit = self.short_call.mid - self.long_call.mid
        return put_spread_credit + call_spread_credit

    @property
    def max_profit(self) -> float:
        """Maximum profit if price stays between short strikes.

        Returns:
            Max profit in dollars (equals net credit)
        """
        return self.net_credit

    @property
    def put_side_width(self) -> float:
        """Width of put spread in dollars."""
        return self.short_put.strike - self.long_put.strike

    @property
    def call_side_width(self) -> float:
        """Width of call spread in dollars."""
        return self.long_call.strike - self.short_call.strike

    @property
    def max_loss_put_side(self) -> float:
        """Max loss if price falls below long put.

        Returns:
            Max loss in dollars (positive value)
        """
        return self.put_side_width - self.net_credit

    @property
    def max_loss_call_side(self) -> float:
        """Max loss if price rises above long call.

        Returns:
            Max loss in dollars (positive value)
        """
        return self.call_side_width - self.net_credit

    @property
    def max_loss(self) -> float:
        """Worst-case loss (larger of the two sides).

        Returns:
            Max loss in dollars (positive value)
        """
        return max(self.max_loss_put_side, self.max_loss_call_side)

    @property
    def return_on_risk(self) -> float:
        """Return on risk as a percentage.

        ROR = (max_profit / max_loss) * 100

        Returns:
            ROR percentage (e.g., 25.0 = 25%)
        """
        if self.max_loss <= 0:
            return 0.0
        return (self.max_profit / self.max_loss) * 100

    @property
    def put_side_breakeven(self) -> float:
        """Downside breakeven price at expiration."""
        return self.short_put.strike - self.net_credit

    @property
    def call_side_breakeven(self) -> float:
        """Upside breakeven price at expiration."""
        return self.short_call.strike + self.net_credit

    @property
    def is_symmetric(self) -> bool:
        """Check if put and call wing widths are equal."""
        return abs(self.put_side_width - self.call_side_width) < 0.01

    def __repr__(self) -> str:
        """Compact string representation."""
        return (f"IronCondor({self.ticker} {self.expiration.strftime('%Y-%m-%d')} "
                f"P[{self.long_put.strike:.0f}/{self.short_put.strike:.0f}] "
                f"C[{self.short_call.strike:.0f}/{self.long_call.strike:.0f}] "
                f"Credit=${self.net_credit:.2f} ROR={self.return_on_risk:.1f}%)")
