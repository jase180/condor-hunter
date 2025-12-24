"""Console output formatter for iron condor screening results."""

from typing import List

from ..models.analytics import Analytics


def print_header(ticker: str, spot_price: float):
    """Print screening session header.

    Args:
        ticker: Ticker symbol
        spot_price: Current underlying price
    """
    print("\n" + "=" * 80)
    print(f"  IRON CONDOR SCREENER - {ticker}")
    print(f"  Spot Price: ${spot_price:.2f}")
    print("=" * 80)


def print_summary(
    total_candidates: int,
    filtered_count: int,
    top_n: int,
):
    """Print summary of screening results.

    Args:
        total_candidates: Total number of candidates generated
        filtered_count: Number after applying filters
        top_n: Number of top results to display
    """
    print(f"\nSummary:")
    print(f"  Total candidates generated: {total_candidates}")
    print(f"  After filtering: {filtered_count}")
    print(f"  Displaying top {top_n} results\n")


def print_ranked_results(ranked_analytics: List[Analytics]):
    """Print ranked iron condor results to console.

    Args:
        ranked_analytics: List of Analytics objects sorted by score

    Output format:
        Compact table with key metrics for each candidate
    """
    if not ranked_analytics:
        print("No candidates found matching criteria.")
        return

    print("\nTop Iron Condor Candidates:")
    print("-" * 120)

    # Header
    header = (
        f"{'Rank':>4} {'Exp':^10} {'Put Strikes':^15} {'Call Strikes':^15} "
        f"{'Credit':>7} {'Max Loss':>8} {'ROR':>6} {'IVR':>5} "
        f"{'Dist%':>6} {'Liq':>5} {'Score':>6}"
    )
    print(header)
    print("-" * 120)

    # Results
    for rank, analytics in enumerate(ranked_analytics, start=1):
        ic = analytics.iron_condor

        # Format strikes as "long/short"
        put_strikes = f"{ic.long_put.strike:.0f}/{ic.short_put.strike:.0f}"
        call_strikes = f"{ic.short_call.strike:.0f}/{ic.long_call.strike:.0f}"

        # Format metrics
        exp_str = ic.expiration.strftime('%Y-%m-%d')
        credit = f"${ic.net_credit:.2f}"
        max_loss = f"${ic.max_loss:.0f}"
        ror = f"{ic.return_on_risk:.1f}%"
        ivr = f"{analytics.iv_rank:.0f}"
        dist = f"{analytics.avg_distance_pct:.1f}%"
        liq = f"{analytics.liquidity_score:.2f}"
        score = f"{analytics.composite_score:.3f}" if analytics.composite_score else "N/A"

        # Print row
        row = (
            f"{rank:>4} {exp_str:^10} {put_strikes:^15} {call_strikes:^15} "
            f"{credit:>7} {max_loss:>8} {ror:>6} {ivr:>5} "
            f"{dist:>6} {liq:>5} {score:>6}"
        )
        print(row)

    print("-" * 120)


