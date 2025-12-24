#!/usr/bin/env python3
"""End-to-end integration test for earnings functionality.

This script tests the complete earnings workflow:
1. Create test earnings data
2. Create test options data
3. Load both in the screener
4. Verify earnings detection works
"""

import csv
import sys
from pathlib import Path
from datetime import date, datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from condor_screener.data.loaders import load_options_from_csv, load_earnings_calendar
from condor_screener.data.validators import filter_options, FilterConfig
from condor_screener.builders.condor_builder import generate_iron_condors, StrategyConfig
from condor_screener.analytics.analyzer import analyze_iron_condor
from condor_screener.models.option import Option


def create_test_earnings_csv(output_file: Path):
    """Create a test earnings calendar CSV."""
    print(f"Creating test earnings calendar: {output_file}")

    # Calculate dates
    today = date.today()
    earnings_date = today + timedelta(days=40)

    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['symbol', 'earnings_date', 'days_until_earnings', 'source'])
        writer.writerow(['TEST', earnings_date.strftime('%Y-%m-%d'), '40', 'test'])

    print(f"  ✅ Created earnings calendar with earnings on {earnings_date}")
    return earnings_date


def create_test_options_csv(output_file: Path, earnings_date: date):
    """Create a test options CSV with various expirations."""
    print(f"Creating test options data: {output_file}")

    today = date.today()

    # Create expirations:
    # 1. Safe expiration (20 days before earnings)
    safe_exp = earnings_date - timedelta(days=20)

    # 2. Risky expiration (2 days before earnings)
    risky_exp = earnings_date - timedelta(days=2)

    # 3. Post-earnings expiration
    post_exp = earnings_date + timedelta(days=10)

    expirations = [safe_exp, risky_exp, post_exp]

    options = []
    for exp in expirations:
        dte = (exp - today).days

        # Create a simple iron condor structure at each expiration
        # Underlying at 100
        strikes = [85, 90, 110, 115]

        for strike in strikes:
            # Puts
            options.append({
                'ticker': 'TEST',
                'option_type': 'put',
                'strike': strike,
                'expiration': exp.strftime('%Y-%m-%d'),
                'bid': 1.0 if strike < 100 else 5.0,
                'ask': 1.2 if strike < 100 else 5.5,
                'last': 1.1 if strike < 100 else 5.2,
                'volume': 100,
                'open_interest': 1000,
                'delta': -0.15 if strike == 90 else -0.05,
                'gamma': 0.01,
                'theta': -0.05,
                'vega': 0.1,
                'implied_vol': 0.25,
            })

            # Calls
            options.append({
                'ticker': 'TEST',
                'option_type': 'call',
                'strike': strike,
                'expiration': exp.strftime('%Y-%m-%d'),
                'bid': 5.0 if strike < 100 else 1.0,
                'ask': 5.5 if strike < 100 else 1.2,
                'last': 5.2 if strike < 100 else 1.1,
                'volume': 100,
                'open_interest': 1000,
                'delta': 0.95 if strike < 100 else 0.15,
                'gamma': 0.01,
                'theta': -0.05,
                'vega': 0.1,
                'implied_vol': 0.25,
            })

    # Write CSV
    with open(output_file, 'w', newline='') as f:
        fieldnames = [
            'ticker', 'option_type', 'strike', 'expiration',
            'bid', 'ask', 'last', 'volume', 'open_interest',
            'delta', 'gamma', 'theta', 'vega', 'implied_vol'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(options)

    print(f"  ✅ Created {len(options)} options with 3 expirations:")
    print(f"     - Safe: {safe_exp} ({(safe_exp - today).days} DTE)")
    print(f"     - Risky: {risky_exp} ({(risky_exp - today).days} DTE) ⚠️")
    print(f"     - Post: {post_exp} ({(post_exp - today).days} DTE)")

    return safe_exp, risky_exp, post_exp


def main():
    """Run end-to-end integration test."""
    print("="*80)
    print("EARNINGS INTEGRATION TEST")
    print("="*80)
    print()

    # Setup
    test_dir = Path("test_output")
    test_dir.mkdir(exist_ok=True)

    earnings_file = test_dir / "test_earnings.csv"
    options_file = test_dir / "test_options.csv"

    try:
        # Step 1: Create test data
        print("Step 1: Creating test data...")
        earnings_date = create_test_earnings_csv(earnings_file)
        safe_exp, risky_exp, post_exp = create_test_options_csv(options_file, earnings_date)
        print()

        # Step 2: Load earnings calendar
        print("Step 2: Loading earnings calendar...")
        earnings_map = load_earnings_calendar(earnings_file)
        print(f"  ✅ Loaded earnings for: {list(earnings_map.keys())}")
        assert 'TEST' in earnings_map, "TEST ticker not found in earnings map"
        print(f"  ✅ Earnings date: {earnings_map['TEST']['date']}")
        print()

        # Step 3: Load options
        print("Step 3: Loading options data...")
        options = load_options_from_csv(options_file)
        print(f"  ✅ Loaded {len(options)} options")
        print()

        # Step 4: Generate iron condors
        print("Step 4: Generating iron condor candidates...")
        strategy_config = StrategyConfig(
            min_dte=1,
            max_dte=365,
            min_delta=0.10,
            max_delta=0.20,
            wing_width_put=5.0,
            wing_width_call=5.0,
        )
        candidates = list(generate_iron_condors(options, strategy_config))
        print(f"  ✅ Generated {len(candidates)} iron condor candidates")
        print()

        # Step 5: Analyze with earnings
        print("Step 5: Analyzing candidates with earnings data...")
        spot_price = 100.0
        historical_ivs = [0.20, 0.22, 0.25, 0.23, 0.24]
        realized_vol_20d = 0.20
        earnings_date_str = earnings_map['TEST']['date']

        analytics_list = []
        for ic in candidates:
            analytics = analyze_iron_condor(
                iron_condor=ic,
                spot_price=spot_price,
                historical_ivs=historical_ivs,
                realized_vol_20d=realized_vol_20d,
                earnings_date=earnings_date_str,
                expected_move_method='straddle',
            )
            analytics_list.append(analytics)

        print(f"  ✅ Analyzed {len(analytics_list)} candidates")
        print()

        # Step 6: Verify earnings detection
        print("Step 6: Verifying earnings detection...")

        safe_count = 0
        risky_count = 0
        post_count = 0

        for analytics in analytics_list:
            exp = analytics.iron_condor.expiration
            is_pre = analytics.is_pre_earnings

            # Count by expiration type
            if exp == safe_exp:
                safe_count += 1
                if is_pre:
                    print(f"  ❌ ERROR: Safe expiration {exp} flagged as pre-earnings!")
                    return 1
            elif exp == risky_exp:
                risky_count += 1
                if not is_pre:
                    print(f"  ❌ ERROR: Risky expiration {exp} NOT flagged as pre-earnings!")
                    return 1
            elif exp == post_exp:
                post_count += 1
                if is_pre:
                    print(f"  ❌ ERROR: Post-earnings expiration {exp} flagged as pre-earnings!")
                    return 1

        print(f"  ✅ Safe expirations: {safe_count} candidates (not pre-earnings)")
        print(f"  ✅ Risky expirations: {risky_count} candidates (pre-earnings ⚠️)")
        print(f"  ✅ Post-earnings expirations: {post_count} candidates (not pre-earnings)")
        print()

        # Step 7: Display example results
        print("Step 7: Example results...")
        print()
        print("Candidate Analysis:")
        print(f"{'Expiration':<15} {'DTE':<6} {'Pre-Earnings':<15} {'Earnings Date':<15}")
        print("-" * 60)

        for analytics in analytics_list[:6]:  # Show first 6
            exp = analytics.iron_condor.expiration
            dte = analytics.iron_condor.short_put.dte
            is_pre = "⚠️ YES" if analytics.is_pre_earnings else "No"
            earnings_str = analytics.earnings_date or "N/A"

            print(f"{exp!s:<15} {dte:<6} {is_pre:<15} {earnings_str:<15}")

        print()
        print("="*80)
        print("✅ ALL TESTS PASSED!")
        print("="*80)
        print()
        print("Earnings integration is working correctly:")
        print("  ✅ Earnings calendar loads properly")
        print("  ✅ Options data loads properly")
        print("  ✅ Iron condors generate successfully")
        print("  ✅ Earnings detection works correctly")
        print("  ✅ Pre-earnings flagging is accurate")
        print()

        # Cleanup
        print("Cleaning up test files...")
        earnings_file.unlink()
        options_file.unlink()
        test_dir.rmdir()
        print("  ✅ Cleanup complete")
        print()

        return 0

    except Exception as e:
        print()
        print("="*80)
        print("❌ TEST FAILED!")
        print("="*80)
        print(f"Error: {e}")
        print()
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
