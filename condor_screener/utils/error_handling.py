"""Error handling utilities for robust production operation.

Provides retry logic, graceful degradation, and error recovery mechanisms.
"""

import time
from typing import TypeVar, Callable, Type, Tuple
from functools import wraps
import logging

logger = logging.getLogger("condor_screener.error_handling")

T = TypeVar('T')


def retry_with_backoff(
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    logger_func: Callable[[str], None] | None = None
):
    """Decorator to retry function with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Multiplier for exponential backoff (wait time = backoff_factor ** attempt)
        exceptions: Tuple of exception types to catch and retry
        logger_func: Optional logging function (defaults to logger.warning)

    Returns:
        Decorated function with retry logic

    Example:
        >>> @retry_with_backoff(max_retries=3, exceptions=(ConnectionError, TimeoutError))
        >>> def fetch_data():
        >>>     # Potentially flaky API call
        >>>     return api.get_option_chain("SPY")

    Raises:
        The original exception if all retries are exhausted
    """
    log_func = logger_func or logger.warning

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries - 1:
                        # Last attempt failed, re-raise
                        logger.error(
                            f"Function {func.__name__} failed after {max_retries} attempts: {e}"
                        )
                        raise

                    wait_time = backoff_factor ** attempt
                    log_func(
                        f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: {e}. "
                        f"Retrying in {wait_time:.1f}s..."
                    )
                    time.sleep(wait_time)

            # Should never reach here, but for type checking
            raise RuntimeError(f"Unexpected state in retry logic for {func.__name__}")

        return wrapper
    return decorator


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers, returning default on division by zero.

    Args:
        numerator: Numerator value
        denominator: Denominator value
        default: Value to return if denominator is zero

    Returns:
        Result of division, or default if denominator is zero

    Example:
        >>> safe_divide(10, 2)
        5.0
        >>> safe_divide(10, 0, default=float('inf'))
        inf
    """
    if denominator == 0:
        logger.debug(f"Division by zero: {numerator}/{denominator}, returning {default}")
        return default
    return numerator / denominator


def validate_option_data(option_dict: dict) -> Tuple[bool, str]:
    """Validate option data dictionary for completeness and sanity.

    Args:
        option_dict: Dictionary containing option data

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        >>> data = {"ticker": "SPY", "strike": 550, "bid": 5.0, "ask": 5.5}
        >>> is_valid, error = validate_option_data(data)
        >>> if not is_valid:
        >>>     logger.error(f"Invalid option data: {error}")
    """
    required_fields = ['ticker', 'strike', 'expiration', 'option_type', 'bid', 'ask']

    # Check required fields
    for field in required_fields:
        if field not in option_dict:
            return False, f"Missing required field: {field}"

    # Sanity checks
    if option_dict.get('bid', 0) < 0:
        return False, f"Negative bid price: {option_dict['bid']}"

    if option_dict.get('ask', 0) < 0:
        return False, f"Negative ask price: {option_dict['ask']}"

    bid = option_dict.get('bid', 0)
    ask = option_dict.get('ask', 0)
    if bid > ask:
        return False, f"Bid {bid} > Ask {ask} (crossed market)"

    if option_dict.get('strike', 0) <= 0:
        return False, f"Invalid strike price: {option_dict['strike']}"

    if option_dict.get('option_type') not in ['call', 'put']:
        return False, f"Invalid option type: {option_dict['option_type']}"

    # Check Greeks if present
    delta = option_dict.get('delta')
    if delta is not None:
        if abs(delta) > 1.0:
            return False, f"Delta {delta} outside valid range [-1, 1]"

        # Call delta should be positive, put delta negative
        if option_dict['option_type'] == 'call' and delta < 0:
            return False, f"Call option has negative delta: {delta}"
        if option_dict['option_type'] == 'put' and delta > 0:
            return False, f"Put option has positive delta: {delta}"

    return True, ""


class ScreeningError(Exception):
    """Base exception for screening-related errors."""
    pass


class DataValidationError(ValueError, ScreeningError):
    """Raised when option data fails validation.

    Inherits from ValueError for backward compatibility.
    """
    pass


class InsufficientDataError(ScreeningError):
    """Raised when insufficient data to perform screening."""
    pass


class ConfigurationError(ScreeningError):
    """Raised when configuration is invalid."""
    pass
