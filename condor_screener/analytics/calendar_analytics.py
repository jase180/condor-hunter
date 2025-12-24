"""Analytics for calendar spread strategies.

Calendar spreads profit from:
1. Time decay differential (theta)
2. Volatility expansion (vega)
3. Price staying near the strike

Key metrics:
- Return on Risk: max_profit / max_loss
- Theta differential: How much faster short leg decays
- Vega exposure: Benefit from IV increase
- Distance to strike: How far current price is from strike
"""

from dataclasses import dataclass
from ..builder.calendar_spreads import CalendarSpread


@dataclass(frozen=True)
class CalendarAnalytics:
    """Analytics for a calendar spread.

    Attributes:
        calendar: The calendar spread being analyzed
        composite_score: Overall score (0-1, higher is better)
        return_on_risk: Max profit / max loss ratio
        theta_differential: Short theta - long theta (higher is better)
        vega_exposure: Net vega (positive = benefits from IV increase)
        distance_to_strike_pct: Distance from current price to strike (%)
        breakeven_lower: Estimated lower breakeven
        breakeven_upper: Estimated upper breakeven
        probability_of_profit: Estimated PoP (simplified)
    """
    calendar: CalendarSpread
    composite_score: float
    return_on_risk: float
    theta_differential: float
    vega_exposure: float
    distance_to_strike_pct: float
    breakeven_lower: float
    breakeven_upper: float
    probability_of_profit: float


def analyze_calendar_spread(
    calendar: CalendarSpread,
    spot_price: float
) -> CalendarAnalytics:
    """Analyze a calendar spread.

    Args:
        calendar: CalendarSpread to analyze
        spot_price: Current price of underlying

    Returns:
        CalendarAnalytics with all metrics calculated

    Example:
        >>> analytics = analyze_calendar_spread(calendar, spot=560.0)
        >>> print(f"Score: {analytics.composite_score:.3f}")
        >>> print(f"RoR: {analytics.return_on_risk:.1%}")
    """
    short = calendar.short_leg
    long = calendar.long_leg
    strike = short.strike

    # Return on Risk
    ror = calendar.max_profit_estimate / calendar.max_loss if calendar.max_loss > 0 else 0

    # Theta differential (short decays faster = good)
    # Note: theta is negative, so more negative = faster decay
    theta_diff = abs(short.theta) - abs(long.theta)

    # Vega exposure (net long vega = good)
    # We're long the long leg, short the short leg
    vega_exposure = long.vega - short.vega

    # Distance to strike
    distance_to_strike_pct = abs(spot_price - strike) / spot_price

    # Breakeven estimates (very rough)
    # Calendar max profit typically occurs at the strike
    # Breakevens are roughly ±5-10% for ATM calendars
    breakeven_width_estimate = strike * 0.07  # 7% as rough estimate
    breakeven_lower = strike - breakeven_width_estimate
    breakeven_upper = strike + breakeven_width_estimate

    # Probability of Profit (simplified)
    # Calendars typically have ~55-65% PoP
    # Better if closer to strike, worse if further
    base_pop = 0.60
    distance_penalty = distance_to_strike_pct * 2  # Penalize if far from strike
    pop = max(0.3, min(0.75, base_pop - distance_penalty))

    # Composite Score (weighted)
    # For calendars, we care about:
    # - Return on risk (30%)
    # - Being close to strike (30%)
    # - Theta differential (20%)
    # - Vega exposure (20%)

    # Normalize RoR (0.4 = good, 0.6 = excellent)
    ror_score = min(1.0, ror / 0.6)

    # Distance score (0% = perfect, 5% = ok, 10%+ = bad)
    distance_score = max(0, 1.0 - (distance_to_strike_pct / 0.08))

    # Theta differential score (normalized to 0-1)
    # Typical theta diff for ATM calendar is 5-15
    theta_score = min(1.0, theta_diff / 15.0) if theta_diff > 0 else 0

    # Vega score (positive vega is good, normalized)
    # Typical net vega is 5-20 for calendar
    vega_score = min(1.0, vega_exposure / 20.0) if vega_exposure > 0 else 0

    composite_score = (
        ror_score * 0.30 +
        distance_score * 0.30 +
        theta_score * 0.20 +
        vega_score * 0.20
    )

    return CalendarAnalytics(
        calendar=calendar,
        composite_score=composite_score,
        return_on_risk=ror,
        theta_differential=theta_diff,
        vega_exposure=vega_exposure,
        distance_to_strike_pct=distance_to_strike_pct,
        breakeven_lower=breakeven_lower,
        breakeven_upper=breakeven_upper,
        probability_of_profit=pop
    )


def rank_calendar_analytics(
    analytics: list[CalendarAnalytics],
    max_results: int = 20
) -> list[CalendarAnalytics]:
    """Rank calendar spreads by composite score.

    Args:
        analytics: List of CalendarAnalytics
        max_results: Maximum number of results to return

    Returns:
        Sorted list of top candidates

    Example:
        >>> ranked = rank_calendar_analytics(analytics, max_results=10)
        >>> for i, a in enumerate(ranked):
        ...     print(f"#{i+1}: {a.calendar} - Score: {a.composite_score:.3f}")
    """
    sorted_analytics = sorted(
        analytics,
        key=lambda a: a.composite_score,
        reverse=True
    )
    return sorted_analytics[:max_results]
