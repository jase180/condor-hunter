#!/usr/bin/env python3
"""
Run earnings edge validation backtest.

This script demonstrates the backtesting framework by:
1. Generating simulated historical iron condor trades
2. Simulating price paths and P&L outcomes
3. Comparing pre-earnings vs post-earnings performance
4. Generating a comprehensive statistical report

USAGE:
    python3 run_earnings_edge_backtest.py --trades 100
    python3 run_earnings_edge_backtest.py --trades 200 --output MY_REPORT.md

NOTE: This is a SIMULATION using synthetic data to demonstrate the framework.
For real validation, you need historical options data (see fetch_tradier.py historical API).
"""

import argparse
import random
from datetime import date, timedelta
from typing import List, Tuple
import logging

from condor_screener.models.option import Option
from condor_screener.models.iron_condor import IronCondor
from condor_screener.backtest.simulator import simulate_iron_condor, ExitRule, BacktestResult
from condor_screener.backtest.earnings_analyzer import EarningsEdgeAnalyzer
from condor_screener.backtest.report import generate_earnings_edge_report

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_simulated_iron_condor(
    spot_price: float,
    entry_date: date,
    dte: int,
    has_earnings: bool
) -> Tuple[IronCondor, str | None]:
    """Generate a simulated iron condor for backtesting.

    Args:
        spot_price: Current underlying price
        entry_date: Date position was entered
        dte: Days to expiration
        has_earnings: Whether this setup has earnings risk

    Returns:
        Tuple of (IronCondor, earnings_date or None)
    """
    expiration = entry_date + timedelta(days=dte)

    # Generate strikes around spot (15 delta ~= 8-10% OTM for 35 DTE)
    otm_pct = 0.08 + random.uniform(-0.02, 0.02)  # 6-10% OTM

    short_put_strike = round(spot_price * (1 - otm_pct))
    long_put_strike = short_put_strike - 5  # $5 wing

    short_call_strike = round(spot_price * (1 + otm_pct))
    long_call_strike = short_call_strike + 5  # $5 wing

    # Estimate credit (simplified - typically 20-30% of width)
    wing_width = 5.0
    credit = random.uniform(0.20, 0.35) * wing_width

    # Create options
    long_put = Option(
        ticker='SPY',
        strike=float(long_put_strike),
        expiration=expiration,
        option_type='put',
        bid=0.5,
        ask=0.6,
        last=0.55,
        volume=100,
        open_interest=1000,
        implied_vol=0.15,
        delta=-0.05,
        gamma=0.01,
        theta=-0.5,
        vega=1.0,
    )

    short_put = Option(
        ticker='SPY',
        strike=float(short_put_strike),
        expiration=expiration,
        option_type='put',
        bid=credit / 2 - 0.1,
        ask=credit / 2 + 0.1,
        last=credit / 2,
        volume=500,
        open_interest=5000,
        implied_vol=0.16,
        delta=-0.15,
        gamma=0.02,
        theta=-1.0,
        vega=2.0,
    )

    short_call = Option(
        ticker='SPY',
        strike=float(short_call_strike),
        expiration=expiration,
        option_type='call',
        bid=credit / 2 - 0.1,
        ask=credit / 2 + 0.1,
        last=credit / 2,
        volume=500,
        open_interest=5000,
        implied_vol=0.16,
        delta=0.15,
        gamma=0.02,
        theta=-1.0,
        vega=2.0,
    )

    long_call = Option(
        ticker='SPY',
        strike=float(long_call_strike),
        expiration=expiration,
        option_type='call',
        bid=0.5,
        ask=0.6,
        last=0.55,
        volume=100,
        open_interest=1000,
        implied_vol=0.15,
        delta=0.05,
        gamma=0.01,
        theta=-0.5,
        vega=1.0,
    )

    iron_condor = IronCondor(
        ticker='SPY',
        expiration=expiration,
        long_put=long_put,
        short_put=short_put,
        short_call=short_call,
        long_call=long_call,
    )

    # Generate earnings date if applicable
    earnings_date = None
    if has_earnings:
        # Pre-earnings: earnings 3-5 days after expiration
        days_after_exp = random.randint(3, 5)
        earnings_dt = expiration + timedelta(days=days_after_exp)
        earnings_date = earnings_dt.isoformat()

    return iron_condor, earnings_date


def generate_price_path(
    spot_price: float,
    start_date: date,
    end_date: date,
    drift: float = 0.0,
    volatility: float = 0.15
) -> List[Tuple[date, float]]:
    """Generate simulated price path using geometric Brownian motion.

    Args:
        spot_price: Starting price
        start_date: Start date
        end_date: End date
        drift: Annual drift (default 0% for neutral)
        volatility: Annual volatility (default 15%)

    Returns:
        List of (date, price) tuples
    """
    days = (end_date - start_date).days
    if days <= 0:
        return [(start_date, spot_price)]

    path = []
    current_price = spot_price
    current_date = start_date

    # Daily parameters
    daily_drift = drift / 252
    daily_vol = volatility / math.sqrt(252)

    for i in range(days + 1):
        path.append((current_date, current_price))

        # Random walk
        random_shock = random.gauss(0, 1)
        daily_return = daily_drift + daily_vol * random_shock
        current_price *= (1 + daily_return)

        current_date += timedelta(days=1)

    return path


