#!/usr/bin/env python3
"""Screen calendar spreads from options CSV data.

Usage:
    python3 screen_calendars.py data/SPY_options.csv
    python3 screen_calendars.py data/SPY_options.csv --call
    python3 screen_calendars.py data/SPY_options.csv --put
    python3 screen_calendars.py data/SPY_options.csv --both
"""

import argparse
import sys
from condor_screener.data.loaders import load_options_from_csv
from condor_screener.builder.calendar_spreads import (
    generate_calendar_spreads,
    CalendarConfig
)
from condor_screener.analytics.calendar_analytics import (
    analyze_calendar_spread,
    rank_calendar_analytics
)


def main():
    parser = argparse.ArgumentParser(
        description='Screen calendar spreads from options data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Screen call calendars
  python3 screen_calendars.py data/SPY_options.csv --call

  # Screen put calendars
  python3 screen_calendars.py data/SPY_options.csv --put

  # Screen both calls and puts
  python3 screen_calendars.py data/SPY_options.csv --both

  # Custom DTE ranges
  python3 screen_calendars.py data/SPY_options.csv \\
      --min-short-dte 25 --max-short-dte 35 \\
      --min-long-dte 45 --min-gap 15
        """
    )

    parser.add_argument('csv_file', help='Path to options CSV file')
    parser.add_argument('--call', action='store_true', help='Screen call calendars (default)')
    parser.add_argument('--put', action='store_true', help='Screen put calendars')
    parser.add_argument('--both', action='store_true', help='Screen both calls and puts')
    parser.add_argument('--min-short-dte', type=int, default=20,
                        help='Min DTE for short leg (default: 20)')
    parser.add_argument('--max-short-dte', type=int, default=35,
                        help='Max DTE for short leg (default: 35)')
    parser.add_argument('--min-long-dte', type=int, default=40,
                        help='Min DTE for long leg (default: 40)')
    parser.add_argument('--min-gap', type=int, default=20,
                        help='Min days between expirations (default: 20)')
    parser.add_argument('--max-gap', type=int, default=45,
                        help='Max days between expirations (default: 45)')
    parser.add_argument('--target-delta', type=float, default=0.50,
                        help='Target delta (default: 0.50 for ATM)')
    parser.add_argument('--max-results', type=int, default=10,
                        help='Max results to display (default: 10)')

    args = parser.parse_args()

    # Determine option type
    if args.both:
        option_type = 'both'
    elif args.put:
        option_type = 'put'
    else:
        option_type = 'call'  # default

    # Load options
    print(f"📊 Loading options from {args.csv_file}...")
    try:
        options = load_options_from_csv(args.csv_file)
    except FileNotFoundError:
        print(f"❌ Error: File not found: {args.csv_file}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        sys.exit(1)

    if not options:
        print("❌ No options loaded")
        sys.exit(1)

    ticker = options[0].ticker
    print(f"✅ Loaded {len(options)} options for {ticker}")

    # Get spot price (use ATM strike as proxy)
    strikes = sorted(set(o.strike for o in options))
    mid_idx = len(strikes) // 2
    spot_price = strikes[mid_idx]
    print(f"💰 Estimated spot price: ${spot_price:.2f}")

    # Configure calendar spread generation
    config = CalendarConfig(
        min_short_dte=args.min_short_dte,
        max_short_dte=args.max_short_dte,
        min_long_dte=args.min_long_dte,
        min_dte_gap=args.min_gap,
        max_dte_gap=args.max_gap,
        target_delta=args.target_delta,
        delta_tolerance=0.10,
        option_type=option_type
    )

    # Generate calendar spreads
    print(f"\n🎯 Generating {option_type} calendar spreads...")
    calendars = list(generate_calendar_spreads(options, config))

    if not calendars:
        print("❌ No calendar spreads found matching criteria")
        print("\nTry:")
        print("  - Wider DTE ranges (--min-short-dte, --max-short-dte, --min-long-dte)")
        print("  - Smaller DTE gap (--min-gap)")
        print("  - Different delta target (--target-delta)")
        sys.exit(1)

    print(f"✅ Generated {len(calendars)} calendar spread candidates")

    # Analyze calendars
    print("⏳ Analyzing spreads...")
    analytics = [
        analyze_calendar_spread(cal, spot_price)
        for cal in calendars
    ]

    # Rank
    ranked = rank_calendar_analytics(analytics, max_results=args.max_results)

    # Display results
    print("\n" + "="*100)
    print(f"  CALENDAR SPREAD SCREENER - {ticker}")
    print(f"  Type: {option_type.upper()}  |  Spot: ${spot_price:.2f}")
    print("="*100)

    print("\nTop Calendar Spread Candidates:")
    print(f"{'Rank':<6}{'Score':<8}{'Strike':<10}{'Short DTE':<12}{'Long DTE':<12}"
          f"{'Debit':<10}{'RoR':<10}{'Theta Δ':<10}{'Distance':<10}")
    print("-"*100)

    for i, analytics in enumerate(ranked, 1):
        cal = analytics.calendar
        print(f"{i:<6}{analytics.composite_score:<8.3f}"
              f"${cal.short_leg.strike:<9.2f}{cal.short_leg.dte:<12}"
              f"{cal.long_leg.dte:<12}${cal.net_debit:<9.2f}"
              f"{analytics.return_on_risk:<10.1%}{analytics.theta_differential:<10.2f}"
              f"{analytics.distance_to_strike_pct:<10.1%}")

    print("\n" + "="*100)

    # Detailed view of top candidate
    if ranked:
        print("\n📋 Detailed Analysis - Top Candidate:")
        print("-"*100)
        top = ranked[0]
        cal = top.calendar

        print(f"\n  {cal}")
        print(f"\n  Composite Score:      {top.composite_score:.3f}")
        print(f"  Return on Risk:       {top.return_on_risk:.1%}")
        print(f"  Probability of Profit: {top.probability_of_profit:.1%}")
        print(f"\n  Net Debit:            ${cal.net_debit:.2f}")
        print(f"  Max Profit (est):     ${cal.max_profit_estimate:.2f}")
        print(f"  Max Loss:             ${cal.max_loss:.2f}")
        print(f"\n  Theta Differential:   {top.theta_differential:.2f}")
        print(f"  Vega Exposure:        {top.vega_exposure:.2f}")
        print(f"  Distance to Strike:   {top.distance_to_strike_pct:.1%}")
        print(f"\n  Breakeven Range:      ${top.breakeven_lower:.2f} - ${top.breakeven_upper:.2f}")

        print("\n  Short Leg:")
        print(f"    {cal.short_leg.option_type.upper()} ${cal.short_leg.strike} exp {cal.short_leg.expiration}")
        print(f"    Bid: ${cal.short_leg.bid:.2f}  Ask: ${cal.short_leg.ask:.2f}")
        print(f"    Delta: {cal.short_leg.delta:.3f}  Theta: {cal.short_leg.theta:.2f}  Vega: {cal.short_leg.vega:.2f}")

        print("\n  Long Leg:")
        print(f"    {cal.long_leg.option_type.upper()} ${cal.long_leg.strike} exp {cal.long_leg.expiration}")
        print(f"    Bid: ${cal.long_leg.bid:.2f}  Ask: ${cal.long_leg.ask:.2f}")
        print(f"    Delta: {cal.long_leg.delta:.3f}  Theta: {cal.long_leg.theta:.2f}  Vega: {cal.long_leg.vega:.2f}")

        print("\n" + "="*100)

    print("\n💡 Tips:")
    print("  - Calendar spreads profit from time decay and volatility expansion")
    print("  - Best when underlying stays near the strike price")
    print("  - Max profit typically occurs at short leg expiration")
    print("  - Consider closing before short expiration if max profit achieved")


if __name__ == '__main__':
    main()
