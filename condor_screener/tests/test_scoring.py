"""Unit tests for scoring system."""

import pytest
from datetime import date, timedelta

from condor_screener.scoring.scorer import (
    ScoringConfig,
    score_analytics,
    normalize,
    rank_analytics,
    adaptive_normalization,
)
from condor_screener.models.option import Option
from condor_screener.models.iron_condor import IronCondor
from condor_screener.models.analytics import Analytics


class TestScoringConfig:
    """Test suite for ScoringConfig."""

    def test_scoring_config_defaults(self):
        """Test ScoringConfig with default values."""
        config = ScoringConfig()

        assert config.weight_ror == 0.30
        assert config.weight_distance == 0.30
        assert config.weight_liquidity == 0.20
        assert config.weight_iv_edge == 0.20

        # Weights should sum to 1.0
        total = (config.weight_ror + config.weight_distance +
                config.weight_liquidity + config.weight_iv_edge)
        assert abs(total - 1.0) < 0.01

    def test_scoring_config_custom(self):
        """Test ScoringConfig with custom values."""
        config = ScoringConfig(
            weight_ror=0.40,
            weight_distance=0.30,
            weight_liquidity=0.15,
            weight_iv_edge=0.15,
        )

        assert config.weight_ror == 0.40
        assert config.weight_distance == 0.30

    def test_scoring_config_normalization_ranges(self):
        """Test normalization range defaults."""
        config = ScoringConfig()

        assert config.ror_min == 10.0
        assert config.ror_max == 50.0
        assert config.distance_min == 0.0
        assert config.distance_max == 15.0
        assert config.iv_ratio_min == 1.0
        assert config.iv_ratio_max == 2.0

    def test_scoring_config_from_dict(self):
        """Test creating ScoringConfig from dictionary."""
        config_dict = {
            'weights': {
                'return_on_risk': 0.40,
                'distance_from_em': 0.25,
                'liquidity': 0.20,
                'iv_edge': 0.15,
            },
            'normalization': {
                'ror_min': 15.0,
                'ror_max': 60.0,
            }
        }

        config = ScoringConfig.from_dict(config_dict)

        assert config.weight_ror == 0.40
        assert config.weight_distance == 0.25
        assert config.ror_min == 15.0
        assert config.ror_max == 60.0

    def test_scoring_config_weight_validation(self, capsys):
        """Test weight sum validation warning."""
        config = ScoringConfig(
            weight_ror=0.50,
            weight_distance=0.30,
            weight_liquidity=0.10,
            weight_iv_edge=0.05,
        )

        captured = capsys.readouterr()
        # Weights sum to 0.95, not 1.0
        assert "Warning" in captured.out


class TestNormalize:
    """Test suite for normalize function."""

    def test_normalize_middle(self):
        """Test normalization at middle of range."""
        result = normalize(50.0, min_val=0.0, max_val=100.0)
        assert abs(result - 0.5) < 0.01

    def test_normalize_min(self):
        """Test normalization at minimum."""
        result = normalize(0.0, min_val=0.0, max_val=100.0)
        assert abs(result - 0.0) < 0.01

    def test_normalize_max(self):
        """Test normalization at maximum."""
        result = normalize(100.0, min_val=0.0, max_val=100.0)
        assert abs(result - 1.0) < 0.01

    def test_normalize_below_min(self):
        """Test normalization below minimum (clamped)."""
        result = normalize(-50.0, min_val=0.0, max_val=100.0)
        assert result == 0.0

    def test_normalize_above_max(self):
        """Test normalization above maximum (clamped)."""
        result = normalize(150.0, min_val=0.0, max_val=100.0)
        assert result == 1.0

    def test_normalize_no_range(self):
        """Test normalization when min equals max."""
        result = normalize(50.0, min_val=50.0, max_val=50.0)
        assert result == 0.5


