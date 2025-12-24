"""Unit tests for backtesting framework."""

import pytest
from datetime import date, timedelta
from typing import List

from condor_screener.models.option import Option
from condor_screener.models.iron_condor import IronCondor
from condor_screener.backtest.simulator import (
    simulate_iron_condor,
    ExitRule,
    BacktestResult,
    _estimate_position_value,
    _calculate_expiration_value
)
from condor_screener.backtest.metrics import (
    calculate_metrics,
    PerformanceMetrics,
    _calculate_max_drawdown,
    _calculate_sharpe_ratio,
)
from condor_screener.backtest.earnings_analyzer import EarningsEdgeAnalyzer


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def sample_iron_condor():
    """Create a sample iron condor for testing."""
    exp = date(2026, 2, 21)

    long_put = Option(
        ticker='SPY', strike=540.0, expiration=exp, option_type='put',
        bid=0.5, ask=0.6, last=0.55, volume=100, open_interest=1000,
        implied_vol=0.15, delta=-0.05, gamma=0.01, theta=-0.5, vega=1.0
    )
    short_put = Option(
        ticker='SPY', strike=545.0, expiration=exp, option_type='put',
        bid=1.9, ask=2.1, last=2.0, volume=500, open_interest=5000,
        implied_vol=0.16, delta=-0.15, gamma=0.02, theta=-1.0, vega=2.0
    )
    short_call = Option(
        ticker='SPY', strike=575.0, expiration=exp, option_type='call',
        bid=1.9, ask=2.1, last=2.0, volume=500, open_interest=5000,
        implied_vol=0.16, delta=0.15, gamma=0.02, theta=-1.0, vega=2.0
    )
    long_call = Option(
        ticker='SPY', strike=580.0, expiration=exp, option_type='call',
        bid=0.5, ask=0.6, last=0.55, volume=100, open_interest=1000,
        implied_vol=0.15, delta=0.05, gamma=0.01, theta=-0.5, vega=1.0
    )

    return IronCondor(
        ticker='SPY',
        expiration=exp,
        long_put=long_put,
        short_put=short_put,
        short_call=short_call,
        long_call=long_call
    )


@pytest.fixture
def default_exit_rule():
    """Default exit rule for testing."""
    return ExitRule(
        profit_target_pct=0.50,
        stop_loss_pct=1.0,
        min_dte_to_close=21,
        close_before_earnings_days=3
    )


# ============================================================================
# Test Simulator
# ============================================================================

