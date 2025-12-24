"""Fetch options data from Tradier API.

Tradier offers free sandbox API with unlimited calls and real market data.

Requirements:
    pip install requests

Setup:
    1. Go to https://developer.tradier.com/
    2. Sign up (free)
    3. Get your sandbox API token from Applications dashboard
    4. Save in .env or pass via --api-key

Sandbox vs Production:
    - Sandbox: Free, unlimited calls, 15-minute delayed data (perfect for screening)
    - Production: Requires Tradier brokerage account, real-time data

Usage:
    # Sandbox (recommended for screening)
    python3 fetch_tradier.py SPY --api-key YOUR_SANDBOX_TOKEN --sandbox

    # Or set environment variable
    export TRADIER_SANDBOX_TOKEN="your_token"
    python3 fetch_tradier.py SPY --sandbox

    # Production (requires Tradier account)
    export TRADIER_TOKEN="your_token"
    python3 fetch_tradier.py SPY

    # Multiple tickers
    python3 fetch_tradier.py SPY QQQ IWM --sandbox
"""

import argparse
import csv
import os
from datetime import date, datetime, timedelta
from typing import List, Dict, Optional
import requests


# API endpoints
SANDBOX_BASE = "https://sandbox.tradier.com/v1"
PRODUCTION_BASE = "https://api.tradier.com/v1"


