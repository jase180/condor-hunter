"""Main analytics orchestrator.

Computes all analytics for iron condor candidates.
"""

from datetime import datetime, date
from typing import List, Tuple

from ..models.iron_condor import IronCondor
from ..models.analytics import Analytics
from ..data.validators import check_liquidity_quality
from .expected_move import calculate_expected_move
from .volatility import calculate_iv_rank, calculate_iv_percentile, calculate_realized_volatility


def analyze_iron_condor(
    iron_condor: IronCondor,
    spot_price: float,
    historical_ivs: List[float],
    realized_vol_20d: float,
    earnings_date: str | None = None,
    expected_move_method: str = "straddle",
) -> Analytics:
    """Compute full analytics for an iron condor.

    Args:
        iron_condor: IronCondor to analyze
        spot_price: Current underlying price
        historical_ivs: List of historical IVs for IV rank/percentile
        realized_vol_20d: 20-day realized volatility
        earnings_date: Optional earnings date (ISO format string)
        expected_move_method: "straddle", "iv", or "both"

    Returns:
        Analytics object with all computed metrics
    """
    # Get current IV (average of short strikes)
    current_iv = (iron_condor.short_put.implied_vol + iron_condor.short_call.implied_vol) / 2.0

    # Calculate IV rank and percentile
    iv_rank = calculate_iv_rank(current_iv, historical_ivs)
    iv_percentile = calculate_iv_percentile(current_iv, historical_ivs)

    # Calculate expected move
    # Use options from the iron condor for expected move calculation
    options = [
        iron_condor.short_put,
        iron_condor.long_put,
        iron_condor.short_call,
        iron_condor.long_call,
    ]
    em_straddle, em_iv = calculate_expected_move(
        options, spot_price, method=expected_move_method
    )

    # Calculate distance metrics
    put_distance_dollars = spot_price - iron_condor.short_put.strike
    call_distance_dollars = iron_condor.short_call.strike - spot_price

    put_distance_pct = (put_distance_dollars / spot_price) * 100
    call_distance_pct = (call_distance_dollars / spot_price) * 100

    # Calculate IV/RV ratio
    if realized_vol_20d > 0:
        iv_to_rv_ratio = current_iv / realized_vol_20d
    else:
        iv_to_rv_ratio = 1.0  # Neutral if no RV data

    # Check if pre-earnings
    is_pre_earnings = _is_pre_earnings(iron_condor.expiration, earnings_date)

    # Calculate liquidity score (average of all legs)
    liquidity_scores = [
        check_liquidity_quality(iron_condor.short_put),
        check_liquidity_quality(iron_condor.long_put),
        check_liquidity_quality(iron_condor.short_call),
        check_liquidity_quality(iron_condor.long_call),
    ]
    # Weight short legs more heavily (they're more important for execution)
    liquidity_score = (
        0.35 * liquidity_scores[0] +  # short put
        0.15 * liquidity_scores[1] +  # long put
        0.35 * liquidity_scores[2] +  # short call
        0.15 * liquidity_scores[3]    # long call
    )

    return Analytics(
        iron_condor=iron_condor,
        spot_price=spot_price,
        expected_move_straddle=em_straddle,
        expected_move_iv=em_iv,
        put_distance_dollars=put_distance_dollars,
        call_distance_dollars=call_distance_dollars,
        put_distance_pct=put_distance_pct,
        call_distance_pct=call_distance_pct,
        iv_rank=iv_rank,
        iv_percentile=iv_percentile,
        realized_vol_20d=realized_vol_20d,
        iv_to_rv_ratio=iv_to_rv_ratio,
        is_pre_earnings=is_pre_earnings,
        earnings_date=earnings_date,
        liquidity_score=liquidity_score,
    )


def _is_pre_earnings(expiration: date, earnings_date: str | None) -> bool:
    """Check if option expires before earnings announcement.

    Args:
        expiration: Option expiration date
        earnings_date: Earnings date as ISO format string (YYYY-MM-DD) or None

    Returns:
        True if earnings date is within 7 days after expiration
    """
    if earnings_date is None:
        return False

    try:
        earnings = datetime.strptime(earnings_date, '%Y-%m-%d').date()
    except ValueError:
        return False

    # Define "pre-earnings" as: earnings date is within 7 days after expiration
    # This captures selling premium before earnings IV crush
    days_until_earnings = (earnings - expiration).days
    return 0 <= days_until_earnings <= 7
