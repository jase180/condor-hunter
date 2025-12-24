"""Greeks calculation and validation using Black-Scholes-Merton model.

Provides fallback Greeks calculations when broker data is unavailable,
and validation functions to ensure Greeks are consistent.
"""

import logging
import math
from typing import Tuple
from datetime import date

import numpy as np
from scipy.stats import norm

from ..models.option import Option

logger = logging.getLogger("condor_screener.greeks")


class BlackScholesGreeks:
    """Calculate option Greeks using Black-Scholes-Merton model.

    Assumes European-style options with no dividends (can be extended).
    """

    @staticmethod
    def calculate_delta(
        spot: float,
        strike: float,
        time_to_expiry: float,
        rate: float,
        vol: float,
        option_type: str
    ) -> float:
        """Calculate delta using Black-Scholes formula.

        Args:
            spot: Current underlying price
            strike: Strike price
            time_to_expiry: Time to expiration in years
            rate: Risk-free interest rate (annualized)
            vol: Implied volatility (annualized)
            option_type: 'call' or 'put'

        Returns:
            Delta value between -1 and 1

        Example:
            >>> delta = BlackScholesGreeks.calculate_delta(
            >>>     spot=100, strike=105, time_to_expiry=0.25,
            >>>     rate=0.02, vol=0.25, option_type='call'
            >>> )
            >>> # Returns ~0.42 for slightly OTM call
        """
        if time_to_expiry <= 0:
            # At expiration
            if option_type == 'call':
                return 1.0 if spot > strike else 0.0
            else:
                return -1.0 if spot < strike else 0.0

        d1 = BlackScholesGreeks._d1(spot, strike, time_to_expiry, rate, vol)

        if option_type == 'call':
            delta = norm.cdf(d1)
        elif option_type == 'put':
            delta = -norm.cdf(-d1)
        else:
            raise ValueError(f"Invalid option_type: {option_type}")

        return delta

    @staticmethod
    def calculate_gamma(
        spot: float,
        strike: float,
        time_to_expiry: float,
        rate: float,
        vol: float
    ) -> float:
        """Calculate gamma using Black-Scholes formula.

        Gamma is the same for both calls and puts.

        Args:
            spot: Current underlying price
            strike: Strike price
            time_to_expiry: Time to expiration in years
            rate: Risk-free interest rate (annualized)
            vol: Implied volatility (annualized)

        Returns:
            Gamma value (always positive)
        """
        if time_to_expiry <= 0:
            return 0.0

        d1 = BlackScholesGreeks._d1(spot, strike, time_to_expiry, rate, vol)
        gamma = norm.pdf(d1) / (spot * vol * math.sqrt(time_to_expiry))

        return gamma

    @staticmethod
    def calculate_theta(
        spot: float,
        strike: float,
        time_to_expiry: float,
        rate: float,
        vol: float,
        option_type: str
    ) -> float:
        """Calculate theta (time decay) using Black-Scholes formula.

        Args:
            spot: Current underlying price
            strike: Strike price
            time_to_expiry: Time to expiration in years
            rate: Risk-free interest rate (annualized)
            vol: Implied volatility (annualized)
            option_type: 'call' or 'put'

        Returns:
            Theta value (typically negative, represents daily decay)

        Note:
            Returns theta per year. Divide by 365 for daily theta.
        """
        if time_to_expiry <= 0:
            return 0.0

        d1 = BlackScholesGreeks._d1(spot, strike, time_to_expiry, rate, vol)
        d2 = d1 - vol * math.sqrt(time_to_expiry)

        term1 = -(spot * norm.pdf(d1) * vol) / (2 * math.sqrt(time_to_expiry))

        if option_type == 'call':
            term2 = -rate * strike * math.exp(-rate * time_to_expiry) * norm.cdf(d2)
            theta = term1 + term2
        elif option_type == 'put':
            term2 = rate * strike * math.exp(-rate * time_to_expiry) * norm.cdf(-d2)
            theta = term1 + term2
        else:
            raise ValueError(f"Invalid option_type: {option_type}")

        return theta

    @staticmethod
    def calculate_vega(
        spot: float,
        strike: float,
        time_to_expiry: float,
        rate: float,
        vol: float
    ) -> float:
        """Calculate vega using Black-Scholes formula.

        Vega is the same for both calls and puts.

        Args:
            spot: Current underlying price
            strike: Strike price
            time_to_expiry: Time to expiration in years
            rate: Risk-free interest rate (annualized)
            vol: Implied volatility (annualized)

        Returns:
            Vega value (change in option price per 1% change in IV)

        Note:
            Returns vega for 1% (0.01) change in IV.
        """
        if time_to_expiry <= 0:
            return 0.0

        d1 = BlackScholesGreeks._d1(spot, strike, time_to_expiry, rate, vol)
        vega = spot * norm.pdf(d1) * math.sqrt(time_to_expiry) / 100

        return vega

    @staticmethod
    def calculate_all_greeks(
        spot: float,
        strike: float,
        time_to_expiry: float,
        rate: float,
        vol: float,
        option_type: str
    ) -> Tuple[float, float, float, float]:
        """Calculate all Greeks at once (more efficient).

        Args:
            spot: Current underlying price
            strike: Strike price
            time_to_expiry: Time to expiration in years
            rate: Risk-free interest rate (annualized)
            vol: Implied volatility (annualized)
            option_type: 'call' or 'put'

        Returns:
            Tuple of (delta, gamma, theta, vega)
        """
        delta = BlackScholesGreeks.calculate_delta(
            spot, strike, time_to_expiry, rate, vol, option_type
        )
        gamma = BlackScholesGreeks.calculate_gamma(
            spot, strike, time_to_expiry, rate, vol
        )
        theta = BlackScholesGreeks.calculate_theta(
            spot, strike, time_to_expiry, rate, vol, option_type
        )
        vega = BlackScholesGreeks.calculate_vega(
            spot, strike, time_to_expiry, rate, vol
        )

        return delta, gamma, theta, vega

    @staticmethod
    def _d1(spot: float, strike: float, time_to_expiry: float, rate: float, vol: float) -> float:
        """Calculate d1 term in Black-Scholes formula."""
        return (math.log(spot / strike) + (rate + 0.5 * vol ** 2) * time_to_expiry) / \
               (vol * math.sqrt(time_to_expiry))


