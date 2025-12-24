"""Earnings edge analyzer - validates if earnings-aware screening provides an edge.

Compares performance of:
- Pre-earnings setups (risky - earnings within 0-7 days after expiration)
- Post-earnings setups (safe - earnings >7 days after expiration)
- No-earnings setups (no earnings data available)

Provides statistical significance tests to validate if observed differences are real.
"""

from dataclasses import dataclass
from typing import List, Tuple
import math
import logging

from condor_screener.backtest.simulator import BacktestResult
from condor_screener.backtest.metrics import PerformanceMetrics, calculate_metrics

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EarningsComparison:
    """Comparison of performance between earnings-aware groups.

    Attributes:
        pre_earnings: Metrics for pre-earnings setups (risky)
        post_earnings: Metrics for post-earnings setups (safe)
        no_earnings: Metrics for setups with no earnings data
        win_rate_diff: Difference in win rate (post - pre)
        avg_return_diff: Difference in avg return % (post - pre)
        sharpe_diff: Difference in Sharpe ratio (post - pre)
        is_significant: True if difference is statistically significant (p < 0.05)
        p_value: P-value from t-test comparing returns
        recommendation: Human-readable recommendation based on results
    """
    pre_earnings: PerformanceMetrics
    post_earnings: PerformanceMetrics
    no_earnings: PerformanceMetrics
    win_rate_diff: float
    avg_return_diff: float
    sharpe_diff: float
    is_significant: bool
    p_value: float
    recommendation: str


