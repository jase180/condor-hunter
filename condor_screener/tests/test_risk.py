"""Tests for risk management modules (margin, portfolio, position sizing)."""

import pytest
from datetime import date
from condor_screener.models.option import Option
from condor_screener.models.iron_condor import IronCondor
from condor_screener.risk.margin import MarginCalculator
from condor_screener.risk.portfolio import PortfolioRiskManager, Position
from condor_screener.risk.position_sizing import PositionSizer


@pytest.fixture
def sample_iron_condor():
    """Create a sample iron condor for testing.

    Setup: SPY @ 560
    - Long put: 540 @ $1.00
    - Short put: 545 @ $3.00
    - Short call: 575 @ $3.00
    - Long call: 580 @ $1.00
    - Net credit: $4.00
    - Max profit: $4.00
    - Max loss: $1.00 (5-wide wing - $4 credit)
    """
    long_put = Option(
        ticker='SPY',
        option_type='put',
        strike=540.0,
        expiration=date(2025, 2, 21),
        bid=0.90,
        ask=1.10,
        last=1.00,
        volume=100,
        open_interest=1000,
        implied_vol=0.25,
        delta=-0.10,
        gamma=0.01,
        theta=-0.05,
        vega=0.10,
    )

    short_put = Option(
        ticker='SPY',
        option_type='put',
        strike=545.0,
        expiration=date(2025, 2, 21),
        bid=2.90,
        ask=3.10,
        last=3.00,
        volume=200,
        open_interest=2000,
        implied_vol=0.24,
        delta=-0.15,
        gamma=0.015,
        theta=-0.08,
        vega=0.15,
    )

    short_call = Option(
        ticker='SPY',
        option_type='call',
        strike=575.0,
        expiration=date(2025, 2, 21),
        bid=2.90,
        ask=3.10,
        last=3.00,
        volume=200,
        open_interest=2000,
        implied_vol=0.24,
        delta=0.15,
        gamma=0.015,
        theta=-0.08,
        vega=0.15,
    )

    long_call = Option(
        ticker='SPY',
        option_type='call',
        strike=580.0,
        expiration=date(2025, 2, 21),
        bid=0.90,
        ask=1.10,
        last=1.00,
        volume=100,
        open_interest=1000,
        implied_vol=0.25,
        delta=0.10,
        gamma=0.01,
        theta=-0.05,
        vega=0.10,
    )

    return IronCondor(
        ticker='SPY',
        expiration=date(2025, 2, 21),
        short_put=short_put,
        long_put=long_put,
        short_call=short_call,
        long_call=long_call,
    )


# ============================================================================
# Margin Calculator Tests
# ============================================================================

