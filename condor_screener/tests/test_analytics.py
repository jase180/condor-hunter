"""Unit tests for analytics modules (expected move, volatility, analyzer)."""

import pytest
import math
from datetime import date, timedelta

from condor_screener.analytics.expected_move import (
    expected_move_from_straddle,
    expected_move_from_iv,
    find_atm_options,
    calculate_expected_move,
)
from condor_screener.analytics.volatility import (
    calculate_iv_rank,
    calculate_iv_percentile,
    calculate_realized_volatility_close_to_close,
    calculate_realized_volatility_garman_klass,
    calculate_realized_volatility,
)
from condor_screener.analytics.analyzer import analyze_iron_condor, _is_pre_earnings
from condor_screener.models.option import Option
from condor_screener.models.iron_condor import IronCondor


class TestExpectedMoveFromStraddle:
    """Test suite for straddle-based expected move calculation."""

    @pytest.fixture
    def atm_options(self):
        """Create ATM call and put options."""
        exp = date.today() + timedelta(days=35)

        atm_call = Option(
            ticker="SPY", strike=560.0, expiration=exp, option_type="call",
            bid=12.0, ask=13.0, volume=5000, open_interest=20000,
            delta=0.50, implied_vol=0.25
        )

        atm_put = Option(
            ticker="SPY", strike=560.0, expiration=exp, option_type="put",
            bid=11.5, ask=12.5, volume=4800, open_interest=19000,
            delta=-0.50, implied_vol=0.26
        )

        return atm_call, atm_put

    def test_expected_move_from_straddle(self, atm_options):
        """Test expected move from ATM straddle."""
        atm_call, atm_put = atm_options

        em = expected_move_from_straddle(atm_call, atm_put)

        # Straddle price: 12.5 + 12.0 = 24.5
        # Expected move: 24.5 * 0.85 = 20.825
        expected = 24.5 * 0.85
        assert abs(em - expected) < 0.01

    def test_expected_move_custom_discount(self, atm_options):
        """Test expected move with custom discount factor."""
        atm_call, atm_put = atm_options

        em = expected_move_from_straddle(atm_call, atm_put, discount_factor=0.90)

        # Straddle price: 24.5
        # Expected move: 24.5 * 0.90 = 22.05
        expected = 24.5 * 0.90
        assert abs(em - expected) < 0.01


class TestExpectedMoveFromIV:
    """Test suite for IV-based expected move calculation."""

    def test_expected_move_from_iv(self):
        """Test expected move from IV."""
        spot_price = 560.0
        implied_vol = 0.25
        dte = 35

        em = expected_move_from_iv(spot_price, implied_vol, dte)

        # Expected: 560 * 0.25 * sqrt(35/365)
        time_fraction = 35 / 365.0
        expected = 560.0 * 0.25 * math.sqrt(time_fraction)
        assert abs(em - expected) < 0.01

    def test_expected_move_long_dte(self):
        """Test expected move with longer DTE."""
        spot_price = 560.0
        implied_vol = 0.25
        dte = 365

        em = expected_move_from_iv(spot_price, implied_vol, dte)

        # Expected: 560 * 0.25 * sqrt(1) = 140
        expected = 560.0 * 0.25
        assert abs(em - expected) < 0.01

    def test_expected_move_high_iv(self):
        """Test expected move with high IV."""
        spot_price = 560.0
        implied_vol = 0.50  # 50% IV
        dte = 35

        em = expected_move_from_iv(spot_price, implied_vol, dte)

        time_fraction = 35 / 365.0
        expected = 560.0 * 0.50 * math.sqrt(time_fraction)
        assert abs(em - expected) < 0.01
        assert em > expected_move_from_iv(560.0, 0.25, 35)


