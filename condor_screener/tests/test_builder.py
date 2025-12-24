"""Unit tests for iron condor builder."""

import pytest
from datetime import date, timedelta

from condor_screener.builders.condor_builder import (
    StrategyConfig,
    generate_iron_condors,
    _group_by_expiration,
    _find_strike,
    _is_valid_condor,
)
from condor_screener.models.option import Option
from condor_screener.models.iron_condor import IronCondor


class TestStrategyConfig:
    """Test suite for StrategyConfig."""

    def test_strategy_config_defaults(self):
        """Test StrategyConfig with default values."""
        config = StrategyConfig()

        assert config.min_dte == 30
        assert config.max_dte == 45
        assert config.min_delta == 0.15
        assert config.max_delta == 0.25
        assert config.wing_width_put == 5.0
        assert config.wing_width_call == 5.0
        assert config.allow_asymmetric is True

    def test_strategy_config_custom(self):
        """Test StrategyConfig with custom values."""
        config = StrategyConfig(
            min_dte=20,
            max_dte=60,
            min_delta=0.10,
            max_delta=0.30,
            wing_width_put=10.0,
            wing_width_call=10.0,
            allow_asymmetric=False,
        )

        assert config.min_dte == 20
        assert config.max_dte == 60
        assert config.min_delta == 0.10
        assert config.max_delta == 0.30
        assert config.wing_width_put == 10.0
        assert config.wing_width_call == 10.0
        assert config.allow_asymmetric is False

    def test_strategy_config_from_dict(self):
        """Test creating StrategyConfig from dictionary."""
        config_dict = {
            'min_dte': 25,
            'max_dte': 50,
            'min_delta': 0.12,
            'max_delta': 0.28,
            'wing_width_put': 7.0,
            'wing_width_call': 7.0,
            'allow_asymmetric': False,
        }

        config = StrategyConfig.from_dict(config_dict)

        assert config.min_dte == 25
        assert config.max_dte == 50
        assert config.min_delta == 0.12
        assert config.max_delta == 0.28


class TestGroupByExpiration:
    """Test suite for _group_by_expiration."""

    def test_group_single_expiration(self):
        """Test grouping with single expiration."""
        exp = date.today() + timedelta(days=35)
        options = [
            Option(
                ticker="SPY", strike=580.0, expiration=exp, option_type="call",
                bid=5.0, ask=5.5, volume=1000, open_interest=5000,
                delta=0.20, implied_vol=0.25
            ),
            Option(
                ticker="SPY", strike=540.0, expiration=exp, option_type="put",
                bid=4.5, ask=5.0, volume=800, open_interest=4000,
                delta=-0.20, implied_vol=0.26
            ),
        ]

        grouped = _group_by_expiration(options)

        assert len(grouped) == 1
        assert exp in grouped
        assert len(grouped[exp]) == 2

    def test_group_multiple_expirations(self):
        """Test grouping with multiple expirations."""
        exp1 = date.today() + timedelta(days=35)
        exp2 = date.today() + timedelta(days=42)

        options = [
            Option(
                ticker="SPY", strike=580.0, expiration=exp1, option_type="call",
                bid=5.0, ask=5.5, volume=1000, open_interest=5000,
                delta=0.20, implied_vol=0.25
            ),
            Option(
                ticker="SPY", strike=580.0, expiration=exp2, option_type="call",
                bid=5.5, ask=6.0, volume=900, open_interest=4500,
                delta=0.22, implied_vol=0.24
            ),
        ]

        grouped = _group_by_expiration(options)

        assert len(grouped) == 2
        assert exp1 in grouped
        assert exp2 in grouped
        assert len(grouped[exp1]) == 1
        assert len(grouped[exp2]) == 1