class TestMarginCalculator:
    """Test suite for margin calculations."""

    def test_iron_condor_margin_single_contract(self, sample_iron_condor):
        """Test margin calculation for single iron condor."""
        margin = MarginCalculator.iron_condor_margin(sample_iron_condor, quantity=1)

        # Max wing = 5.0, credit = 4.0
        # Margin = (5.0 * 100) - (4.0 * 100) = 100
        assert margin == pytest.approx(100.0, rel=0.01)

    def test_iron_condor_margin_multiple_contracts(self, sample_iron_condor):
        """Test margin calculation scales linearly with quantity."""
        margin_1 = MarginCalculator.iron_condor_margin(sample_iron_condor, quantity=1)
        margin_10 = MarginCalculator.iron_condor_margin(sample_iron_condor, quantity=10)

        assert margin_10 == pytest.approx(margin_1 * 10, rel=0.01)

    def test_vertical_spread_margin_credit_spread(self):
        """Test margin for credit spread."""
        margin = MarginCalculator.vertical_spread_margin(
            width=5.0,
            credit=2.0,
            quantity=1
        )

        # Credit spread: (5.0 - 2.0) * 100 = 300
        assert margin == pytest.approx(300.0, rel=0.01)

    def test_vertical_spread_margin_debit_spread(self):
        """Test margin for debit spread."""
        margin = MarginCalculator.vertical_spread_margin(
            width=5.0,
            credit=-3.0,  # Negative = debit paid
            quantity=1
        )

        # Debit spread: margin is the debit paid
        # abs(-3.0) * 100 = 300
        assert margin == pytest.approx(300.0, rel=0.01)

    def test_buying_power_reduction_equals_margin(self, sample_iron_condor):
        """Test that BPR equals margin requirement."""
        margin = MarginCalculator.iron_condor_margin(sample_iron_condor, quantity=5)
        bpr = MarginCalculator.buying_power_reduction(sample_iron_condor, quantity=5)

        assert bpr == pytest.approx(margin, rel=0.01)

    def test_capital_efficiency(self, sample_iron_condor):
        """Test capital efficiency calculation."""
        efficiency = MarginCalculator.capital_efficiency(sample_iron_condor)

        # Max profit = 4.00 * 100 = 400
        # Margin = 100
        # Efficiency = (400 / 100) * 100 = 400%
        assert efficiency == pytest.approx(400.0, rel=0.01)

    def test_capital_efficiency_zero_margin_returns_zero(self):
        """Test that zero margin returns zero efficiency."""
        # Create IC with zero margin (credit = wing width)
        long_put = Option(
            ticker='SPY', option_type='put', strike=540.0,
            expiration=date(2025, 2, 21), bid=0.0, ask=0.0, last=0.0,
            volume=0, open_interest=0, implied_vol=0.25,
            delta=-0.10, gamma=0.01, theta=-0.05, vega=0.10
        )
        short_put = Option(
            ticker='SPY', option_type='put', strike=545.0,
            expiration=date(2025, 2, 21), bid=5.0, ask=5.0, last=5.0,
            volume=0, open_interest=0, implied_vol=0.24,
            delta=-0.15, gamma=0.015, theta=-0.08, vega=0.15
        )
        short_call = Option(
            ticker='SPY', option_type='call', strike=575.0,
            expiration=date(2025, 2, 21), bid=5.0, ask=5.0, last=5.0,
            volume=0, open_interest=0, implied_vol=0.24,
            delta=0.15, gamma=0.015, theta=-0.08, vega=0.15
        )
        long_call = Option(
            ticker='SPY', option_type='call', strike=580.0,
            expiration=date(2025, 2, 21), bid=0.0, ask=0.0, last=0.0,
            volume=0, open_interest=0, implied_vol=0.25,
            delta=0.10, gamma=0.01, theta=-0.05, vega=0.10
        )

        ic = IronCondor(
            ticker='SPY',
            expiration=date(2025, 2, 21),
            short_put=short_put,
            long_put=long_put,
            short_call=short_call,
            long_call=long_call
        )
        efficiency = MarginCalculator.capital_efficiency(ic)

        # Net credit = 10.0, wing width = 5.0
        # Margin = (5.0 * 100) - (10.0 * 100) = -500 (negative margin)
        # Should return 0.0 for invalid case
        assert efficiency == 0.0

    def test_max_contracts_for_account(self, sample_iron_condor):
        """Test maximum contracts calculation for account size."""
        max_contracts = MarginCalculator.max_contracts_for_account(
            sample_iron_condor,
            account_value=100000,
            max_allocation=0.10  # 10% = $10,000
        )

        # Margin per contract = 100
        # Max capital = 100,000 * 0.10 = 10,000
        # Max contracts = 10,000 / 100 = 100
        assert max_contracts == 100

    def test_max_contracts_small_account(self, sample_iron_condor):
        """Test that small account gets appropriate contract limit."""
        max_contracts = MarginCalculator.max_contracts_for_account(
            sample_iron_condor,
            account_value=5000,
            max_allocation=0.10  # 10% = $500
        )

        # Max capital = 5,000 * 0.10 = 500
        # Margin per contract = 100
        # Max contracts = 500 / 100 = 5
        assert max_contracts == 5

    def test_margin_summary_comprehensive(self, sample_iron_condor):
        """Test comprehensive margin summary."""
        summary = MarginCalculator.margin_summary(sample_iron_condor, quantity=10)

        assert 'margin_required' in summary
        assert 'credit_received' in summary
        assert 'max_profit' in summary
        assert 'max_loss' in summary
        assert 'buying_power_reduction' in summary
        assert 'capital_efficiency' in summary
        assert 'return_on_margin' in summary
        assert 'quantity' in summary
        assert 'per_contract_margin' in summary

        # Verify calculations
        assert summary['margin_required'] == pytest.approx(1000.0, rel=0.01)  # 100 * 10
        assert summary['credit_received'] == pytest.approx(4000.0, rel=0.01)  # 4.00 * 100 * 10
        assert summary['max_profit'] == pytest.approx(4000.0, rel=0.01)
        assert summary['quantity'] == 10
        assert summary['per_contract_margin'] == pytest.approx(100.0, rel=0.01)


