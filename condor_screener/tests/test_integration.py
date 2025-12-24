"""Integration tests for end-to-end workflow."""

import pytest
import tempfile
import csv
from pathlib import Path
from datetime import date, timedelta

from condor_screener.data.loaders import load_options_from_csv, OptionChainData
from condor_screener.data.validators import FilterConfig, filter_options
from condor_screener.builders.condor_builder import StrategyConfig, generate_iron_condors
from condor_screener.analytics.analyzer import analyze_iron_condor
from condor_screener.scoring.scorer import ScoringConfig, rank_analytics


class TestEndToEndWorkflow:
    """Test complete screening workflow from CSV to ranked results."""

    @pytest.fixture
    def sample_csv_file(self):
        """Create a complete option chain CSV file."""
        exp = (date.today() + timedelta(days=35)).strftime('%Y-%m-%d')

        # Create realistic option chain data
        rows = []

        # Puts
        put_strikes = [
            (530.0, -0.10, 1.5, 1.7, 800, 4000),
            (535.0, -0.15, 2.0, 2.2, 1000, 5000),
            (540.0, -0.20, 2.8, 3.0, 1200, 6000),
            (545.0, -0.25, 3.8, 4.0, 1000, 5000),
        ]

        for strike, delta, bid, ask, volume, oi in put_strikes:
            rows.append({
                'ticker': 'SPY',
                'strike': str(strike),
                'expiration': exp,
                'option_type': 'put',
                'bid': str(bid),
                'ask': str(ask),
                'last': str((bid + ask) / 2),
                'volume': str(volume),
                'open_interest': str(oi),
                'delta': str(delta),
                'gamma': '0.05',
                'theta': '-0.10',
                'vega': '0.30',
                'implied_vol': '0.25',
            })

        # Calls
        call_strikes = [
            (575.0, 0.25, 3.8, 4.0, 1000, 5000),
            (580.0, 0.20, 2.8, 3.0, 1200, 6000),
            (585.0, 0.15, 2.0, 2.2, 1000, 5000),
            (590.0, 0.10, 1.5, 1.7, 800, 4000),
        ]

        for strike, delta, bid, ask, volume, oi in call_strikes:
            rows.append({
                'ticker': 'SPY',
                'strike': str(strike),
                'expiration': exp,
                'option_type': 'call',
                'bid': str(bid),
                'ask': str(ask),
                'last': str((bid + ask) / 2),
                'volume': str(volume),
                'open_interest': str(oi),
                'delta': str(delta),
                'gamma': '0.05',
                'theta': '-0.10',
                'vega': '0.30',
                'implied_vol': '0.25',
            })

        # Write to temp file
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
        fieldnames = [
            'ticker', 'strike', 'expiration', 'option_type', 'bid', 'ask',
            'last', 'volume', 'open_interest', 'delta', 'gamma', 'theta',
            'vega', 'implied_vol'
        ]

        writer = csv.DictWriter(temp_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        temp_file.close()

        yield temp_file.name

        # Cleanup
        Path(temp_file.name).unlink()

    def test_complete_workflow(self, sample_csv_file):
        """Test complete workflow from loading to ranking."""
        # Step 1: Load options from CSV
        options = load_options_from_csv(sample_csv_file)
        assert len(options) > 0

        # Step 2: Apply hard filters
        filter_config = FilterConfig(
            min_iv_rank=40.0,
            max_bid_ask_spread_pct=0.15,
            min_open_interest=500,
            min_volume=100,
        )

        filtered_options = filter_options(
            options,
            iv_rank=65.0,
            iv_percentile=70.0,
            config=filter_config,
        )

        assert len(filtered_options) > 0
        assert len(filtered_options) <= len(options)

        # Step 3: Generate iron condor candidates
        strategy_config = StrategyConfig(
            min_dte=30,
            max_dte=45,
            min_delta=0.15,
            max_delta=0.25,
            wing_width_put=5.0,
            wing_width_call=5.0,
        )

        condors = list(generate_iron_condors(filtered_options, strategy_config))

        assert len(condors) > 0

        # Verify condor structure
        for condor in condors:
            assert condor.ticker == "SPY"
            assert condor.net_credit > 0
            assert condor.max_loss > 0
            assert condor.return_on_risk > 0

        # Step 4: Analyze each condor
        spot_price = 560.0
        historical_ivs = [0.18, 0.20, 0.22, 0.24, 0.26, 0.28, 0.30]
        realized_vol = 0.20

        analytics_list = []
        for condor in condors:
            analytics = analyze_iron_condor(
                iron_condor=condor,
                spot_price=spot_price,
                historical_ivs=historical_ivs,
                realized_vol_20d=realized_vol,
            )
            analytics_list.append(analytics)

        assert len(analytics_list) == len(condors)

        # Verify analytics
        for analytics in analytics_list:
            assert analytics.spot_price == spot_price
            assert analytics.expected_move_straddle > 0
            assert analytics.iv_rank > 0
            assert analytics.liquidity_score > 0

        # Step 5: Score and rank
        scoring_config = ScoringConfig()
        ranked = rank_analytics(analytics_list, scoring_config, top_n=5)

        assert len(ranked) > 0
        assert len(ranked) <= 5

        # Verify ranking
        for analytics in ranked:
            assert analytics.composite_score is not None
            assert 0.0 <= analytics.composite_score <= 1.0

        # Verify descending order
        for i in range(len(ranked) - 1):
            assert ranked[i].composite_score >= ranked[i + 1].composite_score

    def test_workflow_with_option_chain_data(self, sample_csv_file):
        """Test workflow using OptionChainData container."""
        # Load options
        options = load_options_from_csv(sample_csv_file)

        # Create OptionChainData
        chain_data = OptionChainData(
            options=options,
            spot_price=560.0,
            historical_ivs=[0.18, 0.20, 0.22, 0.24, 0.26, 0.28],
            earnings_date="2025-02-20",
        )

        assert chain_data.ticker == "SPY"
        assert chain_data.spot_price == 560.0
        assert len(chain_data.historical_ivs) == 6
        assert chain_data.earnings_date == "2025-02-20"

    def test_workflow_no_candidates(self):
        """Test workflow when filters are too strict (no candidates)."""
        exp = (date.today() + timedelta(days=35)).strftime('%Y-%m-%d')

        # Create minimal option chain
        rows = [
            {
                'ticker': 'SPY',
                'strike': '540.0',
                'expiration': exp,
                'option_type': 'put',
                'bid': '2.0',
                'ask': '2.5',
                'volume': '10',  # Very low volume
                'open_interest': '50',  # Very low OI
                'delta': '-0.20',
                'implied_vol': '0.25',
            },
        ]

        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
        fieldnames = [
            'ticker', 'strike', 'expiration', 'option_type', 'bid', 'ask',
            'volume', 'open_interest', 'delta', 'implied_vol'
        ]

        writer = csv.DictWriter(temp_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        temp_file.close()

        try:
            # Load and filter
            options = load_options_from_csv(temp_file.name)

            filter_config = FilterConfig(
                min_open_interest=1000,  # Too high
                min_volume=100,  # Too high
            )

            filtered = filter_options(
                options,
                iv_rank=65.0,
                iv_percentile=70.0,
                config=filter_config,
            )

            # Should have no options after filtering
            assert len(filtered) == 0

            # Generate condors (should be empty)
            strategy_config = StrategyConfig()
            condors = list(generate_iron_condors(filtered, strategy_config))

            assert len(condors) == 0

        finally:
            Path(temp_file.name).unlink()

    def test_workflow_multiple_expirations(self):
        """Test workflow with multiple expiration dates."""
        exp1 = (date.today() + timedelta(days=35)).strftime('%Y-%m-%d')
        exp2 = (date.today() + timedelta(days=42)).strftime('%Y-%m-%d')

        rows = []

        # Add options for both expirations
        for exp in [exp1, exp2]:
            rows.extend([
                {
                    'ticker': 'SPY',
                    'strike': '535.0',
                    'expiration': exp,
                    'option_type': 'put',
                    'bid': '2.0',
                    'ask': '2.2',
                    'volume': '1000',
                    'open_interest': '5000',
                    'delta': '-0.15',
                    'implied_vol': '0.25',
                },
                {
                    'ticker': 'SPY',
                    'strike': '540.0',
                    'expiration': exp,
                    'option_type': 'put',
                    'bid': '2.8',
                    'ask': '3.0',
                    'volume': '1200',
                    'open_interest': '6000',
                    'delta': '-0.20',
                    'implied_vol': '0.25',
                },
                {
                    'ticker': 'SPY',
                    'strike': '580.0',
                    'expiration': exp,
                    'option_type': 'call',
                    'bid': '2.8',
                    'ask': '3.0',
                    'volume': '1200',
                    'open_interest': '6000',
                    'delta': '0.20',
                    'implied_vol': '0.25',
                },
                {
                    'ticker': 'SPY',
                    'strike': '585.0',
                    'expiration': exp,
                    'option_type': 'call',
                    'bid': '2.0',
                    'ask': '2.2',
                    'volume': '1000',
                    'open_interest': '5000',
                    'delta': '0.15',
                    'implied_vol': '0.25',
                },
            ])

        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
        fieldnames = [
            'ticker', 'strike', 'expiration', 'option_type', 'bid', 'ask',
            'volume', 'open_interest', 'delta', 'implied_vol'
        ]

        writer = csv.DictWriter(temp_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        temp_file.close()

        try:
            options = load_options_from_csv(temp_file.name)

            # Should have options for both expirations
            expirations = {opt.expiration for opt in options}
            assert len(expirations) == 2

            # Generate condors
            strategy_config = StrategyConfig(min_dte=30, max_dte=45)
            condors = list(generate_iron_condors(options, strategy_config))

            # Should generate condors for both expirations
            condor_expirations = {c.expiration for c in condors}
            assert len(condor_expirations) == 2

        finally:
            Path(temp_file.name).unlink()

    def test_workflow_scoring_consistency(self, sample_csv_file):
        """Test that scoring is consistent and deterministic."""
        # Run workflow twice
        results1 = self._run_workflow(sample_csv_file)
        results2 = self._run_workflow(sample_csv_file)

        # Results should be identical
        assert len(results1) == len(results2)

        for i in range(len(results1)):
            assert abs(results1[i].composite_score - results2[i].composite_score) < 0.001

    def _run_workflow(self, csv_file):
        """Helper to run complete workflow."""
        options = load_options_from_csv(csv_file)

        filter_config = FilterConfig()
        filtered = filter_options(options, iv_rank=65.0, iv_percentile=70.0, config=filter_config)

        strategy_config = StrategyConfig()
        condors = list(generate_iron_condors(filtered, strategy_config))

        analytics_list = []
        for condor in condors:
            analytics = analyze_iron_condor(
                condor,
                spot_price=560.0,
                historical_ivs=[0.20, 0.25],
                realized_vol_20d=0.20,
            )
            analytics_list.append(analytics)

        scoring_config = ScoringConfig()
        return rank_analytics(analytics_list, scoring_config)

    def test_workflow_edge_case_zero_credit(self):
        """Test workflow handles zero/negative credit condors gracefully."""
        exp = (date.today() + timedelta(days=35)).strftime('%Y-%m-%d')

        # Create options where long legs are more expensive (no credit)
        rows = [
            {
                'ticker': 'SPY',
                'strike': '540.0',
                'expiration': exp,
                'option_type': 'put',
                'bid': '1.0',
                'ask': '1.2',
                'volume': '1000',
                'open_interest': '5000',
                'delta': '-0.20',
                'implied_vol': '0.25',
            },
            {
                'ticker': 'SPY',
                'strike': '535.0',
                'expiration': exp,
                'option_type': 'put',
                'bid': '3.0',
                'ask': '3.2',
                'volume': '800',
                'open_interest': '4000',
                'delta': '-0.15',
                'implied_vol': '0.24',
            },
            {
                'ticker': 'SPY',
                'strike': '580.0',
                'expiration': exp,
                'option_type': 'call',
                'bid': '1.0',
                'ask': '1.2',
                'volume': '1000',
                'open_interest': '5000',
                'delta': '0.20',
                'implied_vol': '0.25',
            },
            {
                'ticker': 'SPY',
                'strike': '585.0',
                'expiration': exp,
                'option_type': 'call',
                'bid': '3.0',
                'ask': '3.2',
                'volume': '800',
                'open_interest': '4000',
                'delta': '0.15',
                'implied_vol': '0.24',
            },
        ]

        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
        fieldnames = [
            'ticker', 'strike', 'expiration', 'option_type', 'bid', 'ask',
            'volume', 'open_interest', 'delta', 'implied_vol'
        ]

        writer = csv.DictWriter(temp_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        temp_file.close()

        try:
            options = load_options_from_csv(temp_file.name)

            strategy_config = StrategyConfig()
            condors = list(generate_iron_condors(options, strategy_config))

            # Should generate no valid condors (credit <= 0)
            assert len(condors) == 0

        finally:
            Path(temp_file.name).unlink()
