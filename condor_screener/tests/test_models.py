"""Unit tests for data models (Option, IronCondor, Analytics)."""

import pytest
from datetime import date, timedelta

from condor_screener.models.option import Option
from condor_screener.models.iron_condor import IronCondor
from condor_screener.models.analytics import Analytics


class TestOption:
    """Test suite for Option model."""

    @pytest.fixture
    def sample_call(self):
        """Create a sample call option."""
        return Option(
            ticker="SPY",
            strike=580.0,
            expiration=date.today() + timedelta(days=35),
            option_type="call",
            bid=5.0,
            ask=5.5,
            volume=1000,
            open_interest=5000,
            delta=0.20,
            implied_vol=0.25,
            last=5.2,
            gamma=0.05,
            theta=-0.10,
            vega=0.30,
        )

    @pytest.fixture
    def sample_put(self):
        """Create a sample put option."""
        return Option(
            ticker="SPY",
            strike=540.0,
            expiration=date.today() + timedelta(days=35),
            option_type="put",
            bid=4.5,
            ask=5.0,
            volume=800,
            open_interest=4000,
            delta=-0.20,
            implied_vol=0.26,
            last=4.8,
        )

    def test_option_creation(self, sample_call):
        """Test basic option creation."""
        assert sample_call.ticker == "SPY"
        assert sample_call.strike == 580.0
        assert sample_call.option_type == "call"
        assert sample_call.delta == 0.20

    def test_option_immutable(self, sample_call):
        """Test that options are immutable (frozen dataclass)."""
        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            sample_call.strike = 590.0

    def test_mid_price(self, sample_call):
        """Test mid price calculation."""
        assert sample_call.mid == 5.25

    def test_bid_ask_spread_pct(self, sample_call):
        """Test bid-ask spread percentage calculation."""
        # (5.5 - 5.0) / 5.25 = 0.5 / 5.25 ≈ 0.0952
        assert abs(sample_call.bid_ask_spread_pct - 0.0952) < 0.001

    def test_bid_ask_spread_pct_zero_mid(self):
        """Test bid-ask spread when mid is zero."""
        option = Option(
            ticker="SPY",
            strike=100.0,
            expiration=date.today() + timedelta(days=30),
            option_type="call",
            bid=0.0,
            ask=0.0,
            volume=0,
            open_interest=0,
            delta=0.01,
            implied_vol=0.20,
        )
        assert option.bid_ask_spread_pct == float('inf')

    def test_dte(self, sample_call):
        """Test days to expiration calculation."""
        expected_dte = 35
        assert sample_call.dte == expected_dte

    def test_repr(self, sample_call):
        """Test string representation."""
        repr_str = repr(sample_call)
        assert "SPY" in repr_str
        assert "580" in repr_str
        assert "C" in repr_str  # Call option
        assert "0.200" in repr_str  # Delta

    def test_optional_greeks(self):
        """Test option with minimal fields (no optional greeks)."""
        option = Option(
            ticker="SPY",
            strike=500.0,
            expiration=date.today() + timedelta(days=30),
            option_type="put",
            bid=3.0,
            ask=3.5,
            volume=100,
            open_interest=500,
            delta=-0.15,
            implied_vol=0.22,
        )
        assert option.gamma is None
        assert option.theta is None
        assert option.vega is None
        assert option.last is None


