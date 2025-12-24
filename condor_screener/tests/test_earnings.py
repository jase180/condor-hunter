"""Tests for earnings calendar integration."""

import pytest
from datetime import date, datetime
from pathlib import Path
import tempfile
import csv

from condor_screener.data.loaders import load_earnings_calendar
from condor_screener.analytics.analyzer import _is_pre_earnings


class TestLoadEarningsCalendar:
    """Tests for load_earnings_calendar function."""

    def test_load_valid_earnings_calendar(self, tmp_path):
        """Test loading a valid earnings calendar CSV."""
        # Create test CSV
        csv_file = tmp_path / "earnings.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['symbol', 'earnings_date', 'days_until_earnings', 'source'])
            writer.writerow(['AAPL', '2026-02-05', '45', 'yfinance'])
            writer.writerow(['MSFT', '2026-02-20', '60', 'yfinance'])
            writer.writerow(['TSLA', '2026-01-28', '37', 'yfinance'])

        # Load and verify
        earnings_map = load_earnings_calendar(csv_file)

        assert len(earnings_map) == 3
        assert 'AAPL' in earnings_map
        assert earnings_map['AAPL']['date'] == '2026-02-05'
        assert earnings_map['AAPL']['days_until'] == 45

        assert 'MSFT' in earnings_map
        assert earnings_map['MSFT']['date'] == '2026-02-20'
        assert earnings_map['MSFT']['days_until'] == 60

        assert 'TSLA' in earnings_map
        assert earnings_map['TSLA']['date'] == '2026-01-28'
        assert earnings_map['TSLA']['days_until'] == 37

    def test_load_empty_earnings_calendar(self, tmp_path):
        """Test loading an empty earnings calendar."""
        csv_file = tmp_path / "earnings.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['symbol', 'earnings_date', 'days_until_earnings', 'source'])

        earnings_map = load_earnings_calendar(csv_file)
        assert len(earnings_map) == 0

    def test_load_missing_file(self, tmp_path):
        """Test loading a non-existent file returns empty dict."""
        csv_file = tmp_path / "nonexistent.csv"
        earnings_map = load_earnings_calendar(csv_file)
        assert earnings_map == {}

    def test_skip_invalid_rows(self, tmp_path):
        """Test that invalid rows are skipped."""
        csv_file = tmp_path / "earnings.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['symbol', 'earnings_date', 'days_until_earnings', 'source'])
            writer.writerow(['AAPL', '2026-02-05', '45', 'yfinance'])
            writer.writerow(['BAD', '', '', 'yfinance'])  # Empty date - should skip
            writer.writerow(['MSFT', '2026-02-20', '60', 'yfinance'])
            writer.writerow(['INVALID', 'null', 'null', 'yfinance'])  # Null values - should skip

        earnings_map = load_earnings_calendar(csv_file)
        assert len(earnings_map) == 2
        assert 'AAPL' in earnings_map
        assert 'MSFT' in earnings_map
        assert 'BAD' not in earnings_map
        assert 'INVALID' not in earnings_map

    def test_ticker_case_insensitive(self, tmp_path):
        """Test that ticker symbols are converted to uppercase."""
        csv_file = tmp_path / "earnings.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['symbol', 'earnings_date', 'days_until_earnings', 'source'])
            writer.writerow(['aapl', '2026-02-05', '45', 'yfinance'])  # lowercase
            writer.writerow(['MSFT', '2026-02-20', '60', 'yfinance'])  # uppercase

        earnings_map = load_earnings_calendar(csv_file)
        assert 'AAPL' in earnings_map  # Should be uppercase
        assert 'aapl' not in earnings_map

    def test_handle_missing_days_until(self, tmp_path):
        """Test handling of missing days_until_earnings field."""
        csv_file = tmp_path / "earnings.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['symbol', 'earnings_date', 'days_until_earnings', 'source'])
            writer.writerow(['AAPL', '2026-02-05', '', 'yfinance'])  # Missing days

        earnings_map = load_earnings_calendar(csv_file)
        assert 'AAPL' in earnings_map
        assert earnings_map['AAPL']['date'] == '2026-02-05'
        assert earnings_map['AAPL']['days_until'] is None


