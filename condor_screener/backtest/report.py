"""Report generator for backtest results and earnings edge analysis."""

from datetime import datetime
from pathlib import Path
from typing import List
import logging

from condor_screener.backtest.simulator import BacktestResult
from condor_screener.backtest.metrics import PerformanceMetrics
from condor_screener.backtest.earnings_analyzer import EarningsComparison

logger = logging.getLogger(__name__)


def generate_earnings_edge_report(
    comparison: EarningsComparison,
    results: List[BacktestResult],
    output_path: str | Path = "EARNINGS_EDGE_REPORT.md"
) -> str:
    """Generate comprehensive markdown report for earnings edge validation.

    Args:
        comparison: EarningsComparison object with analysis results
        results: List of all BacktestResult objects
        output_path: Path to save report (default: EARNINGS_EDGE_REPORT.md)

    Returns:
        Path to generated report
    """
    output_path = Path(output_path)

    # Generate report content
    report = _build_report_content(comparison, results)

    # Write to file
    with open(output_path, 'w') as f:
        f.write(report)

    logger.info(f"Earnings edge report generated: {output_path}")
    return str(output_path)


def _build_report_content(comparison: EarningsComparison, results: List[BacktestResult]) -> str:
    """Build the complete report content."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    report = f"""# 📊 Earnings Edge Validation Report

**Generated**: {timestamp}
**Total Trades Analyzed**: {len(results)}

---

## 🎯 Executive Summary

{comparison.recommendation}

---

## 📈 Performance Comparison

### Pre-Earnings Setups (Risky - Earnings within 0-7 days after expiration)

{_format_metrics_table(comparison.pre_earnings)}

### Post-Earnings Setups (Safe - Earnings >7 days after expiration or before entry)

{_format_metrics_table(comparison.post_earnings)}

### No-Earnings Data Setups

{_format_metrics_table(comparison.no_earnings)}

---

## 📊 Key Differences

| Metric | Pre-Earnings | Post-Earnings | Difference | Better |
|--------|--------------|---------------|------------|--------|
| **Win Rate** | {comparison.pre_earnings.win_rate:.1f}% | {comparison.post_earnings.win_rate:.1f}% | {comparison.win_rate_diff:+.1f}% | {"✅ Post" if comparison.win_rate_diff > 0 else "❌ Pre"} |
| **Avg Return** | {comparison.pre_earnings.avg_return_pct:.2f}% | {comparison.post_earnings.avg_return_pct:.2f}% | {comparison.avg_return_diff:+.2f}% | {"✅ Post" if comparison.avg_return_diff > 0 else "❌ Pre"} |
| **Sharpe Ratio** | {comparison.pre_earnings.sharpe_ratio:.2f} | {comparison.post_earnings.sharpe_ratio:.2f} | {comparison.sharpe_diff:+.2f} | {"✅ Post" if comparison.sharpe_diff > 0 else "❌ Pre"} |
| **Max Drawdown** | {comparison.pre_earnings.max_drawdown_pct:.1f}% | {comparison.post_earnings.max_drawdown_pct:.1f}% | {comparison.post_earnings.max_drawdown_pct - comparison.pre_earnings.max_drawdown_pct:+.1f}% | {"✅ Post" if comparison.post_earnings.max_drawdown_pct < comparison.pre_earnings.max_drawdown_pct else "❌ Pre"} |
| **Profit Factor** | {comparison.pre_earnings.profit_factor:.2f} | {comparison.post_earnings.profit_factor:.2f} | {comparison.post_earnings.profit_factor - comparison.pre_earnings.profit_factor:+.2f} | {"✅ Post" if comparison.post_earnings.profit_factor > comparison.pre_earnings.profit_factor else "❌ Pre"} |

**Statistical Significance**: {"✅ YES (p={:.4f})".format(comparison.p_value) if comparison.is_significant else "❌ NO (p={:.4f})".format(comparison.p_value)}

---

## 🔬 Statistical Analysis

### Hypothesis Test

**Null Hypothesis (H0)**: There is no difference in returns between pre-earnings and post-earnings setups.

**Alternative Hypothesis (H1)**: Post-earnings setups have different returns than pre-earnings setups.

**Test**: Two-sample t-test (two-tailed)

**Result**: {"REJECT H0" if comparison.is_significant else "FAIL TO REJECT H0"}

**P-value**: {comparison.p_value:.4f}

