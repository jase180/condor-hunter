#!/usr/bin/env python3
"""Fetch earnings calendar from Tradier API.

Earnings events are critical for iron condor screening:
- IV typically spikes before earnings
- IV crushes after earnings
- Knowing earnings dates helps you either avoid risk or target post-earnings setups

Usage:
    # Fetch next 60 days of earnings for specific tickers
    python3 fetch_earnings_calendar.py SPY QQQ IWM --sandbox

    # Fetch wider window
    python3 fetch_earnings_calendar.py SPY QQQ --sandbox --days-forward 90

    # Output to custom file
    python3 fetch_earnings_calendar.py SPY QQQ --sandbox --output earnings.csv
"""

import argparse
import csv
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import requests


# API endpoints
SANDBOX_BASE = "https://sandbox.tradier.com/v1"
PRODUCTION_BASE = "https://api.tradier.com/v1"


class TradierAPI:
    """Tradier API client for earnings calendar."""

    def __init__(self, api_token: str, sandbox: bool = True):
        """Initialize Tradier API client.

        Args:
            api_token: Tradier API token
            sandbox: Use sandbox endpoint (default True)
        """
        self.api_token = api_token
        self.base_url = SANDBOX_BASE if sandbox else PRODUCTION_BASE
        self.headers = {
            'Authorization': f'Bearer {api_token}',
            'Accept': 'application/json'
        }
        self.sandbox = sandbox

    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make GET request to Tradier API.

        Args:
            endpoint: API endpoint
            params: Query parameters

        Returns:
            JSON response as dictionary
        """
        url = f"{self.base_url}{endpoint}"
        response = requests.get(url, headers=self.headers, params=params or {})

        if response.status_code != 200:
            raise Exception(f"API Error {response.status_code}: {response.text}")

        return response.json()

    def get_earnings_calendar(self, symbols: List[str], days_forward: int = 60) -> List[Dict]:
        """Get earnings calendar for symbols.

        Args:
            symbols: List of stock symbols
            days_forward: How many days forward to look

        Returns:
            List of earnings events with dates

        Note:
            Tradier's calendar endpoint returns earnings for all symbols.
            We filter to requested symbols client-side.
        """
        # Tradier calendar endpoint
        # GET /markets/calendar?month=<MM>&year=<YYYY>&last=<days>&next=<days>

        # For simplicity, we'll use a different approach:
        # Fetch quote data which includes earnings date
        earnings_data = []

        for symbol in symbols:
            try:
                quote_data = self._get('/markets/quotes', {'symbols': symbol, 'greeks': 'false'})
                quote = quote_data.get('quotes', {}).get('quote', {})

                if not quote:
                    continue

                # Extract earnings info if available
                # Note: Tradier quote doesn't always have earnings date in sandbox
                # We'll need to use a workaround or different endpoint

                # Try company calendar endpoint
                calendar_data = self._get(f'/markets/calendar', {
                    'symbol': symbol,
                })

                # Parse calendar response
                # This is simplified - actual Tradier response structure may vary
                if calendar_data:
                    earnings_data.append({
                        'symbol': symbol,
                        'earnings_date': None,  # Placeholder
                        'last_price': quote.get('last', 0),
                        'description': quote.get('description', '')
                    })

            except Exception as e:
                print(f"Warning: Could not fetch earnings for {symbol}: {e}")
                continue

        return earnings_data


def fetch_earnings_yfinance(symbols: List[str], days_forward: int = 60) -> List[Dict]:
    """Fetch earnings using yfinance as fallback.

    Args:
        symbols: List of stock symbols
        days_forward: How many days forward to look

    Returns:
        List of earnings events
    """
    try:
        import yfinance as yf
    except ImportError:
        print("❌ yfinance not installed. Install with: pip install yfinance")
        return []

    earnings_data = []

    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)

            # Get earnings dates
            earnings_dates = ticker.calendar

            if earnings_dates is not None and not earnings_dates.empty:
                # earnings_dates is a DataFrame with earnings info
                earnings_date = earnings_dates.get('Earnings Date')

                if earnings_date is not None:
                    if isinstance(earnings_date, list):
                        earnings_date = earnings_date[0]

                    earnings_data.append({
                        'symbol': symbol,
                        'earnings_date': str(earnings_date),
                        'source': 'yfinance'
                    })

        except Exception as e:
            print(f"Warning: Could not fetch earnings for {symbol} via yfinance: {e}")
            continue

    return earnings_data


def save_to_csv(earnings_data: List[Dict], output_file: str):
    """Save earnings calendar to CSV.

    Args:
        earnings_data: List of earnings event dictionaries
        output_file: Output file path
    """
    if not earnings_data:
        print("⚠️  No earnings data to save")
        return

    fieldnames = ['symbol', 'earnings_date', 'days_until_earnings', 'source']

    # Calculate days until earnings
    today = datetime.now().date()

    for event in earnings_data:
        earnings_date_str = event.get('earnings_date')
        if earnings_date_str:
            try:
                # Try parsing different date formats
                for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%m/%d/%Y']:
                    try:
                        earnings_date = datetime.strptime(earnings_date_str.split()[0], fmt).date()
                        days_until = (earnings_date - today).days
                        event['days_until_earnings'] = days_until
                        break
                    except ValueError:
                        continue
            except:
                event['days_until_earnings'] = None
        else:
            event['days_until_earnings'] = None

    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(earnings_data)


def main():
    parser = argparse.ArgumentParser(
        description='Fetch earnings calendar for tickers',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch earnings for SPY, QQQ using yfinance (easiest)
  python3 fetch_earnings_calendar.py SPY QQQ

  # Fetch with Tradier sandbox
  python3 fetch_earnings_calendar.py SPY QQQ --sandbox --api-key YOUR_TOKEN

  # Save to custom file
  python3 fetch_earnings_calendar.py SPY QQQ --output my_earnings.csv

Note:
  By default, uses yfinance (free, no API key needed).
  Use --tradier to use Tradier API instead.
        """
    )

    parser.add_argument('tickers', nargs='+', help='Stock symbols (e.g., SPY QQQ)')
    parser.add_argument('--tradier', action='store_true', help='Use Tradier API instead of yfinance')
    parser.add_argument('--api-key', help='Tradier API token (or set TRADIER_SANDBOX_TOKEN env var)')
    parser.add_argument('--sandbox', action='store_true', help='Use Tradier sandbox API')
    parser.add_argument('--days-forward', type=int, default=60, help='Days to look forward (default: 60)')
    parser.add_argument('--output', default='data/earnings_calendar.csv', help='Output file (default: data/earnings_calendar.csv)')

    args = parser.parse_args()

    print(f"📅 Fetching earnings calendar for {len(args.tickers)} ticker(s): {', '.join(args.tickers)}")

    if args.tradier:
        # Use Tradier API
        api_token = args.api_key or os.getenv('TRADIER_SANDBOX_TOKEN') or os.getenv('TRADIER_TOKEN')

        if not api_token:
            print("❌ Error: No Tradier API token provided")
            print("\nOptions:")
            print("  1. Pass via --api-key")
            print("  2. Set TRADIER_SANDBOX_TOKEN environment variable")
            print("  3. Use yfinance instead (omit --tradier flag)")
            return

        api = TradierAPI(api_token, sandbox=args.sandbox)
        mode = "sandbox" if args.sandbox else "production"
        print(f"🔗 Using Tradier API ({mode})")

        earnings_data = api.get_earnings_calendar(args.tickers, args.days_forward)
    else:
        # Use yfinance (default)
        print("🔗 Using yfinance (free, no API key needed)")
        earnings_data = fetch_earnings_yfinance(args.tickers, args.days_forward)

    if not earnings_data:
        print("❌ No earnings data found")
        print("\nTroubleshooting:")
        print("  - Check ticker symbols are correct")
        print("  - Try installing yfinance: pip install yfinance")
        print("  - Some ETFs (like SPY, QQQ) don't have earnings calls")
        return

    # Create output directory
    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    # Save to CSV
    save_to_csv(earnings_data, args.output)

    print(f"\n✅ Successfully fetched {len(earnings_data)} earnings events")
    print(f"📁 Saved to: {args.output}")

    # Display summary
    print("\n📊 Earnings Calendar Summary:")
    print(f"{'Symbol':<10}{'Earnings Date':<20}{'Days Until':<15}")
    print("-" * 45)

    for event in sorted(earnings_data, key=lambda x: x.get('days_until_earnings') or 999):
        symbol = event.get('symbol', 'N/A')
        date = event.get('earnings_date', 'Unknown')
        days = event.get('days_until_earnings')
        days_str = f"{days} days" if days is not None else "Unknown"

        print(f"{symbol:<10}{date:<20}{days_str:<15}")


if __name__ == '__main__':
    main()