def run_simulated_backtest(num_trades: int = 100) -> List[BacktestResult]:
    """Run simulated backtest with specified number of trades.

    Args:
        num_trades: Number of trades to simulate

    Returns:
        List of BacktestResult objects
    """
    logger.info(f"Generating {num_trades} simulated iron condor trades...")

    results = []
    base_spot = 560.0  # SPY starting price
    current_date = date(2024, 1, 1)

    # Generate mix of pre-earnings and post-earnings setups
    for i in range(num_trades):
        # Random DTE between 30-45
        dte = random.randint(30, 45)

        # 40% pre-earnings, 60% post-earnings (realistic distribution)
        has_earnings = random.random() < 0.4

        # Generate iron condor
        iron_condor, earnings_date = generate_simulated_iron_condor(
            spot_price=base_spot,
            entry_date=current_date,
            dte=dte,
            has_earnings=has_earnings
        )

        # Generate price path
        # Pre-earnings setups have slightly higher volatility (simulate IV crush risk)
        vol = 0.18 if has_earnings else 0.15
        price_path = generate_price_path(
            spot_price=base_spot,
            start_date=current_date,
            end_date=iron_condor.expiration,
            drift=0.0,
            volatility=vol
        )

        # Simulate trade
        exit_rule = ExitRule(
            profit_target_pct=0.50,
            stop_loss_pct=1.0,
            min_dte_to_close=21,
            close_before_earnings_days=3
        )

        result = simulate_iron_condor(
            iron_condor=iron_condor,
            entry_date=current_date,
            exit_rule=exit_rule,
            price_path=price_path,
            earnings_date=earnings_date
        )

        results.append(result)

        # Move forward in time for next trade
        current_date += timedelta(days=random.randint(7, 14))

        if (i + 1) % 20 == 0:
            logger.info(f"  Simulated {i + 1}/{num_trades} trades...")

    logger.info(f"✅ Generated {len(results)} backtest results")
    return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Run earnings edge validation backtest (simulated data)'
    )
    parser.add_argument(
        '--trades',
        type=int,
        default=100,
        help='Number of trades to simulate (default: 100)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='EARNINGS_EDGE_REPORT.md',
        help='Output report path (default: EARNINGS_EDGE_REPORT.md)'
    )

    args = parser.parse_args()

    print("=" * 80)
    print("  EARNINGS EDGE VALIDATION BACKTEST")
    print("=" * 80)
    print()
    print(f"Simulating {args.trades} iron condor trades...")
    print("This demonstrates the backtesting framework with synthetic data.")
    print()
    print("⚠️  NOTE: This uses SIMULATED data. For real validation, use historical")
    print("   options data from Tradier historical API or your broker.")
    print()
    print("=" * 80)
    print()

    # Run simulation
    results = run_simulated_backtest(num_trades=args.trades)

    # Analyze earnings edge
    logger.info("Analyzing earnings edge...")
    analyzer = EarningsEdgeAnalyzer(results)
    comparison = analyzer.analyze()

    # Print summary to console
    print()
    print("=" * 80)
    print("  RESULTS SUMMARY")
    print("=" * 80)
    print()
    print(f"Total Trades: {len(results)}")
    print(f"Pre-Earnings Trades: {comparison.pre_earnings.total_trades}")
    print(f"Post-Earnings Trades: {comparison.post_earnings.total_trades}")
    print()
    print("PRE-EARNINGS PERFORMANCE:")
    print(f"  Win Rate: {comparison.pre_earnings.win_rate:.1f}%")
    print(f"  Avg Return: {comparison.pre_earnings.avg_return_pct:.2f}%")
    print(f"  Sharpe Ratio: {comparison.pre_earnings.sharpe_ratio:.2f}")
    print()
    print("POST-EARNINGS PERFORMANCE:")
    print(f"  Win Rate: {comparison.post_earnings.win_rate:.1f}%")
    print(f"  Avg Return: {comparison.post_earnings.avg_return_pct:.2f}%")
    print(f"  Sharpe Ratio: {comparison.post_earnings.sharpe_ratio:.2f}")
    print()
    print("DIFFERENCES:")
    print(f"  Win Rate: {comparison.win_rate_diff:+.1f}%")
    print(f"  Avg Return: {comparison.avg_return_diff:+.2f}%")
    print(f"  Sharpe Ratio: {comparison.sharpe_diff:+.2f}")
    print()
    print(f"Statistical Significance: {'✅ YES' if comparison.is_significant else '❌ NO'} (p={comparison.p_value:.4f})")
    print()
    print("RECOMMENDATION:")
    print(f"  {comparison.recommendation}")
    print()
    print("=" * 80)
    print()

    # Generate full report
    logger.info(f"Generating detailed report: {args.output}")
    generate_earnings_edge_report(comparison, results, args.output)

    print(f"✅ Full report saved to: {args.output}")
    print()
    print("Next steps:")
    print("1. Review the detailed report")
    print("2. If using real data, run with historical options CSV files")
    print("3. Validate findings with paper trading")
    print()


if __name__ == '__main__':
    import math  # Import here for generate_price_path
    main()