def validate_greeks(option: Option, tolerance: float = 0.05) -> Tuple[bool, str]:
    """Validate that option Greeks are consistent and within valid ranges.

    Args:
        option: Option object with Greeks to validate
        tolerance: Tolerance for validation checks (default 5%)

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        >>> is_valid, error = validate_greeks(my_option)
        >>> if not is_valid:
        >>>     logger.warning("Invalid Greeks: %s", error)
    """
    if option.delta is None:
        return True, ""  # Can't validate if no delta provided

    # Delta must be in [-1, 1]
    if abs(option.delta) > 1.0 + tolerance:
        return False, f"Delta {option.delta:.3f} outside valid range [-1, 1]"

    # Call delta should be positive [0, 1]
    if option.option_type == 'call':
        if option.delta < -tolerance:
            return False, f"Call option has negative delta: {option.delta:.3f}"
        if option.delta > 1.0 + tolerance:
            return False, f"Call delta {option.delta:.3f} > 1.0"

    # Put delta should be negative [-1, 0]
    if option.option_type == 'put':
        if option.delta > tolerance:
            return False, f"Put option has positive delta: {option.delta:.3f}"
        if option.delta < -1.0 - tolerance:
            return False, f"Put delta {option.delta:.3f} < -1.0"

    # Gamma should be non-negative
    if option.gamma is not None:
        if option.gamma < -tolerance:
            return False, f"Gamma should be non-negative, got: {option.gamma:.3f}"

    # Vega should be non-negative
    if option.vega is not None:
        if option.vega < -tolerance:
            return False, f"Vega should be non-negative, got: {option.vega:.3f}"

    # Theta is typically negative but can be positive for deep ITM puts
    # Just check it's not unreasonably large
    if option.theta is not None:
        if abs(option.theta) > option.mid * 2:  # Sanity check
            return False, f"Theta {option.theta:.3f} seems unreasonably large"

    return True, ""


def compute_or_fallback_greeks(
    option: Option,
    spot: float,
    rate: float = 0.02
) -> Tuple[float, float | None, float | None, float | None]:
    """Get option Greeks, computing them if not provided.

    Args:
        option: Option object (may or may not have Greeks)
        spot: Current underlying price
        rate: Risk-free rate (default 2%)

    Returns:
        Tuple of (delta, gamma, theta, vega) - uses provided values or computes fallback

    Example:
        >>> delta, gamma, theta, vega = compute_or_fallback_greeks(option, spot=560.0)
        >>> # Returns broker-provided Greeks if available, otherwise computes them
    """
    # If delta is provided and valid, trust it
    if option.delta is not None:
        is_valid, error = validate_greeks(option)
        if is_valid:
            return option.delta, option.gamma, option.theta, option.vega
        else:
            logger.warning(
                "Option %s strike %s has invalid Greeks: %s. Computing fallback.",
                option.ticker, option.strike, error
            )

    # Need to compute Greeks
    if option.implied_vol is None or option.implied_vol <= 0:
        logger.warning(
            "Cannot compute Greeks for %s strike %s: invalid IV %s",
            option.ticker, option.strike, option.implied_vol
        )
        # Return zero delta as last resort
        return 0.0, None, None, None

    time_to_expiry = option.dte / 365.0

    try:
        delta, gamma, theta, vega = BlackScholesGreeks.calculate_all_greeks(
            spot=spot,
            strike=option.strike,
            time_to_expiry=time_to_expiry,
            rate=rate,
            vol=option.implied_vol,
            option_type=option.option_type
        )

        logger.debug(
            "Computed fallback Greeks for %s strike %s: delta=%.3f",
            option.ticker, option.strike, delta
        )

        return delta, gamma, theta, vega

    except Exception as e:
        logger.error(
            "Failed to compute Greeks for %s strike %s: %s",
            option.ticker, option.strike, e
        )
        return 0.0, None, None, None
