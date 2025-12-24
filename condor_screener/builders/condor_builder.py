"""Iron condor strategy builder.

Generates iron condor candidates from filtered option chains using lazy evaluation.
"""

from collections import defaultdict
from datetime import date
from typing import Iterator, List, Dict

from ..models.option import Option
from ..models.iron_condor import IronCondor


class StrategyConfig:
    """Configuration for iron condor strategy constraints."""

    def __init__(
        self,
        min_dte: int = 30,
        max_dte: int = 45,
        min_delta: float = 0.15,
        max_delta: float = 0.25,
        wing_width_put: float = 5.0,
        wing_width_call: float = 5.0,
        allow_asymmetric: bool = True,
    ):
        """Initialize strategy configuration.

        Args:
            min_dte: Minimum days to expiration
            max_dte: Maximum days to expiration
            min_delta: Minimum absolute delta for short legs
            max_delta: Maximum absolute delta for short legs
            wing_width_put: Put side wing width in dollars
            wing_width_call: Call side wing width in dollars
            allow_asymmetric: Allow different wing widths for puts and calls
        """
        self.min_dte = min_dte
        self.max_dte = max_dte
        self.min_delta = min_delta
        self.max_delta = max_delta
        self.wing_width_put = wing_width_put
        self.wing_width_call = wing_width_call
        self.allow_asymmetric = allow_asymmetric

    @classmethod
    def from_dict(cls, config: Dict) -> "StrategyConfig":
        """Create StrategyConfig from dictionary (e.g., from YAML).

        Args:
            config: Dictionary with strategy parameters

        Returns:
            StrategyConfig instance
        """
        return cls(
            min_dte=config.get('min_dte', 30),
            max_dte=config.get('max_dte', 45),
            min_delta=config.get('min_delta', 0.15),
            max_delta=config.get('max_delta', 0.25),
            wing_width_put=config.get('wing_width_put', 5.0),
            wing_width_call=config.get('wing_width_call', 5.0),
            allow_asymmetric=config.get('allow_asymmetric', True),
        )


def generate_iron_condors(
    options: List[Option],
    config: StrategyConfig,
) -> Iterator[IronCondor]:
    """Generate all valid iron condor candidates from an option chain.

    Uses lazy evaluation (generator) to avoid materializing all combinations.

    Args:
        options: Filtered option chain (already passed hard gates)
        config: StrategyConfig with strategy constraints

    Yields:
        IronCondor objects that satisfy strategy constraints

    Design notes:
        - Groups options by expiration for efficiency
        - Finds matching strikes using tolerance-based lookup
        - Validates structure before yielding (credit > 0, no arbitrage)
    """
    # Filter by DTE
    valid_options = [opt for opt in options if config.min_dte <= opt.dte <= config.max_dte]

    if not valid_options:
        return

    # Group by expiration
    by_expiration = _group_by_expiration(valid_options)

    # Generate condors for each expiration
    for exp_date, exp_options in by_expiration.items():
        yield from _generate_condors_for_expiration(exp_options, exp_date, config)


def _generate_condors_for_expiration(
    options: List[Option],
    expiration: date,
    config: StrategyConfig,
) -> Iterator[IronCondor]:
    """Generate condors for a single expiration date.

    Args:
        options: Options with same expiration
        expiration: Expiration date
        config: Strategy configuration

    Yields:
        Valid IronCondor objects
    """
    # Separate puts and calls
    puts = [opt for opt in options if opt.option_type == "put"]
    calls = [opt for opt in options if opt.option_type == "call"]

    if not puts or not calls:
        return

    # Index options by strike for fast lookup
    puts_by_strike = {opt.strike: opt for opt in puts}
    calls_by_strike = {opt.strike: opt for opt in calls}

    # Find short put candidates (delta between -max_delta and -min_delta)
    short_puts = [p for p in puts if -config.max_delta <= p.delta <= -config.min_delta]

    # Find short call candidates (delta between +min_delta and +max_delta)
    short_calls = [c for c in calls if config.min_delta <= c.delta <= config.max_delta]

    # Generate all combinations
    for short_put in short_puts:
        # Find corresponding long put
        long_put_strike = short_put.strike - config.wing_width_put
        long_put = _find_strike(puts_by_strike, long_put_strike, tolerance=0.5)

        if not long_put:
            continue

        for short_call in short_calls:
            # Find corresponding long call
            long_call_strike = short_call.strike + config.wing_width_call
            long_call = _find_strike(calls_by_strike, long_call_strike, tolerance=0.5)

            if not long_call:
                continue

            # Construct iron condor
            try:
                ic = IronCondor(
                    ticker=short_put.ticker,
                    expiration=expiration,
                    short_put=short_put,
                    long_put=long_put,
                    short_call=short_call,
                    long_call=long_call,
                )

                # Validate structure
                if _is_valid_condor(ic):
                    yield ic

            except ValueError:
                # Invalid structure (e.g., overlapping strikes)
                continue


def _group_by_expiration(options: List[Option]) -> Dict[date, List[Option]]:
    """Group options by expiration date.

    Args:
        options: List of options

    Returns:
        Dictionary mapping expiration date to list of options
    """
    by_exp: Dict[date, List[Option]] = defaultdict(list)
    for opt in options:
        by_exp[opt.expiration].append(opt)
    return dict(by_exp)


def _find_strike(
    strikes_dict: Dict[float, Option],
    target_strike: float,
    tolerance: float = 0.5,
) -> Option | None:
    """Find option with strike close to target.

    Args:
        strikes_dict: Dictionary mapping strike to Option
        target_strike: Target strike price
        tolerance: Maximum allowed difference

    Returns:
        Option if found within tolerance, else None
    """
    # Exact match
    if target_strike in strikes_dict:
        return strikes_dict[target_strike]

    # Find closest strike within tolerance
    for strike, option in strikes_dict.items():
        if abs(strike - target_strike) <= tolerance:
            return option

    return None


def _is_valid_condor(ic: IronCondor) -> bool:
    """Validate iron condor structure.

    Args:
        ic: IronCondor to validate

    Returns:
        True if valid, False otherwise

    Validation checks:
        - Net credit > 0 (credit spread)
        - Max loss > 0 (no arbitrage)
        - Max profit < wing width (no arbitrage)
    """
    # Must collect credit
    if ic.net_credit <= 0:
        return False

    # Must have risk (no free lunch)
    if ic.max_loss <= 0:
        return False

    # Max profit can't exceed wing width (arbitrage check)
    # This can happen if spreads are mispriced
    if ic.max_profit >= ic.put_side_width or ic.max_profit >= ic.call_side_width:
        return False

    return True