**Interpretation**: {_interpret_p_value(comparison.p_value, comparison.is_significant)}

---

## 📉 Exit Reason Analysis

{_analyze_exit_reasons(results)}

---

## 💡 Recommendations

{_generate_actionable_recommendations(comparison)}

---

## 🔍 Detailed Trade Statistics

### Pre-Earnings Trades
- **Total Trades**: {comparison.pre_earnings.total_trades}
- **Winners**: {comparison.pre_earnings.winners} ({comparison.pre_earnings.win_rate:.1f}%)
- **Losers**: {comparison.pre_earnings.losers}
- **Avg Winner**: {comparison.pre_earnings.avg_winner_pct:.2f}%
- **Avg Loser**: {comparison.pre_earnings.avg_loser_pct:.2f}%
- **Best Trade**: {comparison.pre_earnings.best_trade_pct:.2f}%
- **Worst Trade**: {comparison.pre_earnings.worst_trade_pct:.2f}%
- **Avg Days Held**: {comparison.pre_earnings.avg_days_held:.1f} days

### Post-Earnings Trades
- **Total Trades**: {comparison.post_earnings.total_trades}
- **Winners**: {comparison.post_earnings.winners} ({comparison.post_earnings.win_rate:.1f}%)
- **Losers**: {comparison.post_earnings.losers}
- **Avg Winner**: {comparison.post_earnings.avg_winner_pct:.2f}%
- **Avg Loser**: {comparison.post_earnings.avg_loser_pct:.2f}%
- **Best Trade**: {comparison.post_earnings.best_trade_pct:.2f}%
- **Worst Trade**: {comparison.post_earnings.worst_trade_pct:.2f}%
- **Avg Days Held**: {comparison.post_earnings.avg_days_held:.1f} days

---

## ⚠️ Important Notes

1. **Past Performance ≠ Future Results**: These results are based on historical simulation and do not guarantee future performance.

2. **Data Quality**: Results depend on the quality and completeness of historical options data and earnings dates.

3. **Simulation Limitations**:
   - Exit cost estimates are approximations
   - Does not account for slippage, commissions, or liquidity issues
   - Assumes positions can be entered/exited at calculated prices

4. **Sample Size**: {_assess_sample_size(comparison)}

5. **Market Regimes**: These results may not hold across all market conditions (bull, bear, high vol, low vol).

---

## 📚 Methodology

### Backtest Setup
- **Exit Rules**:
  - Profit Target: 50% of max profit
  - Stop Loss: 100% of max loss
  - Time Exit: Close at 21 DTE
  - Earnings Exit: Close 3 days before earnings

### Classification
- **Pre-Earnings**: Earnings date falls 0-7 days after expiration
- **Post-Earnings**: Earnings date falls >7 days after expiration or before entry
- **No-Earnings**: No earnings data available for ticker

### Performance Metrics
- **Win Rate**: % of trades with positive P&L
- **Avg Return**: Average return as % of max loss
- **Sharpe Ratio**: Risk-adjusted return (annualized, assumes ~10 trades/year)
- **Sortino Ratio**: Like Sharpe but uses downside deviation only
- **Max Drawdown**: Largest peak-to-trough decline in cumulative P&L
- **Profit Factor**: Gross profit / Gross loss

---

**Report End**

*For questions or issues with this report, review the backtest methodology and ensure data quality.*
"""

    return report


def _format_metrics_table(metrics: PerformanceMetrics) -> str:
    """Format performance metrics as a markdown table."""
    return f"""
