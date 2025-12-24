"""Portfolio-level risk management.

Aggregates risk metrics across multiple positions to manage overall portfolio risk.
"""

import logging
from dataclasses import dataclass
from datetime import date
from typing import List, Dict, Tuple

import numpy as np

from ..models.iron_condor import IronCondor
from ..analytics.greeks import compute_or_fallback_greeks
from .margin import MarginCalculator

logger = logging.getLogger("condor_screener.portfolio")


@dataclass(frozen=True)
class Position:
    """Represents an open iron condor position.

    Attributes:
        iron_condor: The iron condor structure
        quantity: Number of contracts (positive for long, negative for short)
        entry_date: Date position was opened
        cost_basis: Total cost/credit for the position (negative = credit received)
        spot_at_entry: Underlying price when position was opened
    """
    iron_condor: IronCondor
    quantity: int
    entry_date: date
    cost_basis: float
    spot_at_entry: float

    @property
    def current_pnl(self) -> float:
        """Calculate current unrealized P&L.

        Note: This is a simplified calculation. In reality, you'd need
        current market prices for the options.
        """
        # Placeholder - would need current option prices
        return 0.0

    @property
    def days_in_trade(self) -> int:
        """Number of days position has been held."""
        return (date.today() - self.entry_date).days

    @property
    def dte(self) -> int:
        """Days to expiration."""
        return self.iron_condor.short_put.dte


