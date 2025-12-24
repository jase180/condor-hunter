"""Tests for Greeks calculation and validation.

Tests Black-Scholes formulas, validation logic, and fallback mechanisms.
"""

import pytest
import math
from datetime import date, timedelta

from condor_screener.analytics.greeks import (
    BlackScholesGreeks,
    validate_greeks,
    compute_or_fallback_greeks
)
from condor_screener.models.option import Option


class TestBlackScholesGreeks:
    """Test suite for Black-Scholes Greeks calculations."""

    def test_atm_call_delta_approximately_half(self):
        """Test that ATM call delta is approximately 0.5."""
        delta = BlackScholesGreeks.calculate_delta(
            spot=100.0,
            strike=100.0,  # ATM
            time_to_expiry=0.25,  # 3 months
            rate=0.02,
            vol=0.25,
            option_type='call'
        )

        # ATM call delta should be around 0.5 (slightly above due to rate and vol)
        assert 0.45 <= delta <= 0.55

    def test_atm_put_delta_approximately_negative_half(self):
        """Test that ATM put delta is approximately -0.5."""
        delta = BlackScholesGreeks.calculate_delta(
            spot=100.0,
            strike=100.0,  # ATM
            time_to_expiry=0.25,
            rate=0.02,
            vol=0.25,
            option_type='put'
        )

        # ATM put delta should be around -0.5 (slightly above -0.5 due to rate)
        assert -0.55 <= delta <= -0.45

    def test_deep_itm_call_delta_approaches_one(self):
        """Test that deep ITM call delta approaches 1.0."""
        delta = BlackScholesGreeks.calculate_delta(
            spot=100.0,
            strike=80.0,  # Deep ITM
            time_to_expiry=0.25,
            rate=0.02,
            vol=0.25,
            option_type='call'
        )

        # Deep ITM call should have delta close to 1.0
        assert delta > 0.95

    def test_deep_otm_call_delta_approaches_zero(self):
        """Test that deep OTM call delta approaches 0.0."""
        delta = BlackScholesGreeks.calculate_delta(
            spot=100.0,
            strike=120.0,  # Deep OTM
            time_to_expiry=0.25,
            rate=0.02,
            vol=0.25,
            option_type='call'
        )

        # Deep OTM call should have low delta
        assert delta < 0.15

    def test_deep_itm_put_delta_approaches_negative_one(self):
        """Test that deep ITM put delta approaches -1.0."""
        delta = BlackScholesGreeks.calculate_delta(
            spot=100.0,
            strike=120.0,  # Deep ITM for put
            time_to_expiry=0.25,
            rate=0.02,
            vol=0.25,
            option_type='put'
        )

        # Deep ITM put should have delta close to -1.0 (but not quite due to time value)
        assert delta < -0.85

    def test_put_call_delta_relationship(self):
        """Test that put delta = call delta - 1."""
        spot, strike = 100.0, 105.0
        tte, rate, vol = 0.25, 0.02, 0.25

        call_delta = BlackScholesGreeks.calculate_delta(
            spot, strike, tte, rate, vol, 'call'
        )
        put_delta = BlackScholesGreeks.calculate_delta(
            spot, strike, tte, rate, vol, 'put'
        )

        # Put-call parity: put_delta = call_delta - 1
        assert abs((call_delta - 1.0) - put_delta) < 0.01

    def test_gamma_same_for_call_and_put(self):
        """Test that gamma is the same for call and put."""
        gamma = BlackScholesGreeks.calculate_gamma(
            spot=100.0,
            strike=100.0,
            time_to_expiry=0.25,
            rate=0.02,
            vol=0.25
        )

        # Gamma should be positive and same for both
        assert gamma > 0

    def test_gamma_highest_at_atm(self):
        """Test that gamma is highest for ATM options."""
        atm_gamma = BlackScholesGreeks.calculate_gamma(
            spot=100.0,
            strike=100.0,  # ATM
            time_to_expiry=0.25,
            rate=0.02,
            vol=0.25
        )

        otm_gamma = BlackScholesGreeks.calculate_gamma(
            spot=100.0,
            strike=110.0,  # OTM
            time_to_expiry=0.25,
            rate=0.02,
            vol=0.25
        )

        # ATM gamma should be higher than OTM
        assert atm_gamma > otm_gamma

    def test_theta_negative_for_long_options(self):
        """Test that theta is negative (time decay) for long options."""
        call_theta = BlackScholesGreeks.calculate_theta(
            spot=100.0,
            strike=100.0,
            time_to_expiry=0.25,
            rate=0.02,
            vol=0.25,
            option_type='call'
        )

        put_theta = BlackScholesGreeks.calculate_theta(
            spot=100.0,
            strike=100.0,
            time_to_expiry=0.25,
            rate=0.02,
            vol=0.25,
            option_type='put'
        )

        # Both should be negative (time decay)
        assert call_theta < 0
        assert put_theta < 0

    def test_vega_positive(self):
        """Test that vega is positive."""
        vega = BlackScholesGreeks.calculate_vega(
            spot=100.0,
            strike=100.0,
            time_to_expiry=0.25,
            rate=0.02,
            vol=0.25
        )

        # Vega should be positive (option value increases with IV)
        assert vega > 0

    def test_vega_highest_at_atm(self):
        """Test that vega is highest for ATM options."""
        atm_vega = BlackScholesGreeks.calculate_vega(
            spot=100.0,
            strike=100.0,  # ATM
            time_to_expiry=0.25,
            rate=0.02,
            vol=0.25
        )

        otm_vega = BlackScholesGreeks.calculate_vega(
            spot=100.0,
            strike=110.0,  # OTM
            time_to_expiry=0.25,
            rate=0.02,
            vol=0.25
        )

        # ATM vega should be higher than OTM
        assert atm_vega > otm_vega

    def test_delta_at_expiration_call(self):
        """Test delta at expiration (t=0)."""
        # ITM at expiration
        delta_itm = BlackScholesGreeks.calculate_delta(
            spot=105.0,
            strike=100.0,
            time_to_expiry=0.0,  # At expiration
            rate=0.02,
            vol=0.25,
            option_type='call'
        )
        assert delta_itm == 1.0

        # OTM at expiration
        delta_otm = BlackScholesGreeks.calculate_delta(
            spot=95.0,
            strike=100.0,
            time_to_expiry=0.0,
            rate=0.02,
            vol=0.25,
            option_type='call'
        )
        assert delta_otm == 0.0

    def test_delta_at_expiration_put(self):
        """Test put delta at expiration (t=0)."""
        # ITM at expiration
        delta_itm = BlackScholesGreeks.calculate_delta(
            spot=95.0,
            strike=100.0,
            time_to_expiry=0.0,
            rate=0.02,
            vol=0.25,
            option_type='put'
        )
        assert delta_itm == -1.0

        # OTM at expiration
        delta_otm = BlackScholesGreeks.calculate_delta(
            spot=105.0,
            strike=100.0,
            time_to_expiry=0.0,
            rate=0.02,
            vol=0.25,
            option_type='put'
        )
        assert delta_otm == 0.0

    def test_greeks_zero_at_expiration(self):
        """Test that gamma, theta, vega are zero at expiration."""
        gamma = BlackScholesGreeks.calculate_gamma(
            spot=100.0,
            strike=100.0,
            time_to_expiry=0.0,
            rate=0.02,
            vol=0.25
        )

        theta = BlackScholesGreeks.calculate_theta(
            spot=100.0,
            strike=100.0,
            time_to_expiry=0.0,
            rate=0.02,
            vol=0.25,
            option_type='call'
        )

        vega = BlackScholesGreeks.calculate_vega(
            spot=100.0,
            strike=100.0,
            time_to_expiry=0.0,
            rate=0.02,
            vol=0.25
        )

        assert gamma == 0.0
        assert theta == 0.0
        assert vega == 0.0

    def test_calculate_all_greeks(self):
        """Test that calculate_all_greeks returns consistent values."""
        delta, gamma, theta, vega = BlackScholesGreeks.calculate_all_greeks(
            spot=100.0,
            strike=100.0,
            time_to_expiry=0.25,
            rate=0.02,
            vol=0.25,
            option_type='call'
        )

        # Check all are calculated
        assert delta is not None
        assert gamma is not None
        assert theta is not None
        assert vega is not None

        # Verify they match individual calculations
        delta_check = BlackScholesGreeks.calculate_delta(
            100.0, 100.0, 0.25, 0.02, 0.25, 'call'
        )
        assert abs(delta - delta_check) < 0.0001

    def test_invalid_option_type_raises(self):
        """Test that invalid option type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid option_type"):
            BlackScholesGreeks.calculate_delta(
                100.0, 100.0, 0.25, 0.02, 0.25, 'invalid'
            )


class TestValidateGreeks:
    """Test suite for Greeks validation."""

    @pytest.fixture
    def valid_call_option(self):
        """Create a call option with valid Greeks."""
        exp = date.today() + timedelta(days=30)
        return Option(
            ticker="SPY",
            strike=550.0,
            expiration=exp,
            option_type="call",
            bid=5.0,
            ask=5.5,
            volume=1000,
            open_interest=5000,
            delta=0.25,
            gamma=0.05,
            theta=-0.10,
            vega=0.15,
            implied_vol=0.25
        )

    @pytest.fixture
    def valid_put_option(self):
        """Create a put option with valid Greeks."""
        exp = date.today() + timedelta(days=30)
        return Option(
            ticker="SPY",
            strike=550.0,
            expiration=exp,
            option_type="put",
            bid=5.0,
            ask=5.5,
            volume=1000,
            open_interest=5000,
            delta=-0.25,
            gamma=0.05,
            theta=-0.10,
            vega=0.15,
            implied_vol=0.25
        )

    def test_valid_call_greeks(self, valid_call_option):
        """Test validation passes for valid call Greeks."""
        is_valid, error = validate_greeks(valid_call_option)
        assert is_valid
        assert error == ""

    def test_valid_put_greeks(self, valid_put_option):
        """Test validation passes for valid put Greeks."""
        is_valid, error = validate_greeks(valid_put_option)
        assert is_valid
        assert error == ""

    def test_missing_delta_is_valid(self):
        """Test that missing delta is considered valid (can't validate)."""
        exp = date.today() + timedelta(days=30)
        option = Option(
            ticker="SPY",
            strike=550.0,
            expiration=exp,
            option_type="call",
            bid=5.0,
            ask=5.5,
            volume=1000,
            open_interest=5000,
            delta=None,  # Missing
            implied_vol=0.25
        )

        is_valid, error = validate_greeks(option)
        assert is_valid  # Can't validate without delta

    def test_delta_out_of_range(self):
        """Test that delta outside [-1, 1] fails validation."""
        exp = date.today() + timedelta(days=30)
        option = Option(
            ticker="SPY",
            strike=550.0,
            expiration=exp,
            option_type="call",
            bid=5.0,
            ask=5.5,
            volume=1000,
            open_interest=5000,
            delta=1.5,  # Invalid
            implied_vol=0.25
        )

        is_valid, error = validate_greeks(option)
        assert not is_valid
        assert "outside valid range" in error

    def test_call_with_negative_delta(self):
        """Test that call with negative delta fails validation."""
        exp = date.today() + timedelta(days=30)
        option = Option(
            ticker="SPY",
            strike=550.0,
            expiration=exp,
            option_type="call",
            bid=5.0,
            ask=5.5,
            volume=1000,
            open_interest=5000,
            delta=-0.25,  # Should be positive for call
            implied_vol=0.25
        )

        is_valid, error = validate_greeks(option)
        assert not is_valid
        assert "negative delta" in error

    def test_put_with_positive_delta(self):
        """Test that put with positive delta fails validation."""
        exp = date.today() + timedelta(days=30)
        option = Option(
            ticker="SPY",
            strike=550.0,
            expiration=exp,
            option_type="put",
            bid=5.0,
            ask=5.5,
            volume=1000,
            open_interest=5000,
            delta=0.25,  # Should be negative for put
            implied_vol=0.25
        )

        is_valid, error = validate_greeks(option)
        assert not is_valid
        assert "positive delta" in error

    def test_negative_gamma_fails(self):
        """Test that negative gamma fails validation."""
        exp = date.today() + timedelta(days=30)
        option = Option(
            ticker="SPY",
            strike=550.0,
            expiration=exp,
            option_type="call",
            bid=5.0,
            ask=5.5,
            volume=1000,
            open_interest=5000,
            delta=0.25,
            gamma=-0.10,  # Should be non-negative (beyond tolerance)
            implied_vol=0.25
        )

        is_valid, error = validate_greeks(option)
        assert not is_valid
        assert "Gamma" in error

    def test_negative_vega_fails(self):
        """Test that negative vega fails validation."""
        exp = date.today() + timedelta(days=30)
        option = Option(
            ticker="SPY",
            strike=550.0,
            expiration=exp,
            option_type="call",
            bid=5.0,
            ask=5.5,
            volume=1000,
            open_interest=5000,
            delta=0.25,
            vega=-0.15,  # Should be non-negative
            implied_vol=0.25
        )

        is_valid, error = validate_greeks(option)
        assert not is_valid
        assert "Vega" in error


class TestComputeOrFallbackGreeks:
    """Test suite for compute_or_fallback_greeks function."""

    def test_uses_provided_greeks_when_valid(self):
        """Test that provided Greeks are used when valid."""
        exp = date.today() + timedelta(days=30)
        option = Option(
            ticker="SPY",
            strike=550.0,
            expiration=exp,
            option_type="call",
            bid=5.0,
            ask=5.5,
            volume=1000,
            open_interest=5000,
            delta=0.35,  # Provided
            gamma=0.05,
            theta=-0.10,
            vega=0.15,
            implied_vol=0.25
        )

        delta, gamma, theta, vega = compute_or_fallback_greeks(option, spot=560.0)

        # Should use provided values
        assert delta == 0.35
        assert gamma == 0.05
        assert theta == -0.10
        assert vega == 0.15

    def test_computes_fallback_when_delta_missing(self):
        """Test that fallback is computed when delta is missing."""
        exp = date.today() + timedelta(days=30)
        option = Option(
            ticker="SPY",
            strike=550.0,
            expiration=exp,
            option_type="call",
            bid=5.0,
            ask=5.5,
            volume=1000,
            open_interest=5000,
            delta=None,  # Missing
            implied_vol=0.25
        )

        delta, gamma, theta, vega = compute_or_fallback_greeks(option, spot=560.0)

        # Should compute fallback
        assert delta is not None
        assert 0.0 < delta < 1.0  # Call delta should be positive

    def test_computes_fallback_when_greeks_invalid(self):
        """Test that fallback is computed when Greeks are invalid."""
        exp = date.today() + timedelta(days=30)
        option = Option(
            ticker="SPY",
            strike=550.0,
            expiration=exp,
            option_type="call",
            bid=5.0,
            ask=5.5,
            volume=1000,
            open_interest=5000,
            delta=-0.25,  # Invalid for call
            implied_vol=0.25
        )

        delta, gamma, theta, vega = compute_or_fallback_greeks(option, spot=560.0)

        # Should compute fallback with correct sign
        assert delta > 0  # Should be positive for call

    def test_returns_zero_when_no_iv(self):
        """Test that zero delta is returned when IV is missing."""
        exp = date.today() + timedelta(days=30)
        option = Option(
            ticker="SPY",
            strike=550.0,
            expiration=exp,
            option_type="call",
            bid=5.0,
            ask=5.5,
            volume=1000,
            open_interest=5000,
            delta=None,
            implied_vol=None  # Missing
        )

        delta, gamma, theta, vega = compute_or_fallback_greeks(option, spot=560.0)

        # Should return zero as last resort
        assert delta == 0.0
        assert gamma is None
        assert theta is None
        assert vega is None

    def test_put_fallback_delta_is_negative(self):
        """Test that fallback delta for put is negative."""
        exp = date.today() + timedelta(days=30)
        option = Option(
            ticker="SPY",
            strike=550.0,
            expiration=exp,
            option_type="put",
            bid=5.0,
            ask=5.5,
            volume=1000,
            open_interest=5000,
            delta=None,
            implied_vol=0.25
        )

        delta, gamma, theta, vega = compute_or_fallback_greeks(option, spot=560.0)

        # Put delta should be negative
        assert delta < 0