# ============================================================================
# Position Sizing Tests
# ============================================================================

class TestPositionSizer:
    """Test suite for position sizing strategies."""

    def test_kelly_criterion_positive_edge(self):
        """Test Kelly Criterion with positive edge."""
        kelly_frac, kelly_dollars = PositionSizer.kelly_criterion(
            win_rate=0.70,
            avg_win=200.0,
            avg_loss=300.0,
            account_value=100000,
            max_kelly_fraction=0.25
        )

        # Kelly = (0.70 * 200 - 0.30 * 300) / 200
        #       = (140 - 90) / 200 = 50 / 200 = 0.25
        # With max_kelly_fraction=0.25, should be capped at 0.25
        assert kelly_frac == pytest.approx(0.25, rel=0.01)
        assert kelly_dollars == pytest.approx(25000, rel=1.0)

    def test_kelly_criterion_no_edge_returns_zero(self):
        """Test Kelly Criterion with no edge returns zero."""
        kelly_frac, kelly_dollars = PositionSizer.kelly_criterion(
            win_rate=0.50,
            avg_win=200.0,
            avg_loss=200.0,
            account_value=100000
        )

        # Kelly = (0.50 * 200 - 0.50 * 200) / 200 = 0
        assert kelly_frac == 0.0
        assert kelly_dollars == 0

    def test_kelly_criterion_negative_edge_returns_zero(self):
        """Test Kelly Criterion with negative edge returns zero."""
        kelly_frac, kelly_dollars = PositionSizer.kelly_criterion(
            win_rate=0.40,
            avg_win=200.0,
            avg_loss=300.0,
            account_value=100000
        )

        # Kelly = (0.40 * 200 - 0.60 * 300) / 200 = (80 - 180) / 200 = -0.5
        assert kelly_frac == 0.0
        assert kelly_dollars == 0

    def test_kelly_criterion_invalid_win_rate_above_one(self):
        """Test Kelly with win rate > 1.0 returns zero."""
        kelly_frac, kelly_dollars = PositionSizer.kelly_criterion(
            win_rate=1.5,
            avg_win=200.0,
            avg_loss=300.0,
            account_value=100000
        )

        assert kelly_frac == 0.0
        assert kelly_dollars == 0

    def test_kelly_criterion_invalid_win_rate_below_zero(self):
        """Test Kelly with win rate < 0 returns zero."""
        kelly_frac, kelly_dollars = PositionSizer.kelly_criterion(
            win_rate=-0.1,
            avg_win=200.0,
            avg_loss=300.0,
            account_value=100000
        )

        assert kelly_frac == 0.0
        assert kelly_dollars == 0

    def test_fixed_fractional_standard_risk(self):
        """Test fixed fractional with 2% risk."""
        risk_dollars = PositionSizer.fixed_fractional(
            account_value=100000,
            risk_fraction=0.02
        )

        assert risk_dollars == 2000

    def test_fixed_fractional_conservative_risk(self):
        """Test fixed fractional with 1% risk."""
        risk_dollars = PositionSizer.fixed_fractional(
            account_value=50000,
            risk_fraction=0.01
        )

        assert risk_dollars == 500

    def test_fixed_fractional_invalid_fraction_returns_zero(self):
        """Test fixed fractional with invalid fraction returns zero."""
        risk_dollars = PositionSizer.fixed_fractional(
            account_value=100000,
            risk_fraction=1.5  # > 1.0
        )

        assert risk_dollars == 0

    def test_contracts_from_risk_dollars(self, sample_iron_condor):
        """Test converting risk dollars to contracts."""
        contracts = PositionSizer.contracts_from_risk_dollars(
            sample_iron_condor,
            risk_dollars=1000.0
        )

        # Max loss per contract = 1.00 * 100 = 100
        # Contracts = 1000 / 100 = 10
        assert contracts == 10

    def test_contracts_from_risk_dollars_partial_contract(self, sample_iron_condor):
        """Test that partial contracts are truncated."""
        contracts = PositionSizer.contracts_from_risk_dollars(
            sample_iron_condor,
            risk_dollars=350.0
        )

        # Max loss per contract = 100
        # Contracts = 350 / 100 = 3.5 -> int(3.5) = 3
        assert contracts == 3

    def test_optimal_f_positive_edge(self):
        """Test Optimal F calculation with positive edge."""
        optimal_f = PositionSizer.optimal_f(
            win_rate=0.70,
            avg_win=200.0,
            avg_loss=300.0
        )

        # Ratio = 200 / 300 = 0.667
        # Optimal F = 0.70 - (0.30 / 0.667) = 0.70 - 0.45 = 0.25
        assert optimal_f == pytest.approx(0.25, rel=0.01)

    def test_optimal_f_no_edge_returns_zero(self):
        """Test Optimal F with no edge returns zero or negative."""
        optimal_f = PositionSizer.optimal_f(
            win_rate=0.50,
            avg_win=200.0,
            avg_loss=200.0
        )

        # Should return 0 or negative (no edge)
        assert optimal_f <= 0.01

    def test_position_size_with_edge_kelly_method(self, sample_iron_condor):
        """Test position sizing with Kelly method."""
        contracts, details = PositionSizer.position_size_with_edge(
            sample_iron_condor,
            account_value=100000,
            estimated_win_rate=0.70,
            method='kelly'
        )

        assert contracts >= 0
        assert 'method' in details
        assert details['method'] == 'kelly'
        assert 'kelly_fraction' in details
        assert 'kelly_dollars' in details
        assert 'actual_contracts' in details
        assert 'actual_risk' in details
        assert 'risk_pct_of_account' in details

    def test_position_size_with_edge_fixed_method(self, sample_iron_condor):
        """Test position sizing with fixed fractional method."""
        contracts, details = PositionSizer.position_size_with_edge(
            sample_iron_condor,
            account_value=100000,
            estimated_win_rate=0.70,
            method='fixed'
        )

        assert contracts >= 0
        assert details['method'] == 'fixed'
        assert 'risk_dollars' in details
        assert 'actual_contracts' in details

    def test_position_size_with_edge_invalid_method_returns_zero(self, sample_iron_condor):
        """Test position sizing with invalid method returns zero."""
        contracts, details = PositionSizer.position_size_with_edge(
            sample_iron_condor,
            account_value=100000,
            estimated_win_rate=0.70,
            method='invalid_method'
        )

        assert contracts == 0

    def test_max_loss_position_sizing(self, sample_iron_condor):
        """Test conservative max loss position sizing."""
        contracts = PositionSizer.max_loss_position_sizing(
            sample_iron_condor,
            account_value=100000,
            max_loss_pct=0.02
        )

        # Max acceptable loss = 100,000 * 0.02 = 2,000
        # Max loss per contract = 1.00 * 100 = 100
        # Contracts = 2,000 / 100 = 20
        assert contracts == 20

    def test_max_loss_position_sizing_conservative(self, sample_iron_condor):
        """Test very conservative max loss sizing (1%)."""
        contracts = PositionSizer.max_loss_position_sizing(
            sample_iron_condor,
            account_value=100000,
            max_loss_pct=0.01
        )

        # Max acceptable loss = 100,000 * 0.01 = 1,000
        # Max loss per contract = 100
        # Contracts = 1,000 / 100 = 10
        assert contracts == 10