class TestIsPreEarnings:
    """Tests for _is_pre_earnings function."""

    def test_earnings_before_expiration_not_pre_earnings(self):
        """Earnings before expiration should not be pre-earnings."""
        expiration = date(2026, 2, 10)
        earnings_date = "2026-02-05"  # 5 days before expiration

        result = _is_pre_earnings(expiration, earnings_date)
        assert result is False

    def test_earnings_on_expiration_day_is_pre_earnings(self):
        """Earnings on expiration day should be pre-earnings."""
        expiration = date(2026, 2, 5)
        earnings_date = "2026-02-05"  # Same day

        result = _is_pre_earnings(expiration, earnings_date)
        assert result is True

    def test_earnings_1_day_after_expiration_is_pre_earnings(self):
        """Earnings 1 day after expiration should be pre-earnings."""
        expiration = date(2026, 2, 5)
        earnings_date = "2026-02-06"  # 1 day after

        result = _is_pre_earnings(expiration, earnings_date)
        assert result is True

    def test_earnings_7_days_after_expiration_is_pre_earnings(self):
        """Earnings 7 days after expiration should be pre-earnings (boundary)."""
        expiration = date(2026, 2, 5)
        earnings_date = "2026-02-12"  # 7 days after

        result = _is_pre_earnings(expiration, earnings_date)
        assert result is True

    def test_earnings_8_days_after_expiration_not_pre_earnings(self):
        """Earnings 8 days after expiration should not be pre-earnings."""
        expiration = date(2026, 2, 5)
        earnings_date = "2026-02-13"  # 8 days after

        result = _is_pre_earnings(expiration, earnings_date)
        assert result is False

    def test_earnings_far_in_future_not_pre_earnings(self):
        """Earnings far in the future should not be pre-earnings."""
        expiration = date(2026, 2, 5)
        earnings_date = "2026-03-15"  # 38 days after

        result = _is_pre_earnings(expiration, earnings_date)
        assert result is False

    def test_no_earnings_date_not_pre_earnings(self):
        """No earnings date should return False."""
        expiration = date(2026, 2, 5)
        earnings_date = None

        result = _is_pre_earnings(expiration, earnings_date)
        assert result is False

    def test_invalid_earnings_date_format_not_pre_earnings(self):
        """Invalid date format should return False."""
        expiration = date(2026, 2, 5)
        earnings_date = "invalid-date"

        result = _is_pre_earnings(expiration, earnings_date)
        assert result is False

    def test_empty_earnings_date_not_pre_earnings(self):
        """Empty string earnings date should return False."""
        expiration = date(2026, 2, 5)
        earnings_date = ""

        result = _is_pre_earnings(expiration, earnings_date)
        assert result is False


class TestEarningsIntegration:
    """Integration tests for earnings functionality."""

    def test_full_workflow(self, tmp_path):
        """Test complete workflow from CSV to earnings detection."""
        # Create earnings calendar
        csv_file = tmp_path / "earnings.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['symbol', 'earnings_date', 'days_until_earnings', 'source'])
            writer.writerow(['AAPL', '2026-02-08', '42', 'yfinance'])

        # Load earnings calendar
        earnings_map = load_earnings_calendar(csv_file)
        assert 'AAPL' in earnings_map

        # Test various expiration scenarios
        earnings_date = earnings_map['AAPL']['date']

        # Safe expiration (well before earnings)
        safe_exp = date(2026, 1, 20)
        assert _is_pre_earnings(safe_exp, earnings_date) is False

        # Risky expiration (2 days before earnings)
        risky_exp = date(2026, 2, 6)
        assert _is_pre_earnings(risky_exp, earnings_date) is True

        # Post-earnings expiration
        post_exp = date(2026, 2, 20)
        assert _is_pre_earnings(post_exp, earnings_date) is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