def print_detailed_analytics(analytics: Analytics, rank: int = 1):
    """Print detailed analytics for a single iron condor.

    Args:
        analytics: Analytics object to display
        rank: Rank number (for display purposes)
    """
    ic = analytics.iron_condor

    print(f"\n{'=' * 80}")
    print(f"Rank #{rank}: {ic.ticker} Iron Condor")
    print(f"{'=' * 80}")

    # Basic info
    print(f"\nExpiration: {ic.expiration.strftime('%Y-%m-%d')} ({ic.short_put.dte} DTE)")
    print(f"Spot Price: ${analytics.spot_price:.2f}")

    # Structure
    print(f"\nStructure:")
    print(f"  Put Side:  Buy {ic.long_put.strike:.0f} / Sell {ic.short_put.strike:.0f}")
    print(f"             (Δ={ic.short_put.delta:.3f}, IV={ic.short_put.implied_vol:.2%})")
    print(f"  Call Side: Sell {ic.short_call.strike:.0f} / Buy {ic.long_call.strike:.0f}")
    print(f"             (Δ={ic.short_call.delta:.3f}, IV={ic.short_call.implied_vol:.2%})")

    # Risk/Reward
    print(f"\nRisk/Reward:")
    print(f"  Net Credit:       ${ic.net_credit:.2f}")
    print(f"  Max Profit:       ${ic.max_profit:.2f}")
    print(f"  Max Loss:         ${ic.max_loss:.0f}")
    print(f"  Return on Risk:   {ic.return_on_risk:.1f}%")
    print(f"  Breakevens:       ${ic.put_side_breakeven:.2f} / ${ic.call_side_breakeven:.2f}")

    # Distance from spot
    print(f"\nPosition Metrics:")
    print(f"  Put strike distance:  {analytics.put_distance_pct:.1f}% (${analytics.put_distance_dollars:.2f})")
    print(f"  Call strike distance: {analytics.call_distance_pct:.1f}% (${analytics.call_distance_dollars:.2f})")
    print(f"  Expected move:        ${analytics.expected_move_straddle:.2f}")
    print(f"  Within exp. move?     {'⚠ YES (risky)' if analytics.within_expected_move else '✓ NO (safe)'}")

    # Volatility
    print(f"\nVolatility Context:")
    print(f"  IV Rank:              {analytics.iv_rank:.1f}")
    print(f"  IV Percentile:        {analytics.iv_percentile:.1f}")
    print(f"  Realized Vol (20d):   {analytics.realized_vol_20d:.2%}")
    print(f"  IV/RV Ratio:          {analytics.iv_to_rv_ratio:.2f}")
    print(f"  Pre-earnings?         {'YES' if analytics.is_pre_earnings else 'NO'}")

    # Liquidity
    print(f"\nLiquidity:")
    print(f"  Liquidity Score:      {analytics.liquidity_score:.2f}")
    print(f"  Short Put:  OI={ic.short_put.open_interest:,}, Vol={ic.short_put.volume:,}, Spread={ic.short_put.bid_ask_spread_pct:.1%}")
    print(f"  Short Call: OI={ic.short_call.open_interest:,}, Vol={ic.short_call.volume:,}, Spread={ic.short_call.bid_ask_spread_pct:.1%}")

    # Score
    if analytics.composite_score is not None:
        print(f"\nComposite Score: {analytics.composite_score:.3f}")

    print(f"{'=' * 80}\n")


def print_comparison_table(ranked_analytics: List[Analytics], top_n: int = 5):
    """Print side-by-side comparison of top candidates.

    Args:
        ranked_analytics: Ranked list of Analytics objects
        top_n: Number of candidates to compare
    """
    candidates = ranked_analytics[:top_n]

    if not candidates:
        print("No candidates to compare.")
        return

    print("\n" + "=" * 120)
    print(f"Top {len(candidates)} Candidates - Detailed Comparison")
    print("=" * 120)

    # Metrics to compare
    metrics = [
        ("Rank", lambda i, a: f"#{i+1}"),
        ("Expiration", lambda i, a: a.iron_condor.expiration.strftime('%m/%d')),
        ("DTE", lambda i, a: f"{a.iron_condor.short_put.dte}"),
        ("Credit", lambda i, a: f"${a.iron_condor.net_credit:.2f}"),
        ("Max Loss", lambda i, a: f"${a.iron_condor.max_loss:.0f}"),
        ("ROR", lambda i, a: f"{a.iron_condor.return_on_risk:.1f}%"),
        ("IVR", lambda i, a: f"{a.iv_rank:.0f}"),
        ("IV/RV", lambda i, a: f"{a.iv_to_rv_ratio:.2f}"),
        ("Avg Dist %", lambda i, a: f"{a.avg_distance_pct:.1f}%"),
        ("Liquidity", lambda i, a: f"{a.liquidity_score:.2f}"),
        ("Score", lambda i, a: f"{a.composite_score:.3f}" if a.composite_score else "N/A"),
    ]

    for metric_name, metric_func in metrics:
        row = f"{metric_name:12}"
        for i, analytics in enumerate(candidates):
            value = metric_func(i, analytics)
            row += f" | {value:^12}"
        print(row)

    print("=" * 120)
