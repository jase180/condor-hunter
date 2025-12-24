"""Calendar spread strategy builder.

A calendar spread (time spread) involves:
- Selling a near-term option
- Buying a longer-term option
- Same strike price
- Same option type (both calls or both puts)

Example:
    Sell: SPY Jan 560 Call (30 DTE)
    Buy:  SPY Feb 560 Call (60 DTE)

The goal is to profit from time decay, where the near-term option
decays faster than the long-term option.
"""

from dataclasses import dataclass
from typing import Iterator
from ..models.option import Option


@dataclass(frozen=True)
class CalendarSpread:
    """Calendar spread position.

    Attributes:
        short_leg: Near-term option (sold)
        long_leg: Far-term option (bought)
        net_debit: Total cost to enter position (debit paid)
        max_profit_estimate: Estimated max profit (approximate)
        max_loss: Maximum loss (net debit paid)
    """
    short_leg: Option
    long_leg: Option
    net_debit: float
    max_profit_estimate: float
    max_loss: float

    def __str__(self) -> str:
        """Human-readable representation."""
        opt_type = self.short_leg.option_type.upper()
        return (
            f"{opt_type} Calendar: "
            f"Sell {self.short_leg.expiration} {self.short_leg.strike} / "
            f"Buy {self.long_leg.expiration} {self.long_leg.strike} "
            f"for ${self.net_debit:.2f} debit"
        )


@dataclass(frozen=True)
class CalendarConfig:
    """Configuration for calendar spread generation.

    Attributes:
        min_short_dte: Minimum days to expiration for short leg
        max_short_dte: Maximum days to expiration for short leg
        min_long_dte: Minimum days to expiration for long leg
        min_dte_gap: Minimum days between expirations (e.g., 20 days)
        max_dte_gap: Maximum days between expirations (e.g., 45 days)
        target_delta: Target delta for both legs (typically 0.50 for ATM)
        delta_tolerance: Acceptable delta deviation
        option_type: 'call' or 'put' (or 'both' to generate both)
    """
    min_short_dte: int = 20
    max_short_dte: int = 35
    min_long_dte: int = 40
    min_dte_gap: int = 20
    max_dte_gap: int = 45
    target_delta: float = 0.50  # ATM calendars are most common
    delta_tolerance: float = 0.10
    option_type: str = 'call'  # 'call', 'put', or 'both'


def calculate_calendar_metrics(short: Option, long: Option) -> tuple[float, float, float]:
    """Calculate calendar spread metrics.

    Args:
        short: Short leg option (near-term, sold)
        long: Long leg option (far-term, bought)

    Returns:
        Tuple of (net_debit, max_profit_estimate, max_loss)

    Note:
        Max profit for calendars is hard to calculate precisely without
        modeling the future price of the long leg at short leg expiration.
        We use a simple estimate: 50% of the debit paid is typical for
        ATM calendars at ideal expiration.
    """
    # Net debit = pay for long leg - receive for short leg
    short_credit = (short.bid + short.ask) / 2
    long_debit = (long.bid + long.ask) / 2
    net_debit = long_debit - short_credit

    # Max loss = net debit paid (if underlying moves far from strike)
    max_loss = net_debit

    # Max profit estimate (simplified):
    # At short expiration, if stock is exactly at strike:
    # - Short leg expires worthless
    # - Long leg retains most of its time value
    # Rough estimate: 40-60% return on debit is realistic
    max_profit_estimate = net_debit * 0.50

    return net_debit, max_profit_estimate, max_loss


def generate_calendar_spreads(
    options: list[Option],
    config: CalendarConfig
) -> Iterator[CalendarSpread]:
    """Generate calendar spread candidates.

    Args:
        options: List of filtered options
        config: Calendar spread configuration

    Yields:
        CalendarSpread candidates that meet criteria

    Example:
        >>> options = load_options_from_csv("SPY_options.csv")
        >>> config = CalendarConfig(min_short_dte=25, max_short_dte=35)
        >>> calendars = list(generate_calendar_spreads(options, config))
    """
    # Determine which option types to generate
    if config.option_type == 'both':
        types_to_generate = ['call', 'put']
    else:
        types_to_generate = [config.option_type]

    for opt_type in types_to_generate:
        # Filter by option type
        typed_options = [o for o in options if o.option_type == opt_type]

        # Group by strike
        strikes = {}
        for opt in typed_options:
            if opt.strike not in strikes:
                strikes[opt.strike] = []
            strikes[opt.strike].append(opt)

        # For each strike, find calendar spread opportunities
        for strike, opts in strikes.items():
            # Separate short-term and long-term options
            short_candidates = [
                o for o in opts
                if config.min_short_dte <= o.dte <= config.max_short_dte
            ]
            long_candidates = [
                o for o in opts
                if o.dte >= config.min_long_dte
            ]

            # Try all combinations
            for short_opt in short_candidates:
                for long_opt in long_candidates:
                    # Validate DTE gap
                    dte_gap = long_opt.dte - short_opt.dte
                    if not (config.min_dte_gap <= dte_gap <= config.max_dte_gap):
                        continue

                    # Validate deltas (both should be near target)
                    if abs(short_opt.delta) < 0.01 or abs(long_opt.delta) < 0.01:
                        continue  # Skip if Greeks missing

                    short_delta_dist = abs(abs(short_opt.delta) - config.target_delta)
                    long_delta_dist = abs(abs(long_opt.delta) - config.target_delta)

                    if short_delta_dist > config.delta_tolerance:
                        continue
                    if long_delta_dist > config.delta_tolerance:
                        continue

                    # Calculate metrics
                    net_debit, max_profit, max_loss = calculate_calendar_metrics(
                        short_opt, long_opt
                    )

                    # Skip if debit is negative (shouldn't happen but be safe)
                    if net_debit <= 0:
                        continue

                    # Skip if no real credit in short leg
                    if short_opt.bid <= 0:
                        continue

                    yield CalendarSpread(
                        short_leg=short_opt,
                        long_leg=long_opt,
                        net_debit=net_debit,
                        max_profit_estimate=max_profit,
                        max_loss=max_loss
                    )