class TestFindATMOptions:
    """Test suite for finding ATM options."""

    def test_find_atm_exact_match(self):
        """Test finding ATM options with exact strike match."""
        exp = date.today() + timedelta(days=35)
        spot = 560.0

        options = [
            Option(
                ticker="SPY", strike=560.0, expiration=exp, option_type="call",
                bid=12.0, ask=13.0, volume=5000, open_interest=20000,
                delta=0.50, implied_vol=0.25
            ),
            Option(
                ticker="SPY", strike=560.0, expiration=exp, option_type="put",
                bid=11.5, ask=12.5, volume=4800, open_interest=19000,
                delta=-0.50, implied_vol=0.26
            ),
        ]

        atm_call, atm_put = find_atm_options(options, spot)

        assert atm_call is not None
        assert atm_put is not None
        assert atm_call.strike == 560.0
        assert atm_put.strike == 560.0

    def test_find_atm_closest_strike(self):
        """Test finding ATM options with closest strike."""
        exp = date.today() + timedelta(days=35)
        spot = 562.5  # Between strikes

        options = [
            Option(
                ticker="SPY", strike=560.0, expiration=exp, option_type="call",
                bid=12.0, ask=13.0, volume=5000, open_interest=20000,
                delta=0.52, implied_vol=0.25
            ),
            Option(
                ticker="SPY", strike=565.0, expiration=exp, option_type="call",
                bid=10.0, ask=11.0, volume=4500, open_interest=18000,
                delta=0.48, implied_vol=0.24
            ),
            Option(
                ticker="SPY", strike=560.0, expiration=exp, option_type="put",
                bid=11.0, ask=12.0, volume=4800, open_interest=19000,
                delta=-0.48, implied_vol=0.26
            ),
        ]

        atm_call, atm_put = find_atm_options(options, spot)

        # Should find 560 strike (closest to 562.5)
        assert atm_call.strike == 560.0
        assert atm_put.strike == 560.0

    def test_find_atm_no_calls(self):
        """Test finding ATM when no calls available."""
        exp = date.today() + timedelta(days=35)
        spot = 560.0

        options = [
            Option(
                ticker="SPY", strike=560.0, expiration=exp, option_type="put",
                bid=11.5, ask=12.5, volume=4800, open_interest=19000,
                delta=-0.50, implied_vol=0.26
            ),
        ]

        atm_call, atm_put = find_atm_options(options, spot)

        assert atm_call is None
        assert atm_put is not None


class TestCalculateExpectedMove:
    """Test suite for calculate_expected_move."""

    @pytest.fixture
    def sample_options(self):
        """Create sample options."""
        exp = date.today() + timedelta(days=35)
        return [
            Option(
                ticker="SPY", strike=560.0, expiration=exp, option_type="call",
                bid=12.0, ask=13.0, volume=5000, open_interest=20000,
                delta=0.50, implied_vol=0.25
            ),
            Option(
                ticker="SPY", strike=560.0, expiration=exp, option_type="put",
                bid=11.5, ask=12.5, volume=4800, open_interest=19000,
                delta=-0.50, implied_vol=0.26
            ),
        ]

    def test_calculate_straddle_method(self, sample_options):
        """Test calculate_expected_move with straddle method."""
        em_straddle, em_iv = calculate_expected_move(
            sample_options, 560.0, method="straddle"
        )

        # Both should be equal when method is "straddle"
        assert em_straddle == em_iv
        assert em_straddle > 0

    def test_calculate_iv_method(self, sample_options):
        """Test calculate_expected_move with IV method."""
        em_straddle, em_iv = calculate_expected_move(
            sample_options, 560.0, method="iv"
        )

        # Both should be equal when method is "iv"
        assert em_straddle == em_iv
        assert em_iv > 0

    def test_calculate_both_method(self, sample_options):
        """Test calculate_expected_move with both methods."""
        em_straddle, em_iv = calculate_expected_move(
            sample_options, 560.0, method="both"
        )

        # Both should be positive and potentially different
        assert em_straddle > 0
        assert em_iv > 0

    def test_calculate_empty_options(self):
        """Test calculate_expected_move with empty list."""
        with pytest.raises(ValueError, match="empty"):
            calculate_expected_move([], 560.0)


class TestIVRank:
    """Test suite for IV rank calculation."""

    def test_iv_rank_middle(self):
        """Test IV rank at middle of range."""
        historical_ivs = [0.15, 0.20, 0.25, 0.30, 0.35]
        current_iv = 0.25

        ivr = calculate_iv_rank(current_iv, historical_ivs)

        # (0.25 - 0.15) / (0.35 - 0.15) = 0.10 / 0.20 = 50%
        assert abs(ivr - 50.0) < 0.1

    def test_iv_rank_high(self):
        """Test IV rank at high end."""
        historical_ivs = [0.15, 0.20, 0.25, 0.30, 0.35]
        current_iv = 0.35

        ivr = calculate_iv_rank(current_iv, historical_ivs)

        assert abs(ivr - 100.0) < 0.1

    def test_iv_rank_low(self):
        """Test IV rank at low end."""
        historical_ivs = [0.15, 0.20, 0.25, 0.30, 0.35]
        current_iv = 0.15

        ivr = calculate_iv_rank(current_iv, historical_ivs)

        assert abs(ivr - 0.0) < 0.1

    def test_iv_rank_no_data(self):
        """Test IV rank with no historical data."""
        ivr = calculate_iv_rank(0.25, [])

        # Should return 50.0 (neutral)
        assert ivr == 50.0

    def test_iv_rank_no_range(self):
        """Test IV rank when all historical IVs are the same."""
        historical_ivs = [0.25, 0.25, 0.25]
        current_iv = 0.25

        ivr = calculate_iv_rank(current_iv, historical_ivs)

        assert ivr == 50.0