class PortfolioRiskManager:
    """Manage portfolio-level risk metrics and limits.

    Aggregates Greeks, calculates risk metrics, and enforces risk limits
    across all open positions.
    """

    def __init__(
        self,
        positions: List[Position],
        account_value: float,
        spot_prices: Dict[str, float] | None = None
    ):
        """Initialize portfolio risk manager.

        Args:
            positions: List of open Position objects
            account_value: Current account value in dollars
            spot_prices: Dictionary mapping ticker to current spot price
        """
        self.positions = positions
        self.account_value = account_value
        self.spot_prices = spot_prices or {}

    def total_delta(self) -> float:
        """Calculate aggregate portfolio delta.

        Delta measures directional exposure. Portfolio delta tells you
        how much your portfolio value will change for a $1 move in the underlying.

        Returns:
            Total portfolio delta

        Example:
            If portfolio delta is +50, portfolio gains ~$50 if underlying rises $1.
            If portfolio delta is -30, portfolio loses ~$30 if underlying rises $1.
        """
        total = 0.0

        for position in self.positions:
            ticker = position.iron_condor.ticker
            spot = self.spot_prices.get(ticker, position.spot_at_entry)

            # Get Greeks for all four legs
            for leg in [position.iron_condor.short_put, position.iron_condor.long_put,
                       position.iron_condor.short_call, position.iron_condor.long_call]:

                delta, _, _, _ = compute_or_fallback_greeks(leg, spot)

                # Short options have negative quantity
                # Long put and long call we're long (+1 per contract)
                # Short put and short call we're short (-1 per contract)
                if leg == position.iron_condor.short_put or leg == position.iron_condor.short_call:
                    leg_quantity = -position.quantity
                else:
                    leg_quantity = position.quantity

                # Each contract is 100 shares
                leg_delta = delta * leg_quantity * 100

                total += leg_delta

        logger.debug("Portfolio total delta: %.2f", total)
        return total

    def total_gamma(self) -> float:
        """Calculate aggregate portfolio gamma.

        Gamma measures how fast delta changes. High gamma means delta
        changes quickly with underlying price moves.

        Returns:
            Total portfolio gamma
        """
        total = 0.0

        for position in self.positions:
            ticker = position.iron_condor.ticker
            spot = self.spot_prices.get(ticker, position.spot_at_entry)

            for leg in [position.iron_condor.short_put, position.iron_condor.long_put,
                       position.iron_condor.short_call, position.iron_condor.long_call]:

                _, gamma, _, _ = compute_or_fallback_greeks(leg, spot)

                if gamma is None:
                    continue

                if leg == position.iron_condor.short_put or leg == position.iron_condor.short_call:
                    leg_quantity = -position.quantity
                else:
                    leg_quantity = position.quantity

                leg_gamma = gamma * leg_quantity * 100
                total += leg_gamma

        logger.debug("Portfolio total gamma: %.4f", total)
        return total

    def total_theta(self) -> float:
        """Calculate aggregate portfolio theta (time decay).

        Theta is typically negative for long options (lose value each day)
        and positive for short options (gain value from time decay).

        Returns:
            Total portfolio theta (daily)

        Note:
            Positive theta means you make money from time decay.
            Negative theta means you lose money from time decay.
        """
        total = 0.0

        for position in self.positions:
            ticker = position.iron_condor.ticker
            spot = self.spot_prices.get(ticker, position.spot_at_entry)

            for leg in [position.iron_condor.short_put, position.iron_condor.long_put,
                       position.iron_condor.short_call, position.iron_condor.long_call]:

                _, _, theta, _ = compute_or_fallback_greeks(leg, spot)

                if theta is None:
                    continue

                if leg == position.iron_condor.short_put or leg == position.iron_condor.short_call:
                    leg_quantity = -position.quantity
                else:
                    leg_quantity = position.quantity

                # Theta is per year, divide by 365 for daily
                leg_theta = (theta / 365) * leg_quantity * 100
                total += leg_theta

        logger.debug("Portfolio total theta (daily): %.2f", total)
        return total

    def total_vega(self) -> float:
        """Calculate aggregate portfolio vega (IV sensitivity).

        Vega measures sensitivity to implied volatility changes.

        Returns:
            Total portfolio vega (change in value per 1% IV change)

        Note:
            Positive vega means you benefit from IV increase.
            Negative vega means you benefit from IV decrease (short vol).
        """
        total = 0.0

        for position in self.positions:
            ticker = position.iron_condor.ticker
            spot = self.spot_prices.get(ticker, position.spot_at_entry)

            for leg in [position.iron_condor.short_put, position.iron_condor.long_put,
                       position.iron_condor.short_call, position.iron_condor.long_call]:

                _, _, _, vega = compute_or_fallback_greeks(leg, spot)

                if vega is None:
                    continue

                if leg == position.iron_condor.short_put or leg == position.iron_condor.short_call:
                    leg_quantity = -position.quantity
                else:
                    leg_quantity = position.quantity

                leg_vega = vega * leg_quantity * 100
                total += leg_vega

        logger.debug("Portfolio total vega: %.2f", total)
        return total

    def total_margin_required(self) -> float:
        """Calculate total margin requirement across all positions.

        Returns:
            Total margin required in dollars
        """
        total = 0.0

        for position in self.positions:
            margin = MarginCalculator.iron_condor_margin(
                position.iron_condor,
                quantity=abs(position.quantity)
            )
            total += margin

        return total

    def margin_utilization(self) -> float:
        """Calculate margin utilization as percentage of account value.

        Returns:
            Margin utilization percentage (e.g., 35.5 means 35.5% utilized)
        """
        if self.account_value <= 0:
            return 0.0

        margin_used = self.total_margin_required()
        utilization = (margin_used / self.account_value) * 100

        return utilization

    def check_risk_limits(
        self,
        max_delta: float = 100.0,
        max_gamma: float = 10.0,
        min_theta: float = -500.0,
        max_vega: float = 1000.0,
        max_margin_pct: float = 50.0
    ) -> List[str]:
        """Check if portfolio violates risk limits.

        Args:
            max_delta: Maximum absolute delta exposure
            max_gamma: Maximum absolute gamma exposure
            min_theta: Minimum theta (most negative allowed)
            max_vega: Maximum absolute vega exposure
            max_margin_pct: Maximum margin utilization percentage

        Returns:
            List of violation messages (empty if no violations)

        Example:
            >>> violations = portfolio.check_risk_limits()
            >>> if violations:
            >>>     for msg in violations:
            >>>         logger.warning(msg)
        """
        violations = []

        # Check delta
        delta = self.total_delta()
        if abs(delta) > max_delta:
            violations.append(
                f"Delta exposure {delta:.2f} exceeds limit ±{max_delta:.2f}"
            )

        # Check gamma
        gamma = self.total_gamma()
        if abs(gamma) > max_gamma:
            violations.append(
                f"Gamma exposure {gamma:.4f} exceeds limit ±{max_gamma:.4f}"
            )

        # Check theta
        theta = self.total_theta()
        if theta < min_theta:
            violations.append(
                f"Theta {theta:.2f} below minimum {min_theta:.2f}"
            )

        # Check vega
        vega = self.total_vega()
        if abs(vega) > max_vega:
            violations.append(
                f"Vega exposure {vega:.2f} exceeds limit ±{max_vega:.2f}"
            )

        # Check margin utilization
        margin_util = self.margin_utilization()
        if margin_util > max_margin_pct:
            violations.append(
                f"Margin utilization {margin_util:.1f}% exceeds limit {max_margin_pct:.1f}%"
            )

        if violations:
            logger.warning("Portfolio has %d risk limit violations", len(violations))
        else:
            logger.info("Portfolio within all risk limits")

        return violations

    def portfolio_summary(self) -> Dict[str, float]:
        """Get comprehensive portfolio risk summary.

        Returns:
            Dictionary with all portfolio risk metrics
        """
        return {
            'account_value': self.account_value,
            'num_positions': len(self.positions),
            'total_delta': self.total_delta(),
            'total_gamma': self.total_gamma(),
            'total_theta': self.total_theta(),
            'total_vega': self.total_vega(),
            'margin_required': self.total_margin_required(),
            'margin_utilization_pct': self.margin_utilization(),
            'buying_power_available': self.account_value - self.total_margin_required(),
        }

    def position_concentration(self) -> Dict[str, float]:
        """Calculate position concentration by ticker.

        Returns:
            Dictionary mapping ticker to percentage of portfolio margin
        """
        total_margin = self.total_margin_required()

        if total_margin == 0:
            return {}

        concentration = {}

        for position in self.positions:
            ticker = position.iron_condor.ticker
            margin = MarginCalculator.iron_condor_margin(
                position.iron_condor,
                quantity=abs(position.quantity)
            )

            pct = (margin / total_margin) * 100

            if ticker in concentration:
                concentration[ticker] += pct
            else:
                concentration[ticker] = pct

        return concentration
