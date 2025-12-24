"""Core Option data model."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal


@dataclass(frozen=True)
class Option:
    """Represents a single option contract.

    Immutable dataclass to prevent accidental mutations during processing.
    All monetary values in dollars, greeks in standard units, IV as decimal (0.25 = 25%).
    """

    ticker: str
    strike: float
    expiration: date
    option_type: Literal["call", "put"]

    # Market data
    bid: float
    ask: float
    volume: int
    open_interest: int

    # Greeks (delta required)
    delta: float

    # Volatility (required)
    implied_vol: float

    # Optional fields
    last: float | None = None
    gamma: float | None = None
    theta: float | None = None
    vega: float | None = None

    @property
    def mid(self) -> float:
        """Mid price between bid and ask."""
        return (self.bid + self.ask) / 2.0

    @property
    def bid_ask_spread_pct(self) -> float:
        """Bid-ask spread as percentage of mid price.

        Returns:
            Percentage (0.10 = 10%), or infinity if mid is zero
        """
        if self.mid <= 0:
            return float('inf')
        return (self.ask - self.bid) / self.mid

    @property
    def dte(self) -> int:
        """Days to expiration from today."""
        return (self.expiration - date.today()).days

    def __repr__(self) -> str:
        """Compact string representation for debugging."""
        return (f"Option({self.ticker} {self.strike:.0f}{self.option_type[0].upper()} "
                f"{self.expiration.strftime('%Y-%m-%d')} Δ={self.delta:.3f} IV={self.implied_vol:.2%})")