class TestIronCondor:
    """Test suite for IronCondor model."""

    @pytest.fixture
    def condor_legs(self):
        """Create the four legs of an iron condor."""
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

        return short_put, long_put, short_call, long_call

    @pytest.fixture
    def sample_condor(self, condor_legs):
        """Create a valid iron condor."""
        short_put, long_put, short_call, long_call = condor_legs
        return IronCondor(
            ticker="SPY",
            expiration=short_put.expiration,
            short_put=short_put,
            long_put=long_put,
            short_call=short_call,
            long_call=long_call,
        )

    def test_iron_condor_creation(self, sample_condor):
        """Test basic iron condor creation."""
        assert sample_condor.ticker == "SPY"
        assert sample_condor.short_put.strike == 540.0
        assert sample_condor.long_put.strike == 535.0
        assert sample_condor.short_call.strike == 580.0
        assert sample_condor.long_call.strike == 585.0

    def test_iron_condor_immutable(self, sample_condor):
        """Test that iron condors are immutable."""
        with pytest.raises(Exception):
            sample_condor.ticker = "QQQ"

    def test_net_credit(self, sample_condor):
        """Test net credit calculation."""
        # Put spread: (2.9 - 2.1) = 0.8
        # Call spread: (2.9 - 2.1) = 0.8
        # Total: 1.6
        expected_credit = 1.6
        assert abs(sample_condor.net_credit - expected_credit) < 0.01

    def test_max_profit(self, sample_condor):
        """Test max profit equals net credit."""
        assert sample_condor.max_profit == sample_condor.net_credit

    def test_wing_widths(self, sample_condor):
        """Test wing width calculations."""
        assert sample_condor.put_side_width == 5.0
        assert sample_condor.call_side_width == 5.0

    def test_max_loss(self, sample_condor):
        """Test max loss calculation."""
        # Wing width (5.0) - net credit (1.6) = 3.4
        expected_max_loss = 3.4
        assert abs(sample_condor.max_loss - expected_max_loss) < 0.01

    def test_return_on_risk(self, sample_condor):
        """Test ROR calculation."""
        # (1.6 / 3.4) * 100 ≈ 47.06%
        expected_ror = (sample_condor.net_credit / sample_condor.max_loss) * 100
        assert abs(sample_condor.return_on_risk - expected_ror) < 0.1

    def test_breakevens(self, sample_condor):
        """Test breakeven calculations."""
        # Put side: 540 - 1.6 = 538.4
        # Call side: 580 + 1.6 = 581.6
        assert abs(sample_condor.put_side_breakeven - 538.4) < 0.01
        assert abs(sample_condor.call_side_breakeven - 581.6) < 0.01

    def test_is_symmetric(self, sample_condor):
        """Test symmetric wing detection."""
        assert sample_condor.is_symmetric is True

    def test_validation_different_tickers(self, condor_legs):
        """Test validation fails with different tickers."""
        short_put, long_put, short_call, long_call = condor_legs

        # Create put with different ticker
        bad_put = Option(
            ticker="QQQ", strike=short_put.strike, expiration=short_put.expiration,
            option_type="put", bid=2.8, ask=3.0, volume=1000,
            open_interest=5000, delta=-0.20, implied_vol=0.25
        )

        with pytest.raises(ValueError, match="same ticker"):
            IronCondor(
                ticker="SPY",
                expiration=short_put.expiration,
                short_put=bad_put,
                long_put=long_put,
                short_call=short_call,
                long_call=long_call,
            )

    def test_validation_different_expirations(self, condor_legs):
        """Test validation fails with different expirations."""
        short_put, long_put, short_call, long_call = condor_legs

        # Create call with different expiration
        bad_call = Option(
            ticker="SPY", strike=short_call.strike,
            expiration=date.today() + timedelta(days=60),
            option_type="call", bid=2.8, ask=3.0, volume=1000,
            open_interest=5000, delta=0.20, implied_vol=0.25
        )

        with pytest.raises(ValueError, match="same expiration"):
            IronCondor(
                ticker="SPY",
                expiration=short_put.expiration,
                short_put=short_put,
                long_put=long_put,
                short_call=bad_call,
                long_call=long_call,
            )

    def test_validation_wrong_option_types(self, condor_legs):
        """Test validation fails with wrong option types."""
        short_put, long_put, short_call, long_call = condor_legs

        # Use call where put should be
        with pytest.raises(ValueError, match="Put side must contain put"):
            IronCondor(
                ticker="SPY",
                expiration=short_put.expiration,
                short_put=short_call,  # Wrong type!
                long_put=long_put,
                short_call=short_call,
                long_call=long_call,
            )

    def test_validation_invalid_strike_order(self, condor_legs):
        """Test validation fails with invalid strike ordering."""
        short_put, long_put, short_call, long_call = condor_legs

        # Swap put strikes (short below long - invalid)
        with pytest.raises(ValueError, match="Short put strike must be above"):
            IronCondor(
                ticker="SPY",
                expiration=short_put.expiration,
                short_put=long_put,  # Swapped
                long_put=short_put,  # Swapped
                short_call=short_call,
                long_call=long_call,
            )

    def test_validation_overlapping_strikes(self, condor_legs):
        """Test validation fails when strikes overlap."""
        short_put, long_put, short_call, long_call = condor_legs

        # Create short call below short put (invalid)
        bad_call = Option(
            ticker="SPY", strike=530.0,  # Below short put!
            expiration=short_put.expiration,
            option_type="call", bid=2.8, ask=3.0, volume=1000,
            open_interest=5000, delta=0.20, implied_vol=0.25
        )

        with pytest.raises(ValueError, match="Short call strike must be above"):
            IronCondor(
                ticker="SPY",
                expiration=short_put.expiration,
                short_put=short_put,
                long_put=long_put,
                short_call=bad_call,
                long_call=long_call,
            )


