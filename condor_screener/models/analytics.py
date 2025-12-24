"""Analytics and scoring data model."""

from dataclasses import dataclass

from .iron_condor import IronCondor


@dataclass(frozen=True)
class Analytics:
    """Risk/reward and volatility metrics for an iron condor.

    All computed values stored as immutable fields to ensure consistency.
    """

    iron_condor: IronCondor

    # Underlying price (spot)
    spot_price: float

    # Expected move estimates
    expected_move_straddle: float  # From ATM straddle price
    expected_move_iv: float        # From IV * price * sqrt(DTE/365)

    # Distance metrics (how far short strikes are from expected move boundaries)
    put_distance_dollars: float    # Dollars below lower expected move boundary
    call_distance_dollars: float   # Dollars above upper expected move boundary
    put_distance_pct: float        # Percentage below current price
    call_distance_pct: float       # Percentage above current price

    # Volatility context
    iv_rank: float                 # IV rank (0–100)
    iv_percentile: float           # IV percentile (0–100)
    realized_vol_20d: float        # 20-day realized volatility
    iv_to_rv_ratio: float          # IV / realized vol

    # Flags
    is_pre_earnings: bool
    earnings_date: str | None      # ISO format date string or None

    # Liquidity score (composite of bid-ask, OI, volume)
    liquidity_score: float         # 0.0 to 1.0

    # Composite score (set by scorer)
    composite_score: float | None = None

    @property
    def within_expected_move(self) -> bool:
        """Check if either short strike is inside expected move range.

        Returns:
            True if risky (inside expected move), False if safe (outside)
        """
        lower_bound = self.spot_price - self.expected_move_straddle
        upper_bound = self.spot_price + self.expected_move_straddle

        put_inside = self.iron_condor.short_put.strike >= lower_bound
        call_inside = self.iron_condor.short_call.strike <= upper_bound

        return put_inside or call_inside

    @property
    def avg_distance_pct(self) -> float:
        """Average distance of short strikes from current price."""
        return (self.put_distance_pct + self.call_distance_pct) / 2.0

    @property
    def iv_edge(self) -> float:
        """How much IV exceeds realized volatility (premium edge).

        Returns:
            Difference in percentage points (e.g., 0.10 = 10 vol points)
        """
        return self.iv_to_rv_ratio - 1.0

    def __repr__(self) -> str:
        """Compact string representation."""
        score_str = f"{self.composite_score:.3f}" if self.composite_score is not None else "N/A"
        return (f"Analytics(ROR={self.iron_condor.return_on_risk:.1f}% "
                f"IVR={self.iv_rank:.0f} IV/RV={self.iv_to_rv_ratio:.2f} "
                f"Liq={self.liquidity_score:.2f} "
                f"Score={score_str})")