class TestIVPercentile:
    """Test suite for IV percentile calculation."""

    def test_iv_percentile_middle(self):
        """Test IV percentile in middle."""
        historical_ivs = [0.15, 0.20, 0.25, 0.30, 0.35]
        current_iv = 0.25

        ivp = calculate_iv_percentile(current_iv, historical_ivs)

        # 2 out of 5 values below 0.25 = 40%
        assert abs(ivp - 40.0) < 0.1

    def test_iv_percentile_high(self):
        """Test IV percentile at high end."""
        historical_ivs = [0.15, 0.20, 0.25, 0.30, 0.35]
        current_iv = 0.40

        ivp = calculate_iv_percentile(current_iv, historical_ivs)

        # All 5 values below 0.40 = 100%
        assert abs(ivp - 100.0) < 0.1

    def test_iv_percentile_low(self):
        """Test IV percentile at low end."""
        historical_ivs = [0.15, 0.20, 0.25, 0.30, 0.35]
        current_iv = 0.10

        ivp = calculate_iv_percentile(current_iv, historical_ivs)

        # 0 values below 0.10 = 0%
        assert abs(ivp - 0.0) < 0.1

    def test_iv_percentile_no_data(self):
        """Test IV percentile with no data."""
        ivp = calculate_iv_percentile(0.25, [])

        assert ivp == 50.0


class TestRealizedVolatility:
    """Test suite for realized volatility calculations."""

    def test_realized_vol_close_to_close(self):
        """Test close-to-close realized volatility."""
        # Sample prices with ~20% annualized vol
        close_prices = [100.0, 101.0, 99.5, 100.5, 102.0, 101.5, 100.0]

        rv = calculate_realized_volatility_close_to_close(close_prices)

        # Should be positive and reasonable
        assert rv > 0
        assert rv < 1.0  # Less than 100%

    def test_realized_vol_single_price(self):
        """Test realized volatility with only one price."""
        rv = calculate_realized_volatility_close_to_close([100.0])

        assert rv == 0.0

    def test_realized_vol_not_annualized(self):
        """Test realized volatility without annualization."""
        close_prices = [100.0, 101.0, 99.5, 100.5]

        rv_annual = calculate_realized_volatility_close_to_close(close_prices, annualize=True)
        rv_daily = calculate_realized_volatility_close_to_close(close_prices, annualize=False)

        # Annualized should be larger (multiplied by sqrt(252))
        assert rv_annual > rv_daily
        assert abs(rv_annual - rv_daily * math.sqrt(252)) < 0.01

    def test_realized_vol_garman_klass(self):
        """Test Garman-Klass realized volatility."""
        # Sample OHLC data
        ohlc_data = [
            (100.0, 102.0, 99.0, 101.0),
            (101.0, 103.0, 100.0, 102.0),
            (102.0, 104.0, 101.0, 103.0),
        ]

        rv = calculate_realized_volatility_garman_klass(ohlc_data)

        # Should be positive and reasonable
        assert rv > 0
        assert rv < 1.0

    def test_realized_vol_garman_klass_empty(self):
        """Test Garman-Klass with empty data."""
        rv = calculate_realized_volatility_garman_klass([])

        assert rv == 0.0

    def test_realized_vol_wrapper(self):
        """Test realized_volatility wrapper function."""
        close_prices = [100.0, 101.0, 99.5, 100.5]
        ohlc_data = [(100.0, 102.0, 99.0, 101.0)]

        # Should use Garman-Klass when OHLC available
        rv_gk = calculate_realized_volatility(ohlc_data=ohlc_data, use_garman_klass=True)
        assert rv_gk > 0

        # Should use close-to-close as fallback
        rv_ctc = calculate_realized_volatility(close_prices=close_prices, use_garman_klass=False)
        assert rv_ctc > 0

        # Should return 0 with no data
        rv_none = calculate_realized_volatility()
        assert rv_none == 0.0