class TestScoreAnalytics:
    """Test suite for score_analytics function."""

    @pytest.fixture
    def sample_analytics(self):
        """Create sample analytics object."""
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
        )

    def test_score_analytics_returns_new_object(self, sample_analytics):
        """Test that scoring returns a new Analytics object."""
        config = ScoringConfig()
        scored = score_analytics(sample_analytics, config)

        # Should be a different object
        assert scored is not sample_analytics

        # Original should not have score
        assert sample_analytics.composite_score is None

        # New object should have score
        assert scored.composite_score is not None

    def test_score_analytics_range(self, sample_analytics):
        """Test that composite score is in valid range."""
        config = ScoringConfig()
        scored = score_analytics(sample_analytics, config)

        # Score should be between 0 and 1
        assert 0.0 <= scored.composite_score <= 1.0

    def test_score_analytics_components(self, sample_analytics):
        """Test scoring components individually."""
        config = ScoringConfig(
            weight_ror=1.0,
            weight_distance=0.0,
            weight_liquidity=0.0,
            weight_iv_edge=0.0,
        )

        scored = score_analytics(sample_analytics, config)

        # Score should be based only on ROR
        # ROR ≈ 47%, normalized to [10, 50] range
        ror = sample_analytics.iron_condor.return_on_risk
        expected_normalized = normalize(ror, 10.0, 50.0)

        assert abs(scored.composite_score - expected_normalized) < 0.01

    def test_score_analytics_high_quality(self):
        """Test scoring for high-quality trade."""
        exp = date.today() + timedelta(days=35)

        # Create high ROR condor
        short_put = Option(
            ticker="SPY", strike=540.0, expiration=exp, option_type="put",
            bid=3.8, ask=4.0, volume=2000, open_interest=10000,
            delta=-0.20, implied_vol=0.30
        )
        long_put = Option(
            ticker="SPY", strike=535.0, expiration=exp, option_type="put",
            bid=1.0, ask=1.2, volume=1500, open_interest=8000,
            delta=-0.15, implied_vol=0.29
        )
        short_call = Option(
            ticker="SPY", strike=600.0, expiration=exp, option_type="call",
            bid=3.8, ask=4.0, volume=2000, open_interest=10000,
            delta=0.20, implied_vol=0.30
        )
        long_call = Option(
            ticker="SPY", strike=605.0, expiration=exp, option_type="call",
            bid=1.0, ask=1.2, volume=1500, open_interest=8000,
            delta=0.15, implied_vol=0.29
        )

        ic = IronCondor(
            ticker="SPY", expiration=exp,
            short_put=short_put, long_put=long_put,
            short_call=short_call, long_call=long_call,
        )

        analytics = Analytics(
            iron_condor=ic,
            spot_price=560.0,
            expected_move_straddle=25.0,
            expected_move_iv=24.0,
            put_distance_dollars=40.0,  # Far OTM
            call_distance_dollars=40.0,
            put_distance_pct=7.14,
            call_distance_pct=7.14,
            iv_rank=75.0,  # High IV
            iv_percentile=80.0,
            realized_vol_20d=0.20,
            iv_to_rv_ratio=1.50,  # Good IV edge
            is_pre_earnings=False,
            earnings_date=None,
            liquidity_score=0.90,  # Good liquidity
        )

        config = ScoringConfig()
        scored = score_analytics(analytics, config)

        # High quality trade should score reasonably well
        # Note: With single analytics object, normalization is limited
        assert scored.composite_score > 0.3

    def test_score_analytics_poor_quality(self):
        """Test scoring for poor-quality trade."""
        exp = date.today() + timedelta(days=35)

        short_put = Option(
            ticker="SPY", strike=555.0, expiration=exp, option_type="put",
            bid=8.0, ask=10.0, volume=10, open_interest=100,
            delta=-0.40, implied_vol=0.20
        )
        long_put = Option(
            ticker="SPY", strike=550.0, expiration=exp, option_type="put",
            bid=7.0, ask=9.0, volume=5, open_interest=50,
            delta=-0.35, implied_vol=0.19
        )
        short_call = Option(
            ticker="SPY", strike=565.0, expiration=exp, option_type="call",
            bid=8.0, ask=10.0, volume=10, open_interest=100,
            delta=0.40, implied_vol=0.20
        )
        long_call = Option(
            ticker="SPY", strike=570.0, expiration=exp, option_type="call",
            bid=7.0, ask=9.0, volume=5, open_interest=50,
            delta=0.35, implied_vol=0.19
        )

        ic = IronCondor(
            ticker="SPY", expiration=exp,
            short_put=short_put, long_put=long_put,
            short_call=short_call, long_call=long_call,
        )

        analytics = Analytics(
            iron_condor=ic,
            spot_price=560.0,
            expected_move_straddle=25.0,
            expected_move_iv=24.0,
            put_distance_dollars=5.0,  # Close to spot
            call_distance_dollars=5.0,
            put_distance_pct=0.89,
            call_distance_pct=0.89,
            iv_rank=20.0,  # Low IV
            iv_percentile=25.0,
            realized_vol_20d=0.25,
            iv_to_rv_ratio=0.80,  # Poor IV edge
            is_pre_earnings=False,
            earnings_date=None,
            liquidity_score=0.20,  # Poor liquidity
        )

        config = ScoringConfig()
        scored = score_analytics(analytics, config)

        # Poor quality trade should score low
        assert scored.composite_score < 0.4