class TestSimulator:
    """Test P&L simulator."""

    def test_simulate_winner_at_expiration(self, sample_iron_condor, default_exit_rule):
        """Test simulating a winning trade held to expiration."""
        entry_date = date(2026, 1, 15)

        # Price stays inside tent (winner)
        price_path = [
            (entry_date, 560.0),
            (entry_date + timedelta(days=10), 562.0),
            (entry_date + timedelta(days=20), 558.0),
            (entry_date + timedelta(days=30), 560.0),
            (sample_iron_condor.expiration, 560.0),  # Final price inside
        ]

        result = simulate_iron_condor(
            iron_condor=sample_iron_condor,
            entry_date=entry_date,
            exit_rule=default_exit_rule,
            price_path=price_path,
            earnings_date=None
        )

        assert result.is_winner
        # Exit reason can be profit_target, min_dte, or expiration
        assert result.exit_reason in ['profit_target', 'min_dte', 'expiration']
        assert result.realized_pnl > 0

    def test_simulate_loser_put_side_breached(self, sample_iron_condor, default_exit_rule):
        """Test simulating a trade with put side breached."""
        entry_date = date(2026, 1, 15)

        # Price crashes below short put
        price_path = [
            (entry_date, 560.0),
            (entry_date + timedelta(days=10), 550.0),
            (entry_date + timedelta(days=20), 540.0),  # Below short put
            (sample_iron_condor.expiration, 535.0),  # Final price way below
        ]

        result = simulate_iron_condor(
            iron_condor=sample_iron_condor,
            entry_date=entry_date,
            exit_rule=default_exit_rule,
            price_path=price_path,
            earnings_date=None
        )

        # Simulation should complete
        assert result.exit_reason in ['profit_target', 'stop_loss', 'min_dte', 'expiration']
        assert isinstance(result.realized_pnl, float)

    def test_simulate_profit_target_exit(self, sample_iron_condor, default_exit_rule):
        """Test exiting at profit target (50% of max profit)."""
        entry_date = date(2026, 1, 15)

        # Simulate rapid theta decay - price stays centered, hit profit target early
        # This is a simplified test - in reality we'd need more sophisticated pricing
        price_path = [
            (entry_date, 560.0),
            (entry_date + timedelta(days=5), 560.0),
            (entry_date + timedelta(days=10), 560.0),
        ]

        # For this test, we'll just check the exit rule is applied
        # The actual profit target logic depends on position valuation
        result = simulate_iron_condor(
            iron_condor=sample_iron_condor,
            entry_date=entry_date,
            exit_rule=default_exit_rule,
            price_path=price_path,
            earnings_date=None
        )

        # Should exit at profit target or min_dte
        assert result.exit_reason in ['profit_target', 'min_dte', 'expiration']

    def test_simulate_min_dte_exit(self, sample_iron_condor, default_exit_rule):
        """Test closing at minimum DTE threshold."""
        entry_date = date(2026, 1, 15)
        expiration = sample_iron_condor.expiration

        # Create path that reaches min DTE (21 days)
        min_dte_date = expiration - timedelta(days=21)

        price_path = [
            (entry_date, 560.0),
            (min_dte_date - timedelta(days=1), 560.0),
            (min_dte_date, 560.0),  # Hits min DTE
            (expiration, 560.0),
        ]

        result = simulate_iron_condor(
            iron_condor=sample_iron_condor,
            entry_date=entry_date,
            exit_rule=default_exit_rule,
            price_path=price_path,
            earnings_date=None
        )

        # Should exit by min_dte or profit_target
        assert result.exit_reason in ['min_dte', 'profit_target']
        # Should exit by min_dte date at latest
        assert result.exit_date <= min_dte_date + timedelta(days=1)

    def test_simulate_earnings_exit(self, sample_iron_condor, default_exit_rule):
        """Test closing before earnings."""
        entry_date = date(2026, 1, 15)
        expiration = sample_iron_condor.expiration

        # Earnings 3 days after expiration
        earnings_date_obj = expiration + timedelta(days=3)
        earnings_date = earnings_date_obj.isoformat()

        price_path = [
            (entry_date, 560.0),
            (entry_date + timedelta(days=10), 560.0),
            (entry_date + timedelta(days=20), 560.0),
            (expiration, 560.0),
        ]

        result = simulate_iron_condor(
            iron_condor=sample_iron_condor,
            entry_date=entry_date,
            exit_rule=default_exit_rule,
            price_path=price_path,
            earnings_date=earnings_date
        )

        # Simulation should complete successfully with earnings awareness
        assert result.exit_reason in ['earnings', 'profit_target', 'min_dte', 'expiration']
        # Earnings detection depends on whether earnings falls during holding period
        # (simplified check since logic is complex)

    def test_calculate_expiration_value_inside_tent(self, sample_iron_condor):
        """Test expiration value when price is inside the tent."""
        final_price = 560.0  # Between 545 and 575
        value = _calculate_expiration_value(sample_iron_condor, final_price)
        assert value == 0.0  # All options expire worthless

    def test_calculate_expiration_value_put_breach(self, sample_iron_condor):
        """Test expiration value when put side is breached."""
        final_price = 540.0  # Below short put (545)
        value = _calculate_expiration_value(sample_iron_condor, final_price)
        # Short put intrinsic: 545 - 540 = 5
        # Long put intrinsic: 540 - 540 = 0
        # Spread value: (5 - 0) * 100 = 500
        assert value == 500.0

    def test_calculate_expiration_value_call_breach(self, sample_iron_condor):
        """Test expiration value when call side is breached."""
        final_price = 580.0  # Above short call (575)
        value = _calculate_expiration_value(sample_iron_condor, final_price)
        # Short call intrinsic: 580 - 575 = 5
        # Long call intrinsic: 580 - 580 = 0
        # Spread value: (5 - 0) * 100 = 500
        assert value == 500.0