class TestIsPreEarnings:
    """Test suite for earnings date detection."""

    def test_is_pre_earnings_true(self):
        """Test when expiration is before earnings."""
        expiration = date.today() + timedelta(days=30)
        earnings_date = (date.today() + timedelta(days=32)).strftime('%Y-%m-%d')

        assert _is_pre_earnings(expiration, earnings_date) is True

    def test_is_pre_earnings_false_too_late(self):
        """Test when earnings are too far after expiration."""
        expiration = date.today() + timedelta(days=30)
        earnings_date = (date.today() + timedelta(days=40)).strftime('%Y-%m-%d')

        assert _is_pre_earnings(expiration, earnings_date) is False

    def test_is_pre_earnings_false_before(self):
        """Test when earnings are before expiration."""
        expiration = date.today() + timedelta(days=30)
        earnings_date = (date.today() + timedelta(days=20)).strftime('%Y-%m-%d')

        assert _is_pre_earnings(expiration, earnings_date) is False

    def test_is_pre_earnings_no_date(self):
        """Test when no earnings date provided."""
        expiration = date.today() + timedelta(days=30)

        assert _is_pre_earnings(expiration, None) is False

    def test_is_pre_earnings_invalid_date(self):
        """Test with invalid earnings date format."""
        expiration = date.today() + timedelta(days=30)

        assert _is_pre_earnings(expiration, "invalid-date") is False


class TestAnalyzeIronCondor:
    """Test suite for full iron condor analysis."""

    @pytest.fixture
    def sample_condor(self):
        """Create sample iron condor."""
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

    def test_analyze_iron_condor_complete(self, sample_condor):
        """Test complete iron condor analysis."""
        historical_ivs = [0.18, 0.20, 0.22, 0.24, 0.26, 0.28]
        realized_vol = 0.20

        analytics = analyze_iron_condor(
            iron_condor=sample_condor,
            spot_price=560.0,
            historical_ivs=historical_ivs,
            realized_vol_20d=realized_vol,
        )

        # Verify all fields are populated
        assert analytics.iron_condor == sample_condor
        assert analytics.spot_price == 560.0
        assert analytics.expected_move_straddle > 0
        assert analytics.expected_move_iv > 0
        assert analytics.put_distance_dollars > 0
        assert analytics.call_distance_dollars > 0
        assert analytics.iv_rank >= 0
        assert analytics.iv_percentile >= 0
        assert analytics.iv_to_rv_ratio > 0
        assert analytics.liquidity_score > 0

    def test_analyze_iron_condor_with_earnings(self, sample_condor):
        """Test iron condor analysis with earnings date."""
        earnings_date = (date.today() + timedelta(days=37)).strftime('%Y-%m-%d')

        analytics = analyze_iron_condor(
            iron_condor=sample_condor,
            spot_price=560.0,
            historical_ivs=[0.20, 0.25],
            realized_vol_20d=0.20,
            earnings_date=earnings_date,
        )

        assert analytics.is_pre_earnings is True
        assert analytics.earnings_date == earnings_date

    def test_analyze_iron_condor_distance_calculations(self, sample_condor):
        """Test distance metric calculations."""
        analytics = analyze_iron_condor(
            iron_condor=sample_condor,
            spot_price=560.0,
            historical_ivs=[0.25],
            realized_vol_20d=0.20,
        )

        # Put distance: 560 - 540 = 20
        assert abs(analytics.put_distance_dollars - 20.0) < 0.1

        # Call distance: 580 - 560 = 20
        assert abs(analytics.call_distance_dollars - 20.0) < 0.1

        # Put distance %: 20 / 560 * 100 ≈ 3.57%
        expected_put_pct = (20.0 / 560.0) * 100
        assert abs(analytics.put_distance_pct - expected_put_pct) < 0.1

    def test_analyze_iron_condor_iv_ratio(self, sample_condor):
        """Test IV/RV ratio calculation."""
        analytics = analyze_iron_condor(
            iron_condor=sample_condor,
            spot_price=560.0,
            historical_ivs=[0.25],
            realized_vol_20d=0.20,
        )

        # Current IV ≈ 0.25, RV = 0.20
        # Ratio: 0.25 / 0.20 = 1.25
        assert abs(analytics.iv_to_rv_ratio - 1.25) < 0.1