class TestRankAnalytics:
    """Test suite for rank_analytics function."""

    @pytest.fixture
    def analytics_list(self):
        """Create a list of analytics with different scores."""
        exp = date.today() + timedelta(days=35)

        analytics = []
        scores = [0.8, 0.5, 0.9, 0.3, 0.7]

        for i, _ in enumerate(scores):
            short_put = Option(
                ticker="SPY", strike=540.0 - i*5, expiration=exp, option_type="put",
                bid=2.8, ask=3.0, volume=1000, open_interest=5000,
                delta=-0.20, implied_vol=0.25
            )
            long_put = Option(
                ticker="SPY", strike=535.0 - i*5, expiration=exp, option_type="put",
                bid=2.0, ask=2.2, volume=800, open_interest=4000,
                delta=-0.15, implied_vol=0.24
            )
            short_call = Option(
                ticker="SPY", strike=580.0 + i*5, expiration=exp, option_type="call",
                bid=2.8, ask=3.0, volume=1000, open_interest=5000,
                delta=0.20, implied_vol=0.25
            )
            long_call = Option(
                ticker="SPY", strike=585.0 + i*5, expiration=exp, option_type="call",
                bid=2.0, ask=2.2, volume=800, open_interest=4000,
                delta=0.15, implied_vol=0.24
            )

            ic = IronCondor(
                ticker="SPY", expiration=exp,
                short_put=short_put, long_put=long_put,
                short_call=short_call, long_call=long_call,
            )

            analytics.append(Analytics(
                iron_condor=ic,
                spot_price=560.0,
                expected_move_straddle=25.0,
                expected_move_iv=24.0,
                put_distance_dollars=20.0 + i*5,
                call_distance_dollars=20.0 + i*5,
                put_distance_pct=3.57 + i,
                call_distance_pct=3.57 + i,
                iv_rank=65.0,
                iv_percentile=68.0,
                realized_vol_20d=0.20,
                iv_to_rv_ratio=1.25,
                is_pre_earnings=False,
                earnings_date=None,
                liquidity_score=0.75,
            ))

        return analytics

    def test_rank_analytics_ordering(self, analytics_list):
        """Test that analytics are sorted by score."""
        config = ScoringConfig()
        ranked = rank_analytics(analytics_list, config)

        # Should be sorted descending by score
        for i in range(len(ranked) - 1):
            assert ranked[i].composite_score >= ranked[i + 1].composite_score

    def test_rank_analytics_all_scored(self, analytics_list):
        """Test that all analytics receive scores."""
        config = ScoringConfig()
        ranked = rank_analytics(analytics_list, config)

        assert len(ranked) == len(analytics_list)

        for analytics in ranked:
            assert analytics.composite_score is not None

    def test_rank_analytics_top_n(self, analytics_list):
        """Test limiting to top N results."""
        config = ScoringConfig()
        ranked = rank_analytics(analytics_list, config, top_n=3)

        assert len(ranked) == 3

        # Should be the top 3 scores
        all_ranked = rank_analytics(analytics_list, config)
        assert ranked[0].composite_score == all_ranked[0].composite_score
        assert ranked[1].composite_score == all_ranked[1].composite_score
        assert ranked[2].composite_score == all_ranked[2].composite_score

    def test_rank_analytics_empty_list(self):
        """Test ranking empty list."""
        config = ScoringConfig()
        ranked = rank_analytics([], config)

        assert len(ranked) == 0


