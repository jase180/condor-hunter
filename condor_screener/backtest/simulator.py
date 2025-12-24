"""Iron condor P&L simulator for backtesting.

Simulates the P&L of an iron condor from entry to exit, accounting for:
- Profit taking (e.g., close at 50% max profit)
- Stop losses (e.g., close at 2x max profit loss)
- Time-based exits (e.g., close at 21 DTE)
- Expiration P&L
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional
import logging

from condor_screener.models.iron_condor import IronCondor

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExitRule:
    """Rules for exiting an iron condor position.

    Attributes:
        profit_target_pct: Close if profit reaches this % of max profit (e.g., 0.50 for 50%)
        stop_loss_pct: Close if loss reaches this % of max loss (e.g., 1.0 for 100% loss)
        min_dte_to_close: Close position when DTE reaches this threshold (e.g., 21)
        close_before_earnings_days: Close this many days before earnings (e.g., 3)
    """
    profit_target_pct: float = 0.50  # 50% of max profit
    stop_loss_pct: float = 1.0  # 100% of max loss (let it expire)
    min_dte_to_close: int = 21  # Close at 21 DTE
    close_before_earnings_days: int = 3  # Close 3 days before earnings


@dataclass(frozen=True)
class BacktestResult:
    """Result of backtesting a single iron condor.

    Attributes:
        iron_condor: The iron condor setup
        entry_date: Date position was entered
        exit_date: Date position was exited
        exit_reason: Why position was closed ('profit_target', 'stop_loss', 'min_dte', 'earnings', 'expiration')
        entry_credit: Credit received at entry
        exit_cost: Cost to close position (or value at expiration)
        realized_pnl: Actual P&L realized (entry_credit - exit_cost)
        max_profit: Maximum possible profit
        max_loss: Maximum possible loss
        return_pct: Return as % of risk (realized_pnl / max_loss * 100)
        days_held: Number of days position was held
        is_winner: True if realized_pnl > 0
        had_earnings: True if earnings fell within position holding period
    """
    iron_condor: IronCondor
    entry_date: date
    exit_date: date
    exit_reason: str
    entry_credit: float
    exit_cost: float
    realized_pnl: float
    max_profit: float
    max_loss: float
    return_pct: float
    days_held: int
    is_winner: bool
    had_earnings: bool


def simulate_iron_condor(
    iron_condor: IronCondor,
    entry_date: date,
    exit_rule: ExitRule,
    price_path: list[tuple[date, float]],
    earnings_date: Optional[str] = None,
) -> BacktestResult:
    """Simulate an iron condor from entry to exit.

    Args:
        iron_condor: The iron condor setup
        entry_date: Date position was entered
        exit_rule: Rules for when to exit
        price_path: List of (date, price) tuples showing underlying price over time
        earnings_date: Optional earnings date (YYYY-MM-DD format)

    Returns:
        BacktestResult with P&L and exit details
    """
    expiration = iron_condor.expiration
    entry_credit = iron_condor.net_credit
    max_profit = iron_condor.max_profit
    max_loss = iron_condor.max_loss

    # Check if earnings falls within holding period
    had_earnings = False
    if earnings_date:
        try:
            earnings_dt = date.fromisoformat(earnings_date)
            if entry_date <= earnings_dt <= expiration:
                had_earnings = True
        except ValueError:
            logger.warning(f"Invalid earnings date format: {earnings_date}")

    # Simulate through each day
    exit_date = expiration
    exit_reason = 'expiration'
    exit_cost = 0.0  # Will be calculated based on exit

    for dt, price in price_path:
        if dt < entry_date:
            continue
        if dt > expiration:
            break

        # Calculate current DTE
        days_to_exp = (expiration - dt).days

        # Rule 1: Close before earnings
        if earnings_date and exit_rule.close_before_earnings_days > 0:
            try:
                earnings_dt = date.fromisoformat(earnings_date)
                days_to_earnings = (earnings_dt - dt).days
                if 0 <= days_to_earnings <= exit_rule.close_before_earnings_days:
                    exit_date = dt
                    exit_reason = 'earnings'
                    exit_cost = _estimate_exit_cost(iron_condor, price, days_to_exp, pct_of_max=0.30)
                    break
            except ValueError:
                pass

        # Rule 2: Close at min DTE
        if days_to_exp <= exit_rule.min_dte_to_close:
            exit_date = dt
            exit_reason = 'min_dte'
            exit_cost = _estimate_exit_cost(iron_condor, price, days_to_exp, pct_of_max=0.25)
            break

        # Estimate current position value
        current_value = _estimate_position_value(iron_condor, price, days_to_exp)
        current_pnl = entry_credit - current_value

        # Rule 3: Profit target
        if current_pnl >= max_profit * exit_rule.profit_target_pct:
            exit_date = dt
            exit_reason = 'profit_target'
            exit_cost = current_value
            break

        # Rule 4: Stop loss
        if current_pnl <= -max_loss * exit_rule.stop_loss_pct:
            exit_date = dt
            exit_reason = 'stop_loss'
            exit_cost = current_value
            break

    # If we didn't exit early, calculate expiration P&L
    if exit_reason == 'expiration':
        final_price = price_path[-1][1] if price_path else 0.0
        exit_cost = _calculate_expiration_value(iron_condor, final_price)

    # Calculate final metrics
    realized_pnl = entry_credit - exit_cost
    return_pct = (realized_pnl / max_loss * 100) if max_loss > 0 else 0.0
    days_held = (exit_date - entry_date).days
    is_winner = realized_pnl > 0

    return BacktestResult(
        iron_condor=iron_condor,
        entry_date=entry_date,
        exit_date=exit_date,
        exit_reason=exit_reason,
        entry_credit=entry_credit,
        exit_cost=exit_cost,
        realized_pnl=realized_pnl,
        max_profit=max_profit,
        max_loss=max_loss,
        return_pct=return_pct,
        days_held=days_held,
        is_winner=is_winner,
        had_earnings=had_earnings,
    )


def _estimate_position_value(iron_condor: IronCondor, price: float, dte: int) -> float:
    """Estimate the current value of an iron condor position.

    Simplified estimation:
    - If price is inside the short strikes, value decays linearly with time
    - If price breaches a short strike, estimate intrinsic value
    """
    short_put = iron_condor.short_put.strike
    short_call = iron_condor.short_call.strike
    long_put = iron_condor.long_put.strike
    long_call = iron_condor.long_call.strike
    max_profit = iron_condor.max_profit
    max_loss = iron_condor.max_loss
    initial_dte = iron_condor.short_put.dte

    # Price is well inside the tent - position is winning
    if short_put < price < short_call:
        # Linear time decay - more time means more value remaining
        time_factor = dte / max(initial_dte, 1)
        return max_profit * time_factor * 0.3  # Keep some value for uncertainty

    # Price breached put side
    if price <= short_put:
        intrinsic = max(0, short_put - price)  # Short put intrinsic value
        intrinsic_long = max(0, long_put - price)  # Long put intrinsic value
        spread_value = intrinsic - intrinsic_long
        return min(spread_value * 100, max_loss)  # Cap at max loss

    # Price breached call side
    if price >= short_call:
        intrinsic = max(0, price - short_call)  # Short call intrinsic value
        intrinsic_long = max(0, price - long_call)  # Long call intrinsic value
        spread_value = intrinsic - intrinsic_long
        return min(spread_value * 100, max_loss)  # Cap at max loss

    # Default: assume some value remains
    return max_profit * 0.5


def _estimate_exit_cost(iron_condor: IronCondor, price: float, dte: int, pct_of_max: float = 0.25) -> float:
    """Estimate cost to close position early.

    When closing early (min DTE or earnings), assume we pay some % of max profit to exit.
    """
    return iron_condor.max_profit * pct_of_max


def _calculate_expiration_value(iron_condor: IronCondor, final_price: float) -> float:
    """Calculate the value of iron condor at expiration (intrinsic value only)."""
    short_put = iron_condor.short_put.strike
    short_call = iron_condor.short_call.strike
    long_put = iron_condor.long_put.strike
    long_call = iron_condor.long_call.strike

    # Price inside tent - all options expire worthless
    if short_put < final_price < short_call:
        return 0.0

    # Put side breached
    if final_price <= short_put:
        short_value = max(0, short_put - final_price)
        long_value = max(0, long_put - final_price)
        return (short_value - long_value) * 100

    # Call side breached
    if final_price >= short_call:
        short_value = max(0, final_price - short_call)
        long_value = max(0, final_price - long_call)
        return (short_value - long_value) * 100

    return 0.0