class TradierAPI:
    """Tradier API client."""

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
            endpoint: API endpoint (e.g., '/markets/quotes')
            params: Query parameters

        Returns:
            JSON response as dictionary
        """
        url = f"{self.base_url}{endpoint}"
        response = requests.get(url, headers=self.headers, params=params or {})

        if response.status_code != 200:
            raise Exception(f"API Error {response.status_code}: {response.text}")

        return response.json()

    def get_quote(self, symbol: str) -> Dict:
        """Get quote for underlying symbol.

        Args:
            symbol: Stock symbol (e.g., 'SPY')

        Returns:
            Quote data
        """
        data = self._get('/markets/quotes', {'symbols': symbol})
        quotes = data.get('quotes', {}).get('quote', {})

        if isinstance(quotes, list):
            return quotes[0] if quotes else {}
        return quotes

    def get_expirations(self, symbol: str) -> List[str]:
        """Get available option expiration dates.

        Args:
            symbol: Stock symbol

        Returns:
            List of expiration dates (YYYY-MM-DD format)
        """
        data = self._get('/markets/options/expirations', {'symbol': symbol})
        expirations = data.get('expirations', {}).get('date', [])

        # Ensure it's a list
        if isinstance(expirations, str):
            expirations = [expirations]

        return expirations

    def get_option_chain(self, symbol: str, expiration: str) -> Dict:
        """Get option chain for specific expiration.

        Args:
            symbol: Stock symbol
            expiration: Expiration date (YYYY-MM-DD)

        Returns:
            Option chain data
        """
        data = self._get('/markets/options/chains', {
            'symbol': symbol,
            'expiration': expiration,
            'greeks': 'true'
        })

        return data.get('options', {}).get('option', [])


def calculate_dte(expiration_str: str) -> int:
    """Calculate days to expiration.

    Args:
        expiration_str: Expiration date (YYYY-MM-DD)

    Returns:
        Days to expiration
    """
    exp_date = datetime.strptime(expiration_str, '%Y-%m-%d').date()
    return (exp_date - date.today()).days


def filter_expirations_by_dte(expirations: List[str], min_dte: int, max_dte: int) -> List[str]:
    """Filter expirations by DTE range.

    Args:
        expirations: List of expiration dates
        min_dte: Minimum days to expiration
        max_dte: Maximum days to expiration

    Returns:
        Filtered list of expirations
    """
    filtered = []

    for exp in expirations:
        dte = calculate_dte(exp)
        if min_dte <= dte <= max_dte:
            filtered.append(exp)

    return filtered


def safe_float(value, default: float = 0.0) -> float:
    """Safely convert value to float, handling None and invalid values.

    Args:
        value: Value to convert
        default: Default value if conversion fails

    Returns:
        Float value or default
    """
    if value is None or value == '':
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value, default: int = 0) -> int:
    """Safely convert value to int, handling None and invalid values.

    Args:
        value: Value to convert
        default: Default value if conversion fails

    Returns:
        Int value or default
    """
    if value is None or value == '':
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def parse_tradier_option(option: Dict, ticker: str, expiration: str) -> Dict:
    """Parse Tradier option data into our CSV format.

    Args:
        option: Tradier option data
        ticker: Underlying ticker
        expiration: Expiration date

    Returns:
        Parsed option dictionary
    """
    # Parse option type from symbol
    # Tradier format: SPY250221C00560000
    # Last 'C' or 'P' before strike indicates type
    symbol = option.get('symbol', '')
    option_type = 'call' if 'C' in symbol.split(ticker)[1][:10] else 'put'

    # Get Greeks (may be missing or None)
    greeks = option.get('greeks', {})
    if greeks is None:
        greeks = {}

    return {
        'ticker': ticker,
        'option_type': option_type,
        'strike': safe_float(option.get('strike'), 0.0),
        'expiration': expiration,
        'bid': safe_float(option.get('bid'), 0.0),
        'ask': safe_float(option.get('ask'), 0.0),
        'last': safe_float(option.get('last'), 0.0),
        'volume': safe_int(option.get('volume'), 0),
        'open_interest': safe_int(option.get('open_interest'), 0),
        'implied_vol': safe_float(greeks.get('mid_iv'), 0.0),
        'delta': safe_float(greeks.get('delta'), 0.0),
        'gamma': safe_float(greeks.get('gamma'), 0.0),
        'theta': safe_float(greeks.get('theta'), 0.0),
        'vega': safe_float(greeks.get('vega'), 0.0),
    }


def fetch_options_for_ticker(
    api: TradierAPI,
    ticker: str,
    min_dte: int,
    max_dte: int
) -> List[Dict]:
    """Fetch all options for a ticker within DTE range.

    Args:
        api: Tradier API client
        ticker: Stock symbol
        min_dte: Minimum days to expiration
        max_dte: Maximum days to expiration

    Returns:
        List of option dictionaries
    """
    print(f"\nFetching options for {ticker}...")

    # Get underlying quote
    quote = api.get_quote(ticker)
    if not quote:
        raise Exception(f"Could not get quote for {ticker}")

    print(f"Underlying price: ${quote.get('last', 0.0):.2f}")

    # Get expirations
    all_expirations = api.get_expirations(ticker)
    print(f"Found {len(all_expirations)} total expirations")

    # Filter by DTE
    expirations = filter_expirations_by_dte(all_expirations, min_dte, max_dte)
    print(f"Filtered to {len(expirations)} expirations in range {min_dte}-{max_dte} DTE:")

    for exp in expirations:
        dte = calculate_dte(exp)
        print(f"  - {exp} ({dte} DTE)")

    if not expirations:
        print(f"⚠️  No expirations found in DTE range {min_dte}-{max_dte}")
        return []

    # Fetch option chains for each expiration
    all_options = []

    for exp in expirations:
        print(f"Fetching option chain for {exp}...")
        chain = api.get_option_chain(ticker, exp)

        if isinstance(chain, dict):
            # Single option returned
            chain = [chain]

        for option in chain:
            try:
                parsed = parse_tradier_option(option, ticker, exp)

                # Skip options with missing critical data
                if parsed['strike'] == 0.0 or parsed['bid'] == 0.0 and parsed['ask'] == 0.0:
                    continue

                all_options.append(parsed)
            except Exception as e:
                print(f"Warning: Could not parse option: {e}")
                continue

        print(f"  Fetched {len(chain)} options")

    return all_options


def save_to_csv(options: List[Dict], output_file: str):
    """Save options data to CSV file.

    Args:
        options: List of option dictionaries
        output_file: Output file path
    """
    fieldnames = [
        'ticker', 'option_type', 'strike', 'expiration',
        'bid', 'ask', 'last', 'volume', 'open_interest',
        'implied_vol', 'delta', 'gamma', 'theta', 'vega'
    ]

    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(options)


def main():
    parser = argparse.ArgumentParser(
        description='Fetch options data from Tradier API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Sandbox (free, unlimited)
  python3 fetch_tradier.py SPY --sandbox --api-key YOUR_TOKEN

  # Multiple tickers
  python3 fetch_tradier.py SPY QQQ IWM --sandbox

  # Use environment variable
  export TRADIER_SANDBOX_TOKEN="your_token"
  python3 fetch_tradier.py SPY --sandbox

  # Fetch ALL expirations (useful for calendar spreads)
  python3 fetch_tradier.py SPY --sandbox --all-expirations

  # Custom DTE range
  python3 fetch_tradier.py SPY --sandbox --from-dte 20 --to-dte 45

  # Production (requires Tradier brokerage account)
  export TRADIER_TOKEN="your_token"
  python3 fetch_tradier.py SPY

Get your free sandbox token:
  https://developer.tradier.com/user/sign_up
        """
    )

    parser.add_argument('tickers', nargs='+', help='Stock symbols (e.g., SPY QQQ)')
    parser.add_argument('--api-key', help='Tradier API token (or set TRADIER_TOKEN/TRADIER_SANDBOX_TOKEN env var)')
    parser.add_argument('--sandbox', action='store_true', help='Use sandbox API (free, recommended)')
    parser.add_argument('--from-dte', type=int, default=30, help='Minimum days to expiration (default: 30)')
    parser.add_argument('--to-dte', type=int, default=60, help='Maximum days to expiration (default: 60)')
    parser.add_argument('--all-expirations', action='store_true', help='Fetch ALL expirations (useful for calendars)')
    parser.add_argument('--output-dir', default='data', help='Output directory (default: data/)')

    args = parser.parse_args()

    # Get API token
    api_token = args.api_key

    if not api_token:
        if args.sandbox:
            api_token = os.getenv('TRADIER_SANDBOX_TOKEN')
        else:
            api_token = os.getenv('TRADIER_TOKEN')

    if not api_token:
        print("❌ Error: No API token provided")
        print("\nOptions:")
        print("  1. Pass via --api-key: python3 fetch_tradier.py SPY --api-key YOUR_TOKEN")
        if args.sandbox:
            print("  2. Set environment variable: export TRADIER_SANDBOX_TOKEN='your_token'")
        else:
            print("  2. Set environment variable: export TRADIER_TOKEN='your_token'")
        print("\nGet your free sandbox token:")
        print("  https://developer.tradier.com/user/sign_up")
        return

    # Initialize API client
    api = TradierAPI(api_token, sandbox=args.sandbox)

    # Handle --all-expirations flag
    if args.all_expirations:
        min_dte = 1
        max_dte = 730  # 2 years
        dte_label = "ALL expirations (1-730 days)"
    else:
        min_dte = args.from_dte
        max_dte = args.to_dte
        dte_label = f"{min_dte}-{max_dte} days"

    mode = "sandbox" if args.sandbox else "production"
    print(f"🔗 Using Tradier API ({mode})")
    print(f"📊 Fetching {len(args.tickers)} ticker(s): {', '.join(args.tickers)}")
    print(f"📅 DTE range: {dte_label}")

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Fetch options for each ticker
    for ticker in args.tickers:
        ticker = ticker.upper()

        try:
            options = fetch_options_for_ticker(api, ticker, min_dte, max_dte)

            if not options:
                print(f"⚠️  No options found for {ticker}")
                continue

            # Save to CSV
            output_file = f"{args.output_dir}/{ticker}_options.csv"
            save_to_csv(options, output_file)

            print(f"\n✅ Successfully fetched {len(options)} options for {ticker}")
            print(f"📁 Saved to: {output_file}")

        except Exception as e:
            print(f"\n❌ Error fetching {ticker}: {e}")
            continue

    print("\n✨ Done! You can now use these files with the screener app:")
    print("   ./run_app.sh")


if __name__ == '__main__':
    main()
