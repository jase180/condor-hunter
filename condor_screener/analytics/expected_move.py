"""Expected move calculations for options.

Provides two methods for estimating expected move (1 standard deviation):
1. Market-implied (from ATM straddle price)
2. Theoretical (from implied volatility)
"""

import math
from typing import List

from ..models.option import Option


def expected_move_from_straddle(
    atm_call: Option,
    atm_put: Option,
    discount_factor: float = 0.85,
) -> float:
    """Estimate expected move from ATM straddle price.

    Args:
        atm_call: At-the-money call option
        atm_put: At-the-money put option
        discount_factor: Discount to apply (0.85 = 85% of straddle price)

    Returns:
        Expected move in dollars (1 standard deviation)

    Rationale:
        Straddle price represents market's implied move, but straddles trade
        at a premium due to supply/demand. Empirically, ~85% of straddle price
        is a better estimator.
    """
    straddle_price = atm_call.mid + atm_put.mid
    return straddle_price * discount_factor


def expected_move_from_iv(
    spot_price: float,
    implied_vol: float,
    dte: int,
) -> float:
    """Estimate expected move using Black-Scholes assumption.

    Args:
        spot_price: Current underlying price
        implied_vol: Implied volatility (annualized, as decimal, e.g., 0.25 = 25%)
        dte: Days to expiration

    Returns:
        Expected move in dollars (1 standard deviation)

    Formula:
        expected_move = S * IV * sqrt(T)
        where T = dte / 365

    Note:
        This assumes lognormal price distribution (Black-Scholes assumption),
        which is not perfectly accurate for equities but provides a reasonable
        theoretical benchmark.
    """
    time_fraction = dte / 365.0
    return spot_price * implied_vol * math.sqrt(time_fraction)


def find_atm_options(
    options: List[Option],
    spot_price: float,
) -> tuple[Option | None, Option | None]:
    """Find ATM call and put options closest to spot price.

    Args:
        options: List of options (should all have same expiration)
        spot_price: Current underlying price

    Returns:
        Tuple of (atm_call, atm_put), either may be None if not found
    """
    calls = [opt for opt in options if opt.option_type == "call"]
    puts = [opt for opt in options if opt.option_type == "put"]

    # Find closest strike to spot
    atm_call = None
    atm_put = None

    if calls:
        atm_call = min(calls, key=lambda c: abs(c.strike - spot_price))

    if puts:
        atm_put = min(puts, key=lambda p: abs(p.strike - spot_price))

    return atm_call, atm_put


def calculate_expected_move(
    options: List[Option],
    spot_price: float,
    method: str = "straddle",
    discount_factor: float = 0.85,
) -> tuple[float, float]:
    """Calculate expected move using specified method.

    Args:
        options: List of options with same expiration
        spot_price: Current underlying price
        method: "straddle", "iv", or "both"
        discount_factor: Discount factor for straddle method

    Returns:
        Tuple of (expected_move_straddle, expected_move_iv)
        If method is "straddle" only, iv estimate will match straddle
        If method is "iv" only, straddle estimate will match iv

    Raises:
        ValueError: If options list is empty or no ATM options found
    """
    if not options:
        raise ValueError("Options list is empty")

    dte = options[0].dte
    atm_call, atm_put = find_atm_options(options, spot_price)

    em_straddle = 0.0
    em_iv = 0.0

    if method in ("straddle", "both"):
        if atm_call and atm_put:
            em_straddle = expected_move_from_straddle(atm_call, atm_put, discount_factor)
        else:
            # Fallback to IV method if ATM options not found
            if atm_call:
                em_straddle = expected_move_from_iv(spot_price, atm_call.implied_vol, dte)
            elif atm_put:
                em_straddle = expected_move_from_iv(spot_price, atm_put.implied_vol, dte)

    if method in ("iv", "both"):
        # Use ATM IV if available, otherwise average of all options
        if atm_call:
            iv = atm_call.implied_vol
        elif atm_put:
            iv = atm_put.implied_vol
        else:
            iv = sum(opt.implied_vol for opt in options) / len(options)

        em_iv = expected_move_from_iv(spot_price, iv, dte)

    # If only one method requested, set both to same value
    if method == "straddle":
        em_iv = em_straddle
    elif method == "iv":
        em_straddle = em_iv

    return em_straddle, em_iv
