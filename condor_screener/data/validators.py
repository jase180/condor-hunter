"""Hard filter validators for option screening.

These filters are applied before strategy construction to reject unsuitable options.
Any option that fails these filters is excluded from candidate generation.
"""

import logging
from typing import List, Dict, Any

from ..models.option import Option

logger = logging.getLogger("condor_screener.validators")


class FilterConfig:
    """Configuration for hard filters."""

    def __init__(
        self,
        min_iv_rank: float = 40.0,
        min_iv_percentile: float = 40.0,
        max_bid_ask_spread_pct: float = 0.15,
        min_open_interest: int = 500,
        min_volume: int = 1,
        max_loss_cap: float | None = None,
    ):
        """Initialize filter configuration.

        Args:
            min_iv_rank: Minimum IV rank (0-100)
            min_iv_percentile: Minimum IV percentile (0-100)
            max_bid_ask_spread_pct: Max bid-ask spread as % of mid (0.15 = 15%)
            min_open_interest: Minimum open interest
            min_volume: Minimum volume
            max_loss_cap: Optional maximum loss cap (applied to iron condors, not options)
        """
        self.min_iv_rank = min_iv_rank
        self.min_iv_percentile = min_iv_percentile
        self.max_bid_ask_spread_pct = max_bid_ask_spread_pct
        self.min_open_interest = min_open_interest
        self.min_volume = min_volume
        self.max_loss_cap = max_loss_cap

    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> "FilterConfig":
        """Create FilterConfig from dictionary (e.g., from YAML).

        Args:
            config: Dictionary with filter parameters

        Returns:
            FilterConfig instance
        """
        return cls(
            min_iv_rank=config.get('min_iv_rank', 40.0),
            min_iv_percentile=config.get('min_iv_percentile', 40.0),
            max_bid_ask_spread_pct=config.get('max_bid_ask_spread_pct', 0.15),
            min_open_interest=config.get('min_open_interest', 500),
            min_volume=config.get('min_volume', 1),
            max_loss_cap=config.get('max_loss_cap'),
        )


def filter_options(
    options: List[Option],
    iv_rank: float,
    iv_percentile: float,
    config: FilterConfig,
) -> List[Option]:
    """Apply hard filters to option list.

    Args:
        options: List of Option objects to filter
        iv_rank: Current IV rank for the underlying
        iv_percentile: Current IV percentile for the underlying
        config: FilterConfig with filter thresholds

    Returns:
        Filtered list of Option objects

    Note:
        Prints rejection statistics for transparency.
    """
    initial_count = len(options)

    # Check IV rank/percentile (applies to entire chain, not individual options)
    if iv_rank < config.min_iv_rank:
        logger.warning(
            "IV Rank %.1f below minimum threshold %.1f - rejecting entire chain",
            iv_rank, config.min_iv_rank
        )
        return []

    if iv_percentile < config.min_iv_percentile:
        logger.warning(
            "IV Percentile %.1f below minimum threshold %.1f - rejecting entire chain",
            iv_percentile, config.min_iv_percentile
        )
        return []

    # Filter individual options
    filtered = []
    reject_reasons: Dict[str, int] = {}

    for option in options:
        # Check bid-ask spread
        if option.bid_ask_spread_pct > config.max_bid_ask_spread_pct:
            reject_reasons['wide_spread'] = reject_reasons.get('wide_spread', 0) + 1
            continue

        # Check open interest
        if option.open_interest < config.min_open_interest:
            reject_reasons['low_oi'] = reject_reasons.get('low_oi', 0) + 1
            continue

        # Check volume
        if option.volume < config.min_volume:
            reject_reasons['no_volume'] = reject_reasons.get('no_volume', 0) + 1
            continue

        # Passed all filters
        filtered.append(option)

    # Log statistics
    logger.info(
        "Filter results: %d/%d options passed",
        len(filtered), initial_count
    )
    if reject_reasons:
        reasons = [f"{count} ({reason})" for reason, count in reject_reasons.items()]
        logger.debug("Rejected: %s", ", ".join(reasons))

    return filtered


def check_liquidity_quality(option: Option) -> float:
    """Compute liquidity score for an option.

    Combines bid-ask spread, open interest, and volume into a single score.

    Args:
        option: Option to evaluate

    Returns:
        Liquidity score between 0.0 (illiquid) and 1.0 (highly liquid)

    Scoring logic:
        - Bid-ask spread: narrower is better
        - Open interest: higher is better (capped at 5000)
        - Volume: higher is better (capped at 1000)
    """
    # Spread component (0 = wide, 1 = tight)
    # Perfect spread = 0%, worst acceptable = 15%
    spread_score = max(0.0, 1.0 - (option.bid_ask_spread_pct / 0.15))

    # OI component (0 = low, 1 = high)
    # Cap at 5000 OI = perfect score
    oi_score = min(1.0, option.open_interest / 5000)

    # Volume component (0 = no volume, 1 = high volume)
    # Cap at 1000 volume = perfect score
    volume_score = min(1.0, option.volume / 1000)

    # Weighted average (spread is most important for execution)
    liquidity_score = (
        0.5 * spread_score +
        0.3 * oi_score +
        0.2 * volume_score
    )

    return liquidity_score