class TestFindStrike:
    """Test suite for _find_strike."""

    def test_find_exact_strike(self):
        """Test finding exact strike match."""
        option = Option(
            ticker="SPY", strike=580.0, expiration=date.today() + timedelta(days=35),
            option_type="call", bid=5.0, ask=5.5, volume=1000,
            open_interest=5000, delta=0.20, implied_vol=0.25
        )

        strikes_dict = {580.0: option}
        result = _find_strike(strikes_dict, 580.0)

        assert result == option

    def test_find_close_strike(self):
        """Test finding strike within tolerance."""
        option = Option(
            ticker="SPY", strike=580.0, expiration=date.today() + timedelta(days=35),
            option_type="call", bid=5.0, ask=5.5, volume=1000,
            open_interest=5000, delta=0.20, implied_vol=0.25
        )

        strikes_dict = {580.0: option}
        result = _find_strike(strikes_dict, 580.3, tolerance=0.5)

        assert result == option

    def test_find_no_match(self):
        """Test when no strike is within tolerance."""
        option = Option(
            ticker="SPY", strike=580.0, expiration=date.today() + timedelta(days=35),
            option_type="call", bid=5.0, ask=5.5, volume=1000,
            open_interest=5000, delta=0.20, implied_vol=0.25
        )

        strikes_dict = {580.0: option}
        result = _find_strike(strikes_dict, 590.0, tolerance=0.5)

        assert result is None


class TestIsValidCondor:
    """Test suite for _is_valid_condor."""

    @pytest.fixture
    def valid_condor(self):
        """Create a valid iron condor."""
        exp = date.today() + timedelta(days=35)

        short_put = Option(
            ticker="SPY", strike=540.0, expiration=exp, option_type="put",
            bid=2.8, ask=3.0, volume=1000, open_interest=5000,
            delta=-0.20, implied_vol=0.25
        )
        long_put = Option(
            ticker="SPY", strike=535.0, expiration=exp, option_type="put",
            bid=2.0, ask=2.2, volume=800, open_interest=4000,
            delta=-0.15, implied_vol=0.24
        )
        short_call = Option(
            ticker="SPY", strike=580.0, expiration=exp, option_type="call",
            bid=2.8, ask=3.0, volume=1000, open_interest=5000,
            delta=0.20, implied_vol=0.25
        )
        long_call = Option(
            ticker="SPY", strike=585.0, expiration=exp, option_type="call",
            bid=2.0, ask=2.2, volume=800, open_interest=4000,
            delta=0.15, implied_vol=0.24
        )

        return IronCondor(
            ticker="SPY", expiration=exp,
            short_put=short_put, long_put=long_put,
            short_call=short_call, long_call=long_call,
        )

    def test_valid_condor(self, valid_condor):
        """Test valid iron condor passes validation."""
        assert _is_valid_condor(valid_condor) is True

    def test_invalid_no_credit(self):
        """Test condor with no net credit fails validation."""
        exp = date.today() + timedelta(days=35)

        # Create condor where long options cost more than short options
        short_put = Option(
            ticker="SPY", strike=540.0, expiration=exp, option_type="put",
            bid=1.0, ask=1.2, volume=1000, open_interest=5000,
            delta=-0.20, implied_vol=0.25
        )
        long_put = Option(
            ticker="SPY", strike=535.0, expiration=exp, option_type="put",
            bid=2.0, ask=2.2, volume=800, open_interest=4000,
            delta=-0.15, implied_vol=0.24
        )
        short_call = Option(
            ticker="SPY", strike=580.0, expiration=exp, option_type="call",
            bid=1.0, ask=1.2, volume=1000, open_interest=5000,
            delta=0.20, implied_vol=0.25
        )
        long_call = Option(
            ticker="SPY", strike=585.0, expiration=exp, option_type="call",
            bid=2.0, ask=2.2, volume=800, open_interest=4000,
            delta=0.15, implied_vol=0.24
        )

        condor = IronCondor(
            ticker="SPY", expiration=exp,
            short_put=short_put, long_put=long_put,
            short_call=short_call, long_call=long_call,
        )

        assert _is_valid_condor(condor) is False

    def test_invalid_arbitrage(self):
        """Test condor with arbitrage opportunity fails validation."""
        exp = date.today() + timedelta(days=35)

        # Create condor where credit exceeds wing width (impossible)
        short_put = Option(
            ticker="SPY", strike=540.0, expiration=exp, option_type="put",
            bid=4.9, ask=5.0, volume=1000, open_interest=5000,
            delta=-0.20, implied_vol=0.25
        )
        long_put = Option(
            ticker="SPY", strike=535.0, expiration=exp, option_type="put",
            bid=0.1, ask=0.2, volume=800, open_interest=4000,
            delta=-0.15, implied_vol=0.24
        )
        short_call = Option(
            ticker="SPY", strike=580.0, expiration=exp, option_type="call",
            bid=2.8, ask=3.0, volume=1000, open_interest=5000,
            delta=0.20, implied_vol=0.25
        )
        long_call = Option(
            ticker="SPY", strike=585.0, expiration=exp, option_type="call",
            bid=2.0, ask=2.2, volume=800, open_interest=4000,
            delta=0.15, implied_vol=0.24
        )

        condor = IronCondor(
            ticker="SPY", expiration=exp,
            short_put=short_put, long_put=long_put,
            short_call=short_call, long_call=long_call,
        )

        # Credit would be ~4.95 + 0.8 = 5.75, which exceeds put wing width of 5.0
        assert _is_valid_condor(condor) is False