class TestAdaptiveNormalization:
    """Test suite for adaptive normalization."""

    @pytest.fixture
    def analytics_for_normalization(self):
        """Create analytics with known ranges."""
        exp = date.today() + timedelta(days=35)
        analytics = []

        rors = [15.0, 25.0, 35.0, 45.0]
        distances = [2.0, 5.0, 8.0, 12.0]
        iv_ratios = [1.1, 1.3, 1.5, 1.8]

        for i in range(4):
            short_put = Option(
                ticker="SPY", strike=540.0, expiration=exp, option_type="put",
                bid=2.0 + i*0.5, ask=2.2 + i*0.5, volume=1000, open_interest=5000,
                delta=-0.20, implied_vol=0.25
            )
            long_put = Option(
                ticker="SPY", strike=535.0, expiration=exp, option_type="put",
                bid=1.5, ask=1.7, volume=800, open_interest=4000,
                delta=-0.15, implied_vol=0.24
            )
            short_call = Option(
                ticker="SPY", strike=580.0, expiration=exp, option_type="call",
                bid=2.0 + i*0.5, ask=2.2 + i*0.5, volume=1000, open_interest=5000,
                delta=0.20, implied_vol=0.25
            )
            long_call = Option(
                ticker="SPY", strike=585.0, expiration=exp, option_type="call",
                bid=1.5, ask=1.7, volume=800, open_interest=4000,
                delta=0.15, implied_vol=0.24
            )

            ic = IronCondor(
                ticker="SPY", expiration=exp,
                short_put=short_put, long_put=long_put,
                short_call=short_call, long_call=long_call,
            )

            analytics.append(Analytics(
                iron_condor=ic,
                spot_price=560.0,
                expected_move_straddle=25.0,
                expected_move_iv=24.0,
                put_distance_dollars=distances[i],
                call_distance_dollars=distances[i],
                put_distance_pct=distances[i],
                call_distance_pct=distances[i],
                iv_rank=65.0,
                iv_percentile=68.0,
                realized_vol_20d=0.20,
                iv_to_rv_ratio=iv_ratios[i],
                is_pre_earnings=False,
                earnings_date=None,
                liquidity_score=0.75,
            ))

        return analytics

    def test_adaptive_normalization_ranges(self, analytics_for_normalization):
        """Test that adaptive normalization computes correct ranges."""
        config = adaptive_normalization(analytics_for_normalization)

        # Check that ranges match data
        rors = [a.iron_condor.return_on_risk for a in analytics_for_normalization]
        assert config.ror_min == min(rors)
        assert config.ror_max == max(rors)

        distances = [a.avg_distance_pct for a in analytics_for_normalization]
        assert config.distance_min == min(distances)
        assert config.distance_max == max(distances)

        iv_ratios = [a.iv_to_rv_ratio for a in analytics_for_normalization]
        assert config.iv_ratio_min == min(iv_ratios)
        assert config.iv_ratio_max == max(iv_ratios)

    def test_adaptive_normalization_empty(self):
        """Test adaptive normalization with empty list."""
        config = adaptive_normalization([])

        # Should return default config
        assert config.ror_min == 10.0
        assert config.ror_max == 50.0
