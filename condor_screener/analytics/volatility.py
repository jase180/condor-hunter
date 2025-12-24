"""Volatility calculations for options screening.

Includes IV rank, IV percentile, and realized volatility estimators.
"""

import math
from typing import List, Tuple


def calculate_iv_rank(
    current_iv: float,
    historical_ivs: List[float],
) -> float:
    """Calculate IV Rank: where current IV sits in historical range.

    Args:
        current_iv: Current implied volatility
        historical_ivs: List of historical IVs (typically 252 days)

    Returns:
        IV Rank as percentage (0–100)

    Formula:
        IVR = (current_IV - min_IV) / (max_IV - min_IV) * 100

    Interpretation:
        - IVR > 50: IV is elevated (good for selling premium)
        - IVR < 50: IV is depressed (poor for credit spreads)
        - IVR > 70: Very high IV (excellent premium environment)
    """
    if not historical_ivs:
        return 50.0  # Neutral default if no data

    min_iv = min(historical_ivs)
    max_iv = max(historical_ivs)

    if max_iv == min_iv:
        return 50.0  # No range, assume neutral

    ivr = ((current_iv - min_iv) / (max_iv - min_iv)) * 100
    return max(0.0, min(100.0, ivr))  # Clamp to [0, 100]


def calculate_iv_percentile(
    current_iv: float,
    historical_ivs: List[float],
) -> float:
    """Calculate IV Percentile: % of days current IV exceeded historical values.

    Args:
        current_iv: Current implied volatility
        historical_ivs: List of historical IVs (typically 252 days)

    Returns:
        IV Percentile as percentage (0–100)

    Formula:
        IVP = (count of days where IV < current_IV) / total_days * 100

    Why use IVP:
        - More robust than IV Rank when outliers exist (e.g., COVID spike)
        - IVP = 80 means current IV is higher than 80% of historical values
    """
    if not historical_ivs:
        return 50.0  # Neutral default if no data

    count_below = sum(1 for iv in historical_ivs if iv < current_iv)
    ivp = (count_below / len(historical_ivs)) * 100
    return ivp


def calculate_realized_volatility_close_to_close(
    close_prices: List[float],
    annualize: bool = True,
) -> float:
    """Calculate realized volatility using close-to-close method.

    Args:
        close_prices: List of closing prices (in chronological order)
        annualize: If True, annualize the volatility (multiply by sqrt(252))

    Returns:
        Realized volatility as decimal (e.g., 0.25 = 25%)

    Formula:
        RV = std(log_returns) * sqrt(252)

    Note:
        This is the simplest RV estimator but less accurate than methods
        that use intraday data (e.g., Garman-Klass).
    """
    if len(close_prices) < 2:
        return 0.0

    # Calculate log returns
    log_returns = []
    for i in range(1, len(close_prices)):
        if close_prices[i] > 0 and close_prices[i - 1] > 0:
            log_ret = math.log(close_prices[i] / close_prices[i - 1])
            log_returns.append(log_ret)

    if not log_returns:
        return 0.0

    # Calculate standard deviation
    mean = sum(log_returns) / len(log_returns)
    variance = sum((r - mean) ** 2 for r in log_returns) / len(log_returns)
    daily_vol = math.sqrt(variance)

    # Annualize if requested
    if annualize:
        return daily_vol * math.sqrt(252)
    else:
        return daily_vol


def calculate_realized_volatility_garman_klass(
    ohlc_data: List[Tuple[float, float, float, float]],
    annualize: bool = True,
) -> float:
    """Calculate realized volatility using Garman-Klass estimator.

    Args:
        ohlc_data: List of (open, high, low, close) tuples
        annualize: If True, annualize the volatility (multiply by sqrt(252))

    Returns:
        Realized volatility as decimal (e.g., 0.25 = 25%)

    Formula:
        GK = sqrt(mean(0.5 * (log(H/L))^2 - (2*log(2)-1) * (log(C/O))^2))

    Why Garman-Klass:
        - Uses intraday range (high-low) which captures more information
        - More accurate than close-to-close method
        - Standard in options research
    """
    if not ohlc_data:
        return 0.0

    daily_variances = []
    for open_price, high, low, close in ohlc_data:
        if high <= 0 or low <= 0 or open_price <= 0 or close <= 0:
            continue
        if high < low:  # Data quality check
            continue

        # Garman-Klass formula
        hl_component = 0.5 * (math.log(high / low) ** 2)
        co_component = (2 * math.log(2) - 1) * (math.log(close / open_price) ** 2)
        daily_var = hl_component - co_component

        daily_variances.append(daily_var)

    if not daily_variances:
        return 0.0

    # Average variance across days
    avg_variance = sum(daily_variances) / len(daily_variances)
    daily_vol = math.sqrt(avg_variance)

    # Annualize if requested
    if annualize:
        return daily_vol * math.sqrt(252)
    else:
        return daily_vol


def calculate_realized_volatility(
    close_prices: List[float] | None = None,
    ohlc_data: List[Tuple[float, float, float, float]] | None = None,
    use_garman_klass: bool = True,
) -> float:
    """Calculate realized volatility using best available method.

    Args:
        close_prices: List of closing prices (fallback method)
        ohlc_data: List of (open, high, low, close) tuples (preferred method)
        use_garman_klass: If True and OHLC data available, use Garman-Klass

    Returns:
        Annualized realized volatility as decimal (e.g., 0.25 = 25%)

    Priority:
        1. Garman-Klass (if ohlc_data provided and use_garman_klass=True)
        2. Close-to-close (if close_prices provided)
        3. Return 0.0 if no data available
    """
    if use_garman_klass and ohlc_data:
        return calculate_realized_volatility_garman_klass(ohlc_data)
    elif close_prices:
        return calculate_realized_volatility_close_to_close(close_prices)
    else:
        return 0.0