class TestGenerateIronCondors:
    """Test suite for generate_iron_condors."""

    @pytest.fixture
    def complete_option_chain(self):
        """Create a complete option chain for testing."""
        exp = date.today() + timedelta(days=35)
        options = []

        # Create puts with various deltas and realistic prices
        # Prices decrease as strikes go lower (OTM puts get cheaper)
        put_strikes = [
            (530.0, -0.10, 1.0, 1.2),  # Far OTM
            (535.0, -0.15, 2.0, 2.2),  # Short put
            (540.0, -0.20, 3.0, 3.2),  # Short put
            (545.0, -0.25, 4.0, 4.2),  # Short put
        ]

        for strike, delta, bid, ask in put_strikes:
            options.append(Option(
                ticker="SPY", strike=strike, expiration=exp, option_type="put",
                bid=bid, ask=ask, volume=1000, open_interest=5000,
                delta=delta, implied_vol=0.25
            ))

        # Create calls with various deltas and realistic prices
        # Prices decrease as strikes go higher (OTM calls get cheaper)
        call_strikes = [
            (575.0, 0.25, 4.0, 4.2),  # Short call
            (580.0, 0.20, 3.0, 3.2),  # Short call
            (585.0, 0.15, 2.0, 2.2),  # Short call
            (590.0, 0.10, 1.0, 1.2),  # Far OTM
        ]

        for strike, delta, bid, ask in call_strikes:
            options.append(Option(
                ticker="SPY", strike=strike, expiration=exp, option_type="call",
                bid=bid, ask=ask, volume=1000, open_interest=5000,
                delta=delta, implied_vol=0.25
            ))

        return options

    def test_generate_no_options(self):
        """Test generation with empty option list."""
        config = StrategyConfig()
        condors = list(generate_iron_condors([], config))

        assert len(condors) == 0

    def test_generate_dte_filter(self, complete_option_chain):
        """Test DTE filtering."""
        # Change all options to have DTE outside range
        old_exp = date.today() + timedelta(days=35)
        new_exp = date.today() + timedelta(days=10)  # Too short

        options = []
        for opt in complete_option_chain:
            options.append(Option(
                ticker=opt.ticker, strike=opt.strike, expiration=new_exp,
                option_type=opt.option_type, bid=opt.bid, ask=opt.ask,
                volume=opt.volume, open_interest=opt.open_interest,
                delta=opt.delta, implied_vol=opt.implied_vol
            ))

        config = StrategyConfig(min_dte=30, max_dte=45)
        condors = list(generate_iron_condors(options, config))

        assert len(condors) == 0

    def test_generate_valid_condors(self, complete_option_chain):
        """Test generation of valid iron condors."""
        config = StrategyConfig(
            min_dte=30,
            max_dte=45,
            min_delta=0.15,
            max_delta=0.25,
            wing_width_put=5.0,
            wing_width_call=5.0,
        )

        condors = list(generate_iron_condors(complete_option_chain, config))

        # Should generate condors
        assert len(condors) > 0

        # Verify structure of first condor
        for condor in condors:
            assert condor.ticker == "SPY"
            assert condor.put_side_width == 5.0
            assert condor.call_side_width == 5.0
            assert condor.net_credit > 0

    def test_generate_delta_filtering(self, complete_option_chain):
        """Test that only options within delta range are used."""
        config = StrategyConfig(
            min_dte=30,
            max_dte=45,
            min_delta=0.15,
            max_delta=0.25,
            wing_width_put=5.0,
            wing_width_call=5.0,
        )

        condors = list(generate_iron_condors(complete_option_chain, config))

        for condor in condors:
            # Short puts should have delta between -0.25 and -0.15
            assert -0.25 <= condor.short_put.delta <= -0.15

            # Short calls should have delta between 0.15 and 0.25
            assert 0.15 <= condor.short_call.delta <= 0.25

    def test_generate_wing_width_matching(self, complete_option_chain):
        """Test that wing widths are matched correctly."""
        config = StrategyConfig(
            min_dte=30,
            max_dte=45,
            min_delta=0.15,
            max_delta=0.25,
            wing_width_put=5.0,
            wing_width_call=5.0,
        )

        condors = list(generate_iron_condors(complete_option_chain, config))

        for condor in condors:
            # Check that wing widths match configuration
            assert abs(condor.put_side_width - 5.0) < 1.0
            assert abs(condor.call_side_width - 5.0) < 1.0

    def test_generate_multiple_expirations(self):
        """Test generation with multiple expirations."""
        exp1 = date.today() + timedelta(days=35)
        exp2 = date.today() + timedelta(days=42)

        options = []

        # Add options for both expirations
        for exp in [exp1, exp2]:
            # Puts
            options.extend([
                Option(
                    ticker="SPY", strike=535.0, expiration=exp, option_type="put",
                    bid=2.0, ask=2.2, volume=1000, open_interest=5000,
                    delta=-0.15, implied_vol=0.25
                ),
                Option(
                    ticker="SPY", strike=540.0, expiration=exp, option_type="put",
                    bid=2.8, ask=3.0, volume=1000, open_interest=5000,
                    delta=-0.20, implied_vol=0.25
                ),
            ])

            # Calls
            options.extend([
                Option(
                    ticker="SPY", strike=580.0, expiration=exp, option_type="call",
                    bid=2.8, ask=3.0, volume=1000, open_interest=5000,
                    delta=0.20, implied_vol=0.25
                ),
                Option(
                    ticker="SPY", strike=585.0, expiration=exp, option_type="call",
                    bid=2.0, ask=2.2, volume=1000, open_interest=5000,
                    delta=0.15, implied_vol=0.24
                ),
            ])

        config = StrategyConfig(
            min_dte=30,
            max_dte=45,
            wing_width_put=5.0,
            wing_width_call=5.0,
        )

        condors = list(generate_iron_condors(options, config))

        # Should generate condors for both expirations
        assert len(condors) > 0

        expirations = {c.expiration for c in condors}
        assert exp1 in expirations
        assert exp2 in expirations

    def test_generate_asymmetric_wings(self):
        """Test generation with asymmetric wing widths."""
        exp = date.today() + timedelta(days=35)

        options = [
            # Puts
            Option(
                ticker="SPY", strike=530.0, expiration=exp, option_type="put",
                bid=1.5, ask=1.7, volume=800, open_interest=4000,
                delta=-0.12, implied_vol=0.24
            ),
            Option(
                ticker="SPY", strike=540.0, expiration=exp, option_type="put",
                bid=2.8, ask=3.0, volume=1000, open_interest=5000,
                delta=-0.20, implied_vol=0.25
            ),
            # Calls
            Option(
                ticker="SPY", strike=580.0, expiration=exp, option_type="call",
                bid=2.8, ask=3.0, volume=1000, open_interest=5000,
                delta=0.20, implied_vol=0.25
            ),
            Option(
                ticker="SPY", strike=595.0, expiration=exp, option_type="call",
                bid=1.2, ask=1.4, volume=700, open_interest=3500,
                delta=0.12, implied_vol=0.24
            ),
        ]

        config = StrategyConfig(
            min_dte=30,
            max_dte=45,
            wing_width_put=10.0,
            wing_width_call=15.0,
            allow_asymmetric=True,
        )

        condors = list(generate_iron_condors(options, config))

        # Should generate at least one condor
        assert len(condors) > 0

        # Verify asymmetric wings
        for condor in condors:
            assert abs(condor.put_side_width - 10.0) < 1.0
            assert abs(condor.call_side_width - 15.0) < 1.0