class TestAnalytics:
    """Test suite for Analytics model."""

    @pytest.fixture
    def sample_analytics(self):
        """Create sample analytics object."""
        # Create minimal iron condor
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

        ic = IronCondor(
            ticker="SPY", expiration=exp,
            short_put=short_put, long_put=long_put,
            short_call=short_call, long_call=long_call,
        )

        return Analytics(
            iron_condor=ic,
            spot_price=560.0,
            expected_move_straddle=25.0,
            expected_move_iv=24.0,
            put_distance_dollars=20.0,
            call_distance_dollars=20.0,
            put_distance_pct=3.57,
            call_distance_pct=3.57,
            iv_rank=65.0,
            iv_percentile=68.0,
            realized_vol_20d=0.20,
            iv_to_rv_ratio=1.25,
            is_pre_earnings=False,
            earnings_date=None,
            liquidity_score=0.75,
            composite_score=None,
        )

    def test_analytics_creation(self, sample_analytics):
        """Test basic analytics creation."""
        assert sample_analytics.spot_price == 560.0
        assert sample_analytics.iv_rank == 65.0
        assert sample_analytics.liquidity_score == 0.75

    def test_analytics_immutable(self, sample_analytics):
        """Test that analytics are immutable."""
        with pytest.raises(Exception):
            sample_analytics.spot_price = 570.0

    def test_within_expected_move(self, sample_analytics):
        """Test expected move boundary check."""
        # Spot: 560, EM: 25
        # Lower bound: 560 - 25 = 535
        # Upper bound: 560 + 25 = 585
        # Short put: 540 (above 535, inside)
        # Short call: 580 (below 585, inside)
        assert sample_analytics.within_expected_move is True

    def test_outside_expected_move(self, sample_analytics):
        """Test when strikes are outside expected move."""
        # Create analytics with larger distances
        analytics = Analytics(
            iron_condor=sample_analytics.iron_condor,
            spot_price=560.0,
            expected_move_straddle=15.0,  # Smaller EM
            expected_move_iv=14.0,
            put_distance_dollars=30.0,
            call_distance_dollars=30.0,
            put_distance_pct=5.36,
            call_distance_pct=5.36,
            iv_rank=65.0,
            iv_percentile=68.0,
            realized_vol_20d=0.20,
            iv_to_rv_ratio=1.25,
            is_pre_earnings=False,
            earnings_date=None,
            liquidity_score=0.75,
        )
        # Lower bound: 560 - 15 = 545
        # Upper bound: 560 + 15 = 575
        # Short put: 540 (below 545, outside)
        # Short call: 580 (above 575, outside)
        assert analytics.within_expected_move is False

    def test_avg_distance_pct(self, sample_analytics):
        """Test average distance percentage calculation."""
        expected = (3.57 + 3.57) / 2.0
        assert abs(sample_analytics.avg_distance_pct - expected) < 0.01

    def test_iv_edge(self, sample_analytics):
        """Test IV edge calculation."""
        # IV/RV ratio: 1.25, edge: 0.25
        assert abs(sample_analytics.iv_edge - 0.25) < 0.01

    def test_composite_score_none(self, sample_analytics):
        """Test that composite score starts as None."""
        assert sample_analytics.composite_score is None

    def test_repr(self, sample_analytics):
        """Test string representation."""
        repr_str = repr(sample_analytics)
        assert "ROR=" in repr_str
        assert "IVR=" in repr_str
        assert "Liq=" in repr_str
