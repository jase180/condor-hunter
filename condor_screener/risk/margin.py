"""Margin calculations for option positions.

Calculates margin requirements for various option strategies to help
traders understand capital requirements and buying power impact.
"""

import logging
from typing import Dict

from ..models.iron_condor import IronCondor

logger = logging.getLogger("condor_screener.margin")


class MarginCalculator:
    """Calculate margin requirements for option positions.

    Implements standard margin rules for iron condor and other spreads.
    These are approximate calculations - always verify with your broker.
    """

    @staticmethod
    def iron_condor_margin(
        ic: IronCondor,
        quantity: int = 1,
        initial: bool = True
    ) -> float:
        """Calculate margin requirement for iron condor position.

        Args:
            ic: IronCondor position
            quantity: Number of iron condors (default 1)
            initial: If True, calculate initial margin. If False, maintenance margin.

        Returns:
            Margin requirement in dollars

        Calculation:
            For iron condors, margin is typically:
            - Maximum wing width (put or call side) * 100 * quantity
            - Minus the net credit received
            - This assumes standard margin rules (not portfolio margin)

        Example:
            >>> ic = IronCondor(...)  # 5-wide wings, $2.00 credit
            >>> margin = MarginCalculator.iron_condor_margin(ic, quantity=10)
            >>> # margin = (5.0 * 100 * 10) - (2.00 * 100 * 10) = 5000 - 2000 = 3000

        Note:
            This is the maximum risk per iron condor. You can only lose
            the margin amount (wing width - credit) if the underlying
            moves through one of your short strikes.
        """
        # Maximum wing width determines margin requirement
        max_wing = max(ic.put_side_width, ic.call_side_width)

        # Gross margin requirement (before credit)
        gross_margin = max_wing * 100 * quantity

        # Credit received reduces margin requirement
        credit_received = ic.net_credit * 100 * quantity

        # Net margin = gross margin - credit
        # This is also equal to max loss
        net_margin = gross_margin - credit_received

        logger.debug(
            "Iron condor margin for %d contracts: gross=%.2f, credit=%.2f, net=%.2f",
            quantity, gross_margin, credit_received, net_margin
        )

        # Maintenance margin is typically the same for defined-risk spreads
        # Some brokers may reduce maintenance margin slightly
        if not initial:
            # Maintenance might be 90% of initial for some brokers
            # Conservative: assume same as initial
            pass

        return net_margin

    @staticmethod
    def vertical_spread_margin(
        width: float,
        credit: float,
        quantity: int = 1
    ) -> float:
        """Calculate margin for a vertical spread (credit or debit).

        Args:
            width: Width of the spread in dollars
            credit: Net credit received (positive) or debit paid (negative)
            quantity: Number of spreads

        Returns:
            Margin requirement in dollars

        For credit spreads:
            margin = (width - credit) * 100 * quantity

        For debit spreads:
            margin = debit * 100 * quantity (the cost to enter)
        """
        if credit > 0:
            # Credit spread: margin is max loss
            margin = (width - credit) * 100 * quantity
        else:
            # Debit spread: margin is the debit paid
            margin = abs(credit) * 100 * quantity

        return margin

    @staticmethod
    def buying_power_reduction(
        ic: IronCondor,
        quantity: int = 1
    ) -> float:
        """Calculate buying power reduction for iron condor.

        This is the amount of buying power consumed by the position.
        For most brokers, this equals the margin requirement.

        Args:
            ic: IronCondor position
            quantity: Number of contracts

        Returns:
            Buying power reduction in dollars
        """
        # For standard margin, BPR = margin requirement
        return MarginCalculator.iron_condor_margin(ic, quantity)

    @staticmethod
    def capital_efficiency(ic: IronCondor) -> float:
        """Calculate capital efficiency metric.

        Capital efficiency = (Max Profit / Margin Required) * 100

        Higher values indicate better capital efficiency.

        Args:
            ic: IronCondor position

        Returns:
            Capital efficiency as a percentage

        Example:
            >>> ic = IronCondor(...)  # $2.00 credit, $3.00 margin
            >>> efficiency = MarginCalculator.capital_efficiency(ic)
            >>> # efficiency = (200 / 300) * 100 = 66.67%
        """
        margin = MarginCalculator.iron_condor_margin(ic, quantity=1)

        if margin <= 0:
            return 0.0

        max_profit = ic.max_profit * 100  # Convert to dollars per contract

        efficiency = (max_profit / margin) * 100

        return efficiency

    @staticmethod
    def max_contracts_for_account(
        ic: IronCondor,
        account_value: float,
        max_allocation: float = 0.05
    ) -> int:
        """Calculate maximum number of contracts for account size.

        Args:
            ic: IronCondor position
            account_value: Total account value in dollars
            max_allocation: Maximum % of account to allocate (default 5%)

        Returns:
            Maximum number of iron condor contracts

        Example:
            >>> ic = IronCondor(...)  # $3000 margin per contract
            >>> max_contracts = MarginCalculator.max_contracts_for_account(
            >>>     ic, account_value=100000, max_allocation=0.10
            >>> )
            >>> # max_contracts = floor(100000 * 0.10 / 3000) = 3
        """
        max_capital = account_value * max_allocation
        margin_per_contract = MarginCalculator.iron_condor_margin(ic, quantity=1)

        if margin_per_contract <= 0:
            return 0

        max_contracts = int(max_capital / margin_per_contract)

        logger.info(
            "Max contracts for $%.2f account with %.1f%% allocation: %d",
            account_value, max_allocation * 100, max_contracts
        )

        return max_contracts

    @staticmethod
    def margin_summary(ic: IronCondor, quantity: int = 1) -> Dict[str, float]:
        """Get comprehensive margin summary for iron condor.

        Args:
            ic: IronCondor position
            quantity: Number of contracts

        Returns:
            Dictionary with margin details

        Example:
            >>> summary = MarginCalculator.margin_summary(ic, quantity=10)
            >>> print(summary)
            {
                'margin_required': 3000.0,
                'credit_received': 2000.0,
                'max_profit': 2000.0,
                'max_loss': 3000.0,
                'buying_power_reduction': 3000.0,
                'capital_efficiency': 66.67,
                'return_on_margin': 66.67
            }
        """
        margin = MarginCalculator.iron_condor_margin(ic, quantity)
        credit = ic.net_credit * 100 * quantity
        max_profit = ic.max_profit * 100 * quantity
        max_loss = ic.max_loss * 100 * quantity
        bpr = MarginCalculator.buying_power_reduction(ic, quantity)
        efficiency = MarginCalculator.capital_efficiency(ic)

        # Return on margin = max profit / margin * 100
        rom = (max_profit / margin * 100) if margin > 0 else 0.0

        return {
            'margin_required': margin,
            'credit_received': credit,
            'max_profit': max_profit,
            'max_loss': max_loss,
            'buying_power_reduction': bpr,
            'capital_efficiency': efficiency,
            'return_on_margin': rom,
            'quantity': quantity,
            'per_contract_margin': margin / quantity if quantity > 0 else 0.0,
        }