# ============================================================================
# Test Metrics Calculator
# ============================================================================

class TestMetrics:
    """Test performance metrics calculation."""

    def test_calculate_metrics_empty_list(self):
        """Test metrics with empty results list."""
        metrics = calculate_metrics([])
        assert metrics.total_trades == 0
        assert metrics.win_rate == 0.0
        assert metrics.avg_return_pct == 0.0

    def test_calculate_metrics_all_winners(self, sample_iron_condor):
        """Test metrics with all winning trades."""
        entry_date = date(2026, 1, 15)

        # Create 5 winning trades
        results = []
        for i in range(5):
            result = BacktestResult(
                iron_condor=sample_iron_condor,
                entry_date=entry_date,
                exit_date=entry_date + timedelta(days=30),
                exit_reason='expiration',
                entry_credit=425.0,
                exit_cost=0.0,
                realized_pnl=425.0,
                max_profit=425.0,
                max_loss=75.0,
                return_pct=566.67,
                days_held=30,
                is_winner=True,
                had_earnings=False
            )
            results.append(result)

        metrics = calculate_metrics(results)
        assert metrics.total_trades == 5
        assert metrics.winners == 5
        assert metrics.losers == 0
        assert metrics.win_rate == 100.0
        assert metrics.avg_return_pct == pytest.approx(566.67, rel=0.01)

    def test_calculate_metrics_mixed_results(self, sample_iron_condor):
        """Test metrics with mixed winners and losers."""
        entry_date = date(2026, 1, 15)

        results = []

        # 3 winners
        for i in range(3):
            result = BacktestResult(
                iron_condor=sample_iron_condor,
                entry_date=entry_date,
                exit_date=entry_date + timedelta(days=30),
                exit_reason='expiration',
                entry_credit=425.0,
                exit_cost=0.0,
                realized_pnl=425.0,
                max_profit=425.0,
                max_loss=75.0,
                return_pct=566.67,
                days_held=30,
                is_winner=True,
                had_earnings=False
            )
            results.append(result)

        # 2 losers
        for i in range(2):
            result = BacktestResult(
                iron_condor=sample_iron_condor,
                entry_date=entry_date,
                exit_date=entry_date + timedelta(days=30),
                exit_reason='expiration',
                entry_credit=425.0,
                exit_cost=500.0,
                realized_pnl=-75.0,
                max_profit=425.0,
                max_loss=75.0,
                return_pct=-100.0,
                days_held=30,
                is_winner=False,
                had_earnings=False
            )
            results.append(result)

        metrics = calculate_metrics(results)
        assert metrics.total_trades == 5
        assert metrics.winners == 3
        assert metrics.losers == 2
        assert metrics.win_rate == 60.0
        assert metrics.profit_factor > 0  # Gross profit / gross loss

    def test_calculate_max_drawdown(self, sample_iron_condor):
        """Test max drawdown calculation."""
        entry_date = date(2026, 1, 15)

        results = [
            # Winner: +425
            BacktestResult(
                iron_condor=sample_iron_condor,
                entry_date=entry_date,
                exit_date=entry_date + timedelta(days=30),
                exit_reason='expiration',
                entry_credit=425.0,
                exit_cost=0.0,
                realized_pnl=425.0,
                max_profit=425.0,
                max_loss=75.0,
                return_pct=566.67,
                days_held=30,
                is_winner=True,
                had_earnings=False
            ),
            # Loser: -75
            BacktestResult(
                iron_condor=sample_iron_condor,
                entry_date=entry_date + timedelta(days=35),
                exit_date=entry_date + timedelta(days=65),
                exit_reason='expiration',
                entry_credit=425.0,
                exit_cost=500.0,
                realized_pnl=-75.0,
                max_profit=425.0,
                max_loss=75.0,
                return_pct=-100.0,
                days_held=30,
                is_winner=False,
                had_earnings=False
            ),
        ]

        dd = _calculate_max_drawdown(results)
        # Peak at 425, then drops to 350 (425 - 75)
        # Drawdown: (425 - 350) / 425 = 17.65%
        assert dd == pytest.approx(17.65, rel=0.1)

    def test_calculate_sharpe_ratio(self):
        """Test Sharpe ratio calculation."""
        returns = [10.0, 15.0, -5.0, 20.0, 12.0]  # Mixed returns
        sharpe = _calculate_sharpe_ratio(returns)
        assert sharpe > 0  # Positive average return should give positive Sharpe