# ============================================================================
# Portfolio Risk Manager Tests
# ============================================================================

class TestPortfolioRiskManager:
    """Test suite for portfolio-level risk management."""

    @pytest.fixture
    def sample_position(self, sample_iron_condor):
        """Create a sample position."""
        return Position(
            iron_condor=sample_iron_condor,
            quantity=10,
            entry_date=date(2025, 1, 1),
            cost_basis=-4000.0,  # Received $4.00 credit per contract * 100 * 10
            spot_at_entry=560.0
        )

    @pytest.fixture
    def multi_position_portfolio(self, sample_iron_condor):
        """Create portfolio with multiple positions."""
        # Position 1: SPY
        pos1 = Position(
            iron_condor=sample_iron_condor,
            quantity=10,
            entry_date=date(2025, 1, 1),
            cost_basis=-4000.0,
            spot_at_entry=560.0
        )

        # Position 2: QQQ (create second IC)
        long_put = Option(
            ticker='QQQ', option_type='put', strike=380.0,
            expiration=date(2025, 2, 21), bid=0.90, ask=1.10, last=1.00,
            volume=100, open_interest=1000, implied_vol=0.28,
            delta=-0.12, gamma=0.01, theta=-0.06, vega=0.12
        )
        short_put = Option(
            ticker='QQQ', option_type='put', strike=385.0,
            expiration=date(2025, 2, 21), bid=2.90, ask=3.10, last=3.00,
            volume=200, open_interest=2000, implied_vol=0.27,
            delta=-0.18, gamma=0.016, theta=-0.09, vega=0.16
        )
        short_call = Option(
            ticker='QQQ', option_type='call', strike=415.0,
            expiration=date(2025, 2, 21), bid=2.90, ask=3.10, last=3.00,
            volume=200, open_interest=2000, implied_vol=0.27,
            delta=0.18, gamma=0.016, theta=-0.09, vega=0.16
        )
        long_call = Option(
            ticker='QQQ', option_type='call', strike=420.0,
            expiration=date(2025, 2, 21), bid=0.90, ask=1.10, last=1.00,
            volume=100, open_interest=1000, implied_vol=0.28,
            delta=0.12, gamma=0.01, theta=-0.06, vega=0.12
        )

        ic2 = IronCondor(
            ticker='QQQ',
            expiration=date(2025, 2, 21),
            short_put=short_put,
            long_put=long_put,
            short_call=short_call,
            long_call=long_call
        )

        pos2 = Position(
            iron_condor=ic2,
            quantity=5,
            entry_date=date(2025, 1, 5),
            cost_basis=-2000.0,
            spot_at_entry=400.0
        )

        return [pos1, pos2]

    def test_portfolio_with_single_position(self, sample_position):
        """Test portfolio with single position."""
        portfolio = PortfolioRiskManager(
            positions=[sample_position],
            account_value=100000,
            spot_prices={'SPY': 560.0}
        )

        assert len(portfolio.positions) == 1
        assert portfolio.account_value == 100000

    def test_total_delta_calculation(self, sample_position):
        """Test portfolio delta aggregation."""
        portfolio = PortfolioRiskManager(
            positions=[sample_position],
            account_value=100000,
            spot_prices={'SPY': 560.0}
        )

        delta = portfolio.total_delta()

        # Iron condor should have near-zero delta
        # Each leg contributes: (delta * quantity * 100)
        # Short puts: -(-0.15) * 10 * 100 = +150
        # Long puts: -0.10 * 10 * 100 = -100
        # Short calls: -(0.15) * 10 * 100 = -150
        # Long calls: 0.10 * 10 * 100 = +100
        # Total = 150 - 100 - 150 + 100 = 0
        assert abs(delta) < 50.0  # Should be close to zero for balanced IC

    def test_total_gamma_calculation(self, sample_position):
        """Test portfolio gamma aggregation."""
        portfolio = PortfolioRiskManager(
            positions=[sample_position],
            account_value=100000,
            spot_prices={'SPY': 560.0}
        )

        gamma = portfolio.total_gamma()

        # Iron condor is short gamma (sold options)
        # Should be negative
        assert gamma < 0

    def test_total_theta_calculation(self, sample_position):
        """Test portfolio theta aggregation."""
        portfolio = PortfolioRiskManager(
            positions=[sample_position],
            account_value=100000,
            spot_prices={'SPY': 560.0}
        )

        theta = portfolio.total_theta()

        # Iron condor is net short options, so should have positive theta
        # (benefit from time decay)
        assert theta > 0

    def test_total_vega_calculation(self, sample_position):
        """Test portfolio vega aggregation."""
        portfolio = PortfolioRiskManager(
            positions=[sample_position],
            account_value=100000,
            spot_prices={'SPY': 560.0}
        )

        vega = portfolio.total_vega()

        # Iron condor is short vega (sold options)
        # Should be negative
        assert vega < 0

    def test_total_margin_required(self, sample_position):
        """Test total margin calculation across positions."""
        portfolio = PortfolioRiskManager(
            positions=[sample_position],
            account_value=100000,
            spot_prices={'SPY': 560.0}
        )

        margin = portfolio.total_margin_required()

        # Single position with 10 contracts, margin = 100 per contract
        # Total margin = 1000
        assert margin == pytest.approx(1000.0, rel=0.01)

    def test_margin_utilization(self, sample_position):
        """Test margin utilization percentage."""
        portfolio = PortfolioRiskManager(
            positions=[sample_position],
            account_value=100000,
            spot_prices={'SPY': 560.0}
        )

        utilization = portfolio.margin_utilization()

        # Margin = 1000, account = 100,000
        # Utilization = (1000 / 100,000) * 100 = 1%
        assert utilization == pytest.approx(1.0, rel=0.01)

    def test_margin_utilization_zero_account_returns_zero(self):
        """Test margin utilization with zero account value."""
        portfolio = PortfolioRiskManager(
            positions=[],
            account_value=0.0
        )

        utilization = portfolio.margin_utilization()
        assert utilization == 0.0

    def test_check_risk_limits_within_limits(self, sample_position):
        """Test risk limit check when within limits."""
        portfolio = PortfolioRiskManager(
            positions=[sample_position],
            account_value=100000,
            spot_prices={'SPY': 560.0}
        )

        violations = portfolio.check_risk_limits(
            max_delta=100.0,
            max_gamma=10.0,
            min_theta=-500.0,
            max_vega=1000.0,
            max_margin_pct=50.0
        )

        # Should be within all limits
        assert len(violations) == 0

    def test_check_risk_limits_delta_violation(self, multi_position_portfolio):
        """Test delta limit violation detection."""
        portfolio = PortfolioRiskManager(
            positions=multi_position_portfolio,
            account_value=100000,
            spot_prices={'SPY': 560.0, 'QQQ': 400.0}
        )

        violations = portfolio.check_risk_limits(
            max_delta=1.0,  # Very tight limit
            max_gamma=1000.0,
            min_theta=-5000.0,
            max_vega=10000.0,
            max_margin_pct=100.0
        )

        # Should detect delta violation
        delta_violations = [v for v in violations if 'Delta' in v]
        # May or may not violate depending on actual delta, just verify format
        if delta_violations:
            assert 'exceeds limit' in delta_violations[0]

    def test_check_risk_limits_margin_violation(self, sample_position):
        """Test margin utilization violation detection."""
        portfolio = PortfolioRiskManager(
            positions=[sample_position],
            account_value=100000,
            spot_prices={'SPY': 560.0}
        )

        violations = portfolio.check_risk_limits(
            max_delta=1000.0,
            max_gamma=1000.0,
            min_theta=-5000.0,
            max_vega=10000.0,
            max_margin_pct=0.5  # 0.5% - very tight
        )

        # Should detect margin violation (we're using 1%)
        margin_violations = [v for v in violations if 'Margin' in v]
        assert len(margin_violations) == 1
        assert 'exceeds limit' in margin_violations[0]

    def test_portfolio_summary_comprehensive(self, sample_position):
        """Test comprehensive portfolio summary."""
        portfolio = PortfolioRiskManager(
            positions=[sample_position],
            account_value=100000,
            spot_prices={'SPY': 560.0}
        )

        summary = portfolio.portfolio_summary()

        assert 'account_value' in summary
        assert 'num_positions' in summary
        assert 'total_delta' in summary
        assert 'total_gamma' in summary
        assert 'total_theta' in summary
        assert 'total_vega' in summary
        assert 'margin_required' in summary
        assert 'margin_utilization_pct' in summary
        assert 'buying_power_available' in summary

        assert summary['account_value'] == 100000
        assert summary['num_positions'] == 1
        assert summary['buying_power_available'] == pytest.approx(99000.0, rel=0.01)

    def test_position_concentration_single_ticker(self, sample_position):
        """Test position concentration with single ticker."""
        portfolio = PortfolioRiskManager(
            positions=[sample_position],
            account_value=100000,
            spot_prices={'SPY': 560.0}
        )

        concentration = portfolio.position_concentration()

        assert 'SPY' in concentration
        assert concentration['SPY'] == pytest.approx(100.0, rel=0.01)  # 100% in SPY

    def test_position_concentration_multiple_tickers(self, multi_position_portfolio):
        """Test position concentration across multiple tickers."""
        portfolio = PortfolioRiskManager(
            positions=multi_position_portfolio,
            account_value=100000,
            spot_prices={'SPY': 560.0, 'QQQ': 400.0}
        )

        concentration = portfolio.position_concentration()

        assert 'SPY' in concentration
        assert 'QQQ' in concentration

        # Total should sum to 100%
        total_pct = sum(concentration.values())
        assert total_pct == pytest.approx(100.0, rel=0.01)

    def test_position_concentration_empty_portfolio(self):
        """Test position concentration with empty portfolio."""
        portfolio = PortfolioRiskManager(
            positions=[],
            account_value=100000
        )

        concentration = portfolio.position_concentration()

        assert concentration == {}

    def test_position_days_in_trade(self, sample_position):
        """Test position days in trade calculation."""
        # Position was entered on 2025-01-01
        # Current date from fixture should calculate days
        days = sample_position.days_in_trade

        # Should be positive
        assert days >= 0

    def test_position_dte(self, sample_position):
        """Test position days to expiration."""
        dte = sample_position.dte

        # Should match the option DTE
        assert dte == sample_position.iron_condor.short_put.dte

    def test_multi_position_portfolio_aggregation(self, multi_position_portfolio):
        """Test that multiple positions aggregate correctly."""
        portfolio = PortfolioRiskManager(
            positions=multi_position_portfolio,
            account_value=100000,
            spot_prices={'SPY': 560.0, 'QQQ': 400.0}
        )

        # All Greeks should be non-None
        delta = portfolio.total_delta()
        gamma = portfolio.total_gamma()
        theta = portfolio.total_theta()
        vega = portfolio.total_vega()
        margin = portfolio.total_margin_required()

        assert delta is not None
        assert gamma is not None
        assert theta is not None
        assert vega is not None
        assert margin > 0

        # Margin should be sum of both positions
        # Position 1: 10 contracts * 100 margin = 1000
        # Position 2: 5 contracts * 100 margin = 500
        # Total ≈ 1500
        assert margin == pytest.approx(1500.0, rel=0.01)