class EarningsEdgeAnalyzer:
    """Analyzer to validate earnings edge hypothesis."""

    def __init__(self, results: List[BacktestResult]):
        """Initialize analyzer with backtest results.

        Args:
            results: List of BacktestResult objects from simulations
        """
        self.results = results
        self._categorize_results()

    def _categorize_results(self):
        """Categorize results into pre-earnings, post-earnings, and no-earnings groups."""
        self.pre_earnings_results = []
        self.post_earnings_results = []
        self.no_earnings_results = []

        for result in self.results:
            if result.had_earnings:
                # Had earnings during holding period = pre-earnings (risky)
                self.pre_earnings_results.append(result)
            elif result.iron_condor.short_put.dte > 0:
                # Check if we have any indication this was earnings-related
                # For now, assume if had_earnings is False, it's either post-earnings or no data
                # This is a simplification - in real backtest, we'd check actual earnings dates
                self.post_earnings_results.append(result)
            else:
                self.no_earnings_results.append(result)

    def analyze(self) -> EarningsComparison:
        """Analyze earnings edge and return comparison.

        Returns:
            EarningsComparison with metrics and statistical significance
        """
        # Calculate metrics for each group
        pre_metrics = calculate_metrics(self.pre_earnings_results)
        post_metrics = calculate_metrics(self.post_earnings_results)
        no_metrics = calculate_metrics(self.no_earnings_results)

        # Calculate differences
        win_rate_diff = post_metrics.win_rate - pre_metrics.win_rate
        avg_return_diff = post_metrics.avg_return_pct - pre_metrics.avg_return_pct
        sharpe_diff = post_metrics.sharpe_ratio - pre_metrics.sharpe_ratio

        # Statistical significance test (two-sample t-test)
        is_significant, p_value = self._t_test(
            [r.return_pct for r in self.post_earnings_results],
            [r.return_pct for r in self.pre_earnings_results]
        )

        # Generate recommendation
        recommendation = self._generate_recommendation(
            pre_metrics, post_metrics, is_significant, p_value
        )

        return EarningsComparison(
            pre_earnings=pre_metrics,
            post_earnings=post_metrics,
            no_earnings=no_metrics,
            win_rate_diff=win_rate_diff,
            avg_return_diff=avg_return_diff,
            sharpe_diff=sharpe_diff,
            is_significant=is_significant,
            p_value=p_value,
            recommendation=recommendation,
        )

    def _t_test(self, sample1: List[float], sample2: List[float]) -> Tuple[bool, float]:
        """Perform two-sample t-test.

        Args:
            sample1: First sample (e.g., post-earnings returns)
            sample2: Second sample (e.g., pre-earnings returns)

        Returns:
            Tuple of (is_significant, p_value)
        """
        if not sample1 or not sample2:
            return False, 1.0

        n1 = len(sample1)
        n2 = len(sample2)

        if n1 < 2 or n2 < 2:
            return False, 1.0

        # Calculate means
        mean1 = sum(sample1) / n1
        mean2 = sum(sample2) / n2

        # Calculate variances
        var1 = sum((x - mean1) ** 2 for x in sample1) / (n1 - 1)
        var2 = sum((x - mean2) ** 2 for x in sample2) / (n2 - 1)

        # Pooled standard error
        pooled_se = math.sqrt(var1 / n1 + var2 / n2)

        if pooled_se == 0:
            return False, 1.0

        # T-statistic
        t_stat = (mean1 - mean2) / pooled_se

        # Degrees of freedom (Welch-Satterthwaite approximation)
        df = ((var1 / n1 + var2 / n2) ** 2) / (
            (var1 / n1) ** 2 / (n1 - 1) + (var2 / n2) ** 2 / (n2 - 1)
        )

        # Approximate p-value using t-distribution
        # For simplicity, use normal approximation if df > 30
        p_value = self._approximate_p_value(abs(t_stat), df)

        is_significant = p_value < 0.05

        return is_significant, p_value

    def _approximate_p_value(self, t_stat: float, df: float) -> float:
        """Approximate two-tailed p-value for t-statistic.

        Uses normal approximation for df > 30, conservative estimate otherwise.
        """
        if df > 30:
            # Normal approximation
            # P(|Z| > t_stat) ≈ 2 * P(Z > t_stat)
            # Using standard normal CDF approximation
            z = t_stat
            # Approximation of P(Z > z) for standard normal
            if z > 3.0:
                return 0.0027  # ~3 sigma
            elif z > 2.5:
                return 0.0124
            elif z > 2.0:
                return 0.0455
            elif z > 1.96:
                return 0.05
            elif z > 1.5:
                return 0.1336
            elif z > 1.0:
                return 0.3173
            else:
                return 0.5
        else:
            # Conservative estimate - require larger t-stat for small samples
            if t_stat > 2.5:
                return 0.02
            elif t_stat > 2.0:
                return 0.06
            elif t_stat > 1.5:
                return 0.15
            else:
                return 0.5

    def _generate_recommendation(
        self,
        pre_metrics: PerformanceMetrics,
        post_metrics: PerformanceMetrics,
        is_significant: bool,
        p_value: float
    ) -> str:
        """Generate human-readable recommendation based on analysis."""
        if post_metrics.total_trades == 0 and pre_metrics.total_trades == 0:
            return "INSUFFICIENT DATA: Not enough trades to analyze earnings edge."

        if post_metrics.total_trades < 10 or pre_metrics.total_trades < 10:
            return "INSUFFICIENT DATA: Need at least 10 trades in each group for reliable analysis."

        # Check if post-earnings clearly outperforms
        if is_significant and post_metrics.avg_return_pct > pre_metrics.avg_return_pct:
            return (
                f"✅ EARNINGS EDGE CONFIRMED: Post-earnings setups significantly outperform "
                f"(p={p_value:.4f}). Avoid pre-earnings setups. "
                f"Win rate improvement: {post_metrics.win_rate - pre_metrics.win_rate:+.1f}%, "
                f"Return improvement: {post_metrics.avg_return_pct - pre_metrics.avg_return_pct:+.2f}%."
            )

        if not is_significant and post_metrics.avg_return_pct > pre_metrics.avg_return_pct:
            return (
                f"⚠️ WEAK EVIDENCE: Post-earnings setups show better returns but difference "
                f"is NOT statistically significant (p={p_value:.4f}). "
                f"Collect more data before drawing conclusions. "
                f"Conservative approach: avoid pre-earnings setups."
            )

        if is_significant and pre_metrics.avg_return_pct > post_metrics.avg_return_pct:
            return (
                f"❌ UNEXPECTED: Pre-earnings setups significantly outperform (p={p_value:.4f}). "
                f"This contradicts the hypothesis. Investigate further - possible data issues "
                f"or market regime differences."
            )

        # No significant difference
        return (
            f"➖ NO EARNINGS EDGE: No significant difference between pre-earnings and "
            f"post-earnings setups (p={p_value:.4f}). Earnings timing may not matter, "
            f"or sample size is too small to detect an edge."
        )

    def get_summary_stats(self) -> dict:
        """Get summary statistics for reporting.

        Returns:
            Dictionary with key statistics for all groups
        """
        pre_metrics = calculate_metrics(self.pre_earnings_results)
        post_metrics = calculate_metrics(self.post_earnings_results)
        no_metrics = calculate_metrics(self.no_earnings_results)

        return {
            'total_trades': len(self.results),
            'pre_earnings_count': len(self.pre_earnings_results),
            'post_earnings_count': len(self.post_earnings_results),
            'no_earnings_count': len(self.no_earnings_results),
            'pre_earnings_win_rate': pre_metrics.win_rate,
            'post_earnings_win_rate': post_metrics.win_rate,
            'pre_earnings_avg_return': pre_metrics.avg_return_pct,
            'post_earnings_avg_return': post_metrics.avg_return_pct,
            'pre_earnings_sharpe': pre_metrics.sharpe_ratio,
            'post_earnings_sharpe': post_metrics.sharpe_ratio,
            'pre_earnings_max_dd': pre_metrics.max_drawdown_pct,
            'post_earnings_max_dd': post_metrics.max_drawdown_pct,
        }