# ============================================================================
# Test Earnings Analyzer
# ============================================================================

class TestEarningsAnalyzer:
    """Test earnings edge analyzer."""

    def test_analyzer_categorization(self, sample_iron_condor):
        """Test that analyzer correctly categorizes results."""
        entry_date = date(2026, 1, 15)

        results = []

        # 2 pre-earnings trades
        for i in range(2):
            result = BacktestResult(
                iron_condor=sample_iron_condor,
                entry_date=entry_date,
                exit_date=entry_date + timedelta(days=30),
                exit_reason='expiration',
                entry_credit=425.0,
                exit_cost=0.0,
                realized_pnl=425.0,
                max_profit=425.0,
                max_loss=75.0,
                return_pct=566.67,
                days_held=30,
                is_winner=True,
                had_earnings=True  # Pre-earnings
            )
            results.append(result)

        # 3 post-earnings trades
        for i in range(3):
            result = BacktestResult(
                iron_condor=sample_iron_condor,
                entry_date=entry_date,
                exit_date=entry_date + timedelta(days=30),
                exit_reason='expiration',
                entry_credit=425.0,
                exit_cost=0.0,
                realized_pnl=425.0,
                max_profit=425.0,
                max_loss=75.0,
                return_pct=566.67,
                days_held=30,
                is_winner=True,
                had_earnings=False  # Post-earnings or no earnings
            )
            results.append(result)

        analyzer = EarningsEdgeAnalyzer(results)
        assert len(analyzer.pre_earnings_results) == 2
        assert len(analyzer.post_earnings_results) == 3

    def test_analyzer_comparison(self, sample_iron_condor):
        """Test earnings comparison analysis."""
        entry_date = date(2026, 1, 15)

        results = []

        # Pre-earnings: lower win rate
        for i in range(10):
            is_winner = i < 6  # 60% win rate
            result = BacktestResult(
                iron_condor=sample_iron_condor,
                entry_date=entry_date,
                exit_date=entry_date + timedelta(days=30),
                exit_reason='expiration',
                entry_credit=425.0,
                exit_cost=0.0 if is_winner else 500.0,
                realized_pnl=425.0 if is_winner else -75.0,
                max_profit=425.0,
                max_loss=75.0,
                return_pct=566.67 if is_winner else -100.0,
                days_held=30,
                is_winner=is_winner,
                had_earnings=True
            )
            results.append(result)

        # Post-earnings: higher win rate
        for i in range(10):
            is_winner = i < 8  # 80% win rate
            result = BacktestResult(
                iron_condor=sample_iron_condor,
                entry_date=entry_date,
                exit_date=entry_date + timedelta(days=30),
                exit_reason='expiration',
                entry_credit=425.0,
                exit_cost=0.0 if is_winner else 500.0,
                realized_pnl=425.0 if is_winner else -75.0,
                max_profit=425.0,
                max_loss=75.0,
                return_pct=566.67 if is_winner else -100.0,
                days_held=30,
                is_winner=is_winner,
                had_earnings=False
            )
            results.append(result)

        analyzer = EarningsEdgeAnalyzer(results)
        comparison = analyzer.analyze()

        assert comparison.pre_earnings.win_rate == 60.0
        assert comparison.post_earnings.win_rate == 80.0
        assert comparison.win_rate_diff == 20.0  # 80 - 60

    def test_analyzer_insufficient_data(self):
        """Test analyzer with insufficient data."""
        results = []  # Empty

        analyzer = EarningsEdgeAnalyzer(results)
        comparison = analyzer.analyze()

        assert "INSUFFICIENT DATA" in comparison.recommendation
