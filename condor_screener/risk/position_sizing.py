"""Position sizing strategies for optimal capital allocation.

Implements Kelly Criterion and other position sizing methods to help
traders determine appropriate position sizes based on edge and risk tolerance.
"""

import logging
import math
from typing import Dict, Tuple

from ..models.iron_condor import IronCondor
from .margin import MarginCalculator

logger = logging.getLogger("condor_screener.position_sizing")


class PositionSizer:
    """Calculate optimal position sizes using various methods."""

    @staticmethod
    def kelly_criterion(
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        account_value: float,
        max_kelly_fraction: float = 0.25
    ) -> Tuple[float, int]:
        """Calculate position size using Kelly Criterion.

        The Kelly Criterion determines the optimal fraction of capital to risk
        on a trade with a given edge.

        Formula:
            Kelly% = (win_rate * avg_win - loss_rate * avg_loss) / avg_win

        Args:
            win_rate: Historical win rate (0.0 to 1.0, e.g., 0.70 = 70%)
            avg_win: Average profit on winning trades (dollars)
            avg_loss: Average loss on losing trades (dollars, positive number)
            account_value: Total account value
            max_kelly_fraction: Maximum Kelly fraction to use (default 0.25 = 1/4 Kelly)

        Returns:
            Tuple of (kelly_fraction, recommended_dollars)

        Example:
            >>> # 70% win rate, avg win $200, avg loss $300
            >>> kelly_frac, dollars = PositionSizer.kelly_criterion(
            >>>     win_rate=0.70,
            >>>     avg_win=200,
            >>>     avg_loss=300,
            >>>     account_value=100000
            >>> )
            >>> # kelly_frac might be 0.05 (5%), dollars = $5000

        Note:
            - Kelly can be aggressive. Many traders use fractional Kelly (1/4 or 1/2)
            - If Kelly is negative or zero, you have no edge - don't trade
            - max_kelly_fraction caps the position size for safety
        """
        if win_rate <= 0 or win_rate >= 1:
            logger.warning("Invalid win_rate: %.2f (must be between 0 and 1)", win_rate)
            return 0.0, 0

        if avg_win <= 0:
            logger.warning("Invalid avg_win: %.2f (must be positive)", avg_win)
            return 0.0, 0

        if avg_loss <= 0:
            logger.warning("Invalid avg_loss: %.2f (must be positive)", avg_loss)
            return 0.0, 0

        loss_rate = 1.0 - win_rate

        # Kelly formula
        kelly = (win_rate * avg_win - loss_rate * avg_loss) / avg_win

        if kelly <= 0:
            logger.warning(
                "Negative Kelly %.4f - no statistical edge. Win rate: %.2f, Avg win: %.2f, Avg loss: %.2f",
                kelly, win_rate, avg_win, avg_loss
            )
            return 0.0, 0

        # Apply maximum Kelly fraction for safety
        kelly = min(kelly, max_kelly_fraction)

        # Calculate dollar amount
        recommended_dollars = account_value * kelly

        logger.info(
            "Kelly Criterion: %.2f%% of account (%.0f / %.0f)",
            kelly * 100, recommended_dollars, account_value
        )

        return kelly, int(recommended_dollars)

    @staticmethod
    def fixed_fractional(
        account_value: float,
        risk_fraction: float = 0.02
    ) -> int:
        """Calculate position size using fixed fractional method.

        Simple approach: risk a fixed percentage of account on each trade.

        Args:
            account_value: Total account value
            risk_fraction: Fraction of account to risk (default 0.02 = 2%)

        Returns:
            Dollar amount to risk

        Example:
            >>> risk_dollars = PositionSizer.fixed_fractional(100000, risk_fraction=0.02)
            >>> # risk_dollars = 2000 (2% of $100k)
        """
        if risk_fraction <= 0 or risk_fraction > 1:
            logger.warning("Invalid risk_fraction: %.2f", risk_fraction)
            return 0

        risk_dollars = int(account_value * risk_fraction)

        logger.info(
            "Fixed fractional: %.1f%% = $%d",
            risk_fraction * 100, risk_dollars
        )

        return risk_dollars

    @staticmethod
    def contracts_from_risk_dollars(
        ic: IronCondor,
        risk_dollars: float
    ) -> int:
        """Convert risk dollars to number of contracts.

        Args:
            ic: IronCondor to size
            risk_dollars: Dollar amount to risk

        Returns:
            Number of contracts

        Example:
            >>> ic = IronCondor(...)  # Max loss $300 per contract
            >>> contracts = PositionSizer.contracts_from_risk_dollars(ic, risk_dollars=3000)
            >>> # contracts = 10 (3000 / 300)
        """
        max_loss_per_contract = ic.max_loss * 100  # Convert to dollars

        if max_loss_per_contract <= 0:
            logger.warning("Invalid max loss: %.2f", max_loss_per_contract)
            return 0

        contracts = int(risk_dollars / max_loss_per_contract)

        logger.info(
            "Risk $%.2f with max loss $%.2f per contract = %d contracts",
            risk_dollars, max_loss_per_contract, contracts
        )

        return max(0, contracts)

    @staticmethod
    def optimal_f(
        win_rate: float,
        avg_win: float,
        avg_loss: float
    ) -> float:
        """Calculate Optimal F (Ralph Vince method).

        Optimal F is the fraction of capital that maximizes geometric growth.

        Args:
            win_rate: Historical win rate (0.0 to 1.0)
            avg_win: Average profit on winning trades
            avg_loss: Average loss on losing trades

        Returns:
            Optimal F fraction

        Note:
            Optimal F can be very aggressive. Consider using fractional Optimal F.
        """
        if avg_loss == 0:
            return 0.0

        # Simplified Optimal F calculation
        # More accurate would require historical trade sequence
        ratio = avg_win / avg_loss

        if ratio <= 0:
            return 0.0

        optimal_f = win_rate - ((1 - win_rate) / ratio)

        logger.info("Optimal F: %.4f", optimal_f)

        return max(0.0, optimal_f)

    @staticmethod
    def position_size_with_edge(
        ic: IronCondor,
        account_value: float,
        estimated_win_rate: float = 0.70,
        method: str = 'kelly'
    ) -> Tuple[int, Dict[str, float]]:
        """Calculate position size incorporating statistical edge.

        Args:
            ic: IronCondor to size
            account_value: Total account value
            estimated_win_rate: Estimated probability of success (default 0.70)
            method: 'kelly' or 'fixed' (default 'kelly')

        Returns:
            Tuple of (num_contracts, sizing_details)

        Example:
            >>> ic = IronCondor(...)
            >>> contracts, details = PositionSizer.position_size_with_edge(
            >>>     ic, account_value=100000, estimated_win_rate=0.75
            >>> )
            >>> print(f"Trade {contracts} contracts")
            >>> print(details)
        """
        max_profit = ic.max_profit * 100  # Per contract
        max_loss = ic.max_loss * 100      # Per contract

        details = {
            'method': method,
            'account_value': account_value,
            'estimated_win_rate': estimated_win_rate,
            'max_profit_per_contract': max_profit,
            'max_loss_per_contract': max_loss,
        }

        if method == 'kelly':
            # Use Kelly Criterion
            kelly_frac, kelly_dollars = PositionSizer.kelly_criterion(
                win_rate=estimated_win_rate,
                avg_win=max_profit,
                avg_loss=max_loss,
                account_value=account_value,
                max_kelly_fraction=0.25  # Use 1/4 Kelly for safety
            )

            contracts = PositionSizer.contracts_from_risk_dollars(ic, kelly_dollars)

            details['kelly_fraction'] = kelly_frac
            details['kelly_dollars'] = kelly_dollars
            details['contracts'] = contracts

        elif method == 'fixed':
            # Use fixed fractional (2% risk)
            risk_dollars = PositionSizer.fixed_fractional(account_value, risk_fraction=0.02)
            contracts = PositionSizer.contracts_from_risk_dollars(ic, risk_dollars)

            details['risk_dollars'] = risk_dollars
            details['contracts'] = contracts

        else:
            logger.error("Invalid sizing method: %s", method)
            return 0, details

        # Calculate actual risk and margin for the position
        actual_margin = MarginCalculator.iron_condor_margin(ic, quantity=contracts)
        actual_risk = max_loss * contracts
        actual_profit_potential = max_profit * contracts

        details['actual_contracts'] = contracts
        details['actual_margin'] = actual_margin
        details['actual_risk'] = actual_risk
        details['actual_profit_potential'] = actual_profit_potential
        details['risk_pct_of_account'] = (actual_risk / account_value * 100) if account_value > 0 else 0

        logger.info(
            "Position sizing (%s): %d contracts, $%.2f risk (%.2f%% of account)",
            method, contracts, actual_risk, details['risk_pct_of_account']
        )

        return contracts, details

    @staticmethod
    def max_loss_position_sizing(
        ic: IronCondor,
        account_value: float,
        max_loss_pct: float = 0.02
    ) -> int:
        """Size position based on maximum acceptable loss.

        Conservative approach: limit max loss to a fixed percentage of account.

        Args:
            ic: IronCondor to size
            account_value: Total account value
            max_loss_pct: Maximum loss as % of account (default 0.02 = 2%)

        Returns:
            Number of contracts

        Example:
            >>> # Don't risk more than 2% of account
            >>> contracts = PositionSizer.max_loss_position_sizing(
            >>>     ic, account_value=100000, max_loss_pct=0.02
            >>> )
        """
        max_acceptable_loss = account_value * max_loss_pct
        max_loss_per_contract = ic.max_loss * 100

        if max_loss_per_contract <= 0:
            return 0

        contracts = int(max_acceptable_loss / max_loss_per_contract)

        logger.info(
            "Max loss sizing: %d contracts (max loss $%.2f = %.2f%% of account)",
            contracts, max_loss_per_contract * contracts, max_loss_pct * 100
        )

        return max(0, contracts)