| Metric | Value |
|--------|-------|
| **Total Trades** | {metrics.total_trades} |
| **Win Rate** | {metrics.win_rate:.1f}% ({metrics.winners}W / {metrics.losers}L) |
| **Avg Return** | {metrics.avg_return_pct:.2f}% |
| **Avg Winner** | {metrics.avg_winner_pct:.2f}% |
| **Avg Loser** | {metrics.avg_loser_pct:.2f}% |
| **Total P&L** | ${metrics.total_pnl:.2f} |
| **Sharpe Ratio** | {metrics.sharpe_ratio:.2f} |
| **Sortino Ratio** | {metrics.sortino_ratio:.2f} |
| **Max Drawdown** | {metrics.max_drawdown_pct:.1f}% |
| **Profit Factor** | {metrics.profit_factor:.2f} |
| **Best Trade** | {metrics.best_trade_pct:.2f}% |
| **Worst Trade** | {metrics.worst_trade_pct:.2f}% |
| **Avg Days Held** | {metrics.avg_days_held:.1f} days |
"""


def _interpret_p_value(p_value: float, is_significant: bool) -> str:
    """Interpret the p-value in plain language."""
    if is_significant:
        return (
            f"With p={p_value:.4f} < 0.05, we have strong evidence that the difference "
            f"in returns between pre-earnings and post-earnings setups is NOT due to random chance. "
            f"The observed difference is statistically significant."
        )
    else:
        return (
            f"With p={p_value:.4f} ≥ 0.05, we do NOT have sufficient evidence to conclude "
            f"that the difference is real. The observed difference could be due to random variation. "
            f"Either there is no real difference, or we need more data to detect it."
        )


def _analyze_exit_reasons(results: List[BacktestResult]) -> str:
    """Analyze and format exit reason statistics."""
    exit_counts = {}
    for result in results:
        reason = result.exit_reason
        if reason not in exit_counts:
            exit_counts[reason] = 0
        exit_counts[reason] += 1

    total = len(results)
    lines = ["| Exit Reason | Count | Percentage |", "|-------------|-------|------------|"]

    for reason, count in sorted(exit_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / total * 100) if total > 0 else 0
        lines.append(f"| {reason.replace('_', ' ').title()} | {count} | {pct:.1f}% |")

    return "\n".join(lines)


def _generate_actionable_recommendations(comparison: EarningsComparison) -> str:
    """Generate specific actionable recommendations based on results."""
    recommendations = []

    if comparison.is_significant and comparison.avg_return_diff > 0:
        recommendations.append(
            "1. ✅ **AVOID PRE-EARNINGS SETUPS**: The data clearly shows post-earnings setups "
            "outperform. Filter out any iron condors that expire 0-7 days before earnings."
        )
        recommendations.append(
            "2. 📅 **FETCH EARNINGS CALENDAR**: Always use `fetch_earnings_calendar.py` before "
            "screening to get earnings dates."
        )
        recommendations.append(
            "3. ⚠️ **WATCH FOR EARNINGS FLAGS**: In the GUI, avoid any setups marked with "
            "⚠️ Earnings warning."
        )

    if comparison.post_earnings.sharpe_ratio > 1.5:
        recommendations.append(
            f"4. 🎯 **FOCUS ON POST-EARNINGS**: With a Sharpe ratio of {comparison.post_earnings.sharpe_ratio:.2f}, "
            "post-earnings setups show excellent risk-adjusted returns."
        )

    if comparison.pre_earnings.max_drawdown_pct > comparison.post_earnings.max_drawdown_pct * 1.5:
        recommendations.append(
            f"5. 📉 **DRAWDOWN RISK**: Pre-earnings setups have {comparison.pre_earnings.max_drawdown_pct:.1f}% "
            f"max drawdown vs {comparison.post_earnings.max_drawdown_pct:.1f}% for post-earnings. "
            "This is another reason to avoid pre-earnings exposure."
        )

    if comparison.pre_earnings.total_trades < 30 or comparison.post_earnings.total_trades < 30:
        recommendations.append(
            "⚠️ **COLLECT MORE DATA**: Sample size is small. Continue paper trading and collecting "
            "data to validate these findings with higher confidence."
        )

    if not recommendations:
        recommendations.append(
            "➖ **INSUFFICIENT EVIDENCE**: Not enough data or no clear edge detected. "
            "Continue collecting data and re-run this analysis with a larger sample size."
        )

    return "\n\n".join(recommendations)


def _assess_sample_size(comparison: EarningsComparison) -> str:
    """Assess whether sample size is sufficient for reliable conclusions."""
    pre_count = comparison.pre_earnings.total_trades
    post_count = comparison.post_earnings.total_trades

    if pre_count >= 50 and post_count >= 50:
        return "✅ **GOOD** - Both groups have ≥50 trades. Results are likely reliable."
    elif pre_count >= 30 and post_count >= 30:
        return "⚠️ **MODERATE** - Both groups have 30-49 trades. Results are directionally useful but collect more data for confidence."
    elif pre_count >= 10 and post_count >= 10:
        return "⚠️ **LOW** - Both groups have 10-29 trades. Treat results as preliminary. More data needed."
    else:
        return "❌ **INSUFFICIENT** - At least one group has <10 trades. Results are unreliable. Collect more data."
