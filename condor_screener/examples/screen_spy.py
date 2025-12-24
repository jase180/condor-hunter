#!/usr/bin/env python3
"""Example: Screen SPY for iron condor opportunities.

This script demonstrates the complete screening pipeline:
1. Load option chain from CSV
2. Apply hard filters
3. Generate iron condor candidates
4. Compute analytics for each candidate
5. Score and rank
6. Display results
"""

import sys
from pathlib import Path

# Add parent directory to path to import condor_screener modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import yaml
from condor_screener.data.loaders import load_options_from_csv
from condor_screener.data.validators import FilterConfig, filter_options
from condor_screener.builders.condor_builder import StrategyConfig, generate_iron_condors
from condor_screener.analytics.analyzer import analyze_iron_condor
from condor_screener.analytics.volatility import calculate_realized_volatility
from condor_screener.scoring.scorer import ScoringConfig, rank_analytics
from condor_screener.output.console import (
    print_header,
    print_summary,
    print_ranked_results,
    print_detailed_analytics,
)


def main():
    """Run iron condor screening on SPY example data."""

    # -------------------------------------------------------------------------
    # 1. Configuration
    # -------------------------------------------------------------------------
    print("Loading configuration...")

    # Load configs (or use defaults)
    config_dir = Path(__file__).parent.parent / "config"

    with open(config_dir / "default_params.yaml") as f:
        params = yaml.safe_load(f)

    with open(config_dir / "scoring_weights.yaml") as f:
        scoring_params = yaml.safe_load(f)

    strategy_config = StrategyConfig.from_dict(params['strategy'])
    filter_config = FilterConfig.from_dict(params['filters'])
    scoring_config = ScoringConfig.from_dict(scoring_params)

    # -------------------------------------------------------------------------
    # 2. Load Data
    # -------------------------------------------------------------------------
    print("Loading option chain from CSV...")

    csv_path = Path(__file__).parent.parent / "data" / "example_chain.csv"
    options = load_options_from_csv(csv_path)

    print(f"  Loaded {len(options)} options")

    # Dummy market data (in production, fetch from API)
    spot_price = 570.0
    historical_ivs = [0.15, 0.18, 0.20, 0.22, 0.25, 0.28, 0.30, 0.26, 0.24, 0.22]  # Dummy
    close_prices = [560, 562, 565, 568, 570, 571, 569, 568, 570, 572]  # Dummy
    earnings_date = None  # No earnings for this example

    # Calculate realized volatility
    realized_vol = calculate_realized_volatility(close_prices=close_prices)
    print(f"  Realized Vol (20d): {realized_vol:.2%}")

    # -------------------------------------------------------------------------
    # 3. Apply Hard Filters
    # -------------------------------------------------------------------------
    print("\nApplying hard filters...")

    # Calculate IV rank/percentile (using dummy historical IVs)
    current_iv = sum(opt.implied_vol for opt in options) / len(options)
    iv_rank = ((current_iv - min(historical_ivs)) / (max(historical_ivs) - min(historical_ivs))) * 100
    iv_percentile = (sum(1 for iv in historical_ivs if iv < current_iv) / len(historical_ivs)) * 100

    print(f"  Current IV: {current_iv:.2%}")
    print(f"  IV Rank: {iv_rank:.1f}")
    print(f"  IV Percentile: {iv_percentile:.1f}")

    filtered_options = filter_options(
        options,
        iv_rank=iv_rank,
        iv_percentile=iv_percentile,
        config=filter_config,
    )

    if not filtered_options:
        print("\n❌ No options passed filters. Exiting.")
        return

    # -------------------------------------------------------------------------
    # 4. Generate Iron Condor Candidates
    # -------------------------------------------------------------------------
    print("\nGenerating iron condor candidates...")

    candidates = list(generate_iron_condors(filtered_options, strategy_config))
    print(f"  Generated {len(candidates)} candidates")

    if not candidates:
        print("\n❌ No valid iron condors found. Try adjusting strategy parameters.")
        return

    # -------------------------------------------------------------------------
    # 5. Compute Analytics
    # -------------------------------------------------------------------------
    print("\nComputing analytics for each candidate...")

    analytics_list = []
    for ic in candidates:
        analytics = analyze_iron_condor(
            ic,
            spot_price=spot_price,
            historical_ivs=historical_ivs,
            realized_vol_20d=realized_vol,
            earnings_date=earnings_date,
            expected_move_method=params['expected_move']['method'],
        )
        analytics_list.append(analytics)

    print(f"  Computed analytics for {len(analytics_list)} candidates")

    # -------------------------------------------------------------------------
    # 6. Score and Rank
    # -------------------------------------------------------------------------
    print("\nScoring and ranking candidates...")

    ranked = rank_analytics(
        analytics_list,
        config=scoring_config,
        top_n=params['ranking']['top_n'],
    )

    print(f"  Ranked top {len(ranked)} candidates")

    # -------------------------------------------------------------------------
    # 7. Display Results
    # -------------------------------------------------------------------------
    print_header("SPY", spot_price)
    print_summary(
        total_candidates=len(candidates),
        filtered_count=len(analytics_list),
        top_n=len(ranked),
    )
    print_ranked_results(ranked)

    # Show detailed view of top candidate
    if ranked:
        print("\n" + "=" * 80)
        print("DETAILED VIEW: Top Candidate")
        print("=" * 80)
        print_detailed_analytics(ranked[0], rank=1)

    # -------------------------------------------------------------------------
    # 8. Summary Statistics
    # -------------------------------------------------------------------------
    print("\nScreening Summary:")
    print(f"  Total candidates:     {len(candidates)}")
    print(f"  Top score:            {ranked[0].composite_score:.3f}" if ranked else "  No candidates")
    print(f"  Best ROR:             {max(a.iron_condor.return_on_risk for a in analytics_list):.1f}%" if analytics_list else "N/A")
    print(f"  Best distance:        {max(a.avg_distance_pct for a in analytics_list):.1f}%" if analytics_list else "N/A")
    print(f"  Avg liquidity score:  {sum(a.liquidity_score for a in analytics_list) / len(analytics_list):.2f}" if analytics_list else "N/A")

    print("\n✅ Screening complete!\n")


if __name__ == "__main__":
    main()
