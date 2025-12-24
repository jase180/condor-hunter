"""Fetch options data from TD Ameritrade API.

Requirements:
    pip install requests

Setup:
    1. Go to https://developer.tdameritrade.com/
    2. Create an app to get your API key (Consumer Key)
    3. Save your API key in .env file or pass via --api-key

Usage:
    python3 fetch_td_ameritrade.py SPY --api-key YOUR_KEY
    python3 fetch_td_ameritrade.py SPY --from-dte 30 --to-dte 45
"""

import argparse
import csv
import os
from datetime import date, datetime, timedelta
from typing import List, Dict
import requests


def fetch_option_chain(ticker: str, api_key: str, from_date: str = None, to_date: str = None) -> Dict:
    """Fetch option chain from TD Ameritrade API.

    Args:
        ticker: Stock symbol (e.g., 'SPY')
        api_key: TD Ameritrade API key (Consumer Key)
        from_date: Start date (YYYY-MM-DD)
        to_date: End date (YYYY-MM-DD)

    Returns:
        Dictionary containing option chain data
    """
    base_url = "https://api.tdameritrade.com/v1/marketdata/chains"

    params = {
        'apikey': api_key,
        'symbol': ticker,
        'includeQuotes': 'TRUE',
        'strategy': 'ANALYTICAL',
    }

    if from_date:
        params['fromDate'] = from_date
    if to_date:
        params['toDate'] = to_date

    print(f"Fetching options for {ticker}...")
    response = requests.get(base_url, params=params)

    if response.status_code != 200:
        raise Exception(f"API Error {response.status_code}: {response.text}")

    return response.json()


def parse_td_option_chain(data: Dict, ticker: str) -> List[Dict]:
    """Parse TD Ameritrade option chain data into our CSV format.

    Args:
        data: Raw API response
        ticker: Stock symbol

    Returns:
        List of option dictionaries ready for CSV
    """
    options = []

    # Get underlying price
    underlying_price = data.get('underlyingPrice', 0.0)

    # Process puts
    for exp_date, strikes in data.get('putExpDateMap', {}).items():
        # Parse expiration date (format: "2025-01-17:35" where 35 is DTE)
        exp_str = exp_date.split(':')[0]
        expiration = datetime.strptime(exp_str, '%Y-%m-%d').date()

        for strike, option_list in strikes.items():
            for option_data in option_list:
                options.append({
                    'ticker': ticker,
                    'option_type': 'put',
                    'strike': float(strike),
                    'expiration': expiration.strftime('%Y-%m-%d'),
                    'bid': option_data.get('bid', 0.0),
                    'ask': option_data.get('ask', 0.0),
                    'last': option_data.get('last', 0.0),
                    'volume': option_data.get('totalVolume', 0),
                    'open_interest': option_data.get('openInterest', 0),
                    'implied_vol': option_data.get('volatility', 0.0) / 100.0,  # Convert from % to decimal
                    'delta': option_data.get('delta', 0.0),
                    'gamma': option_data.get('gamma', 0.0),
                    'theta': option_data.get('theta', 0.0),
                    'vega': option_data.get('vega', 0.0),
                })

    # Process calls
    for exp_date, strikes in data.get('callExpDateMap', {}).items():
        exp_str = exp_date.split(':')[0]
        expiration = datetime.strptime(exp_str, '%Y-%m-%d').date()

        for strike, option_list in strikes.items():
            for option_data in option_list:
                options.append({
                    'ticker': ticker,
                    'option_type': 'call',
                    'strike': float(strike),
                    'expiration': expiration.strftime('%Y-%m-%d'),
                    'bid': option_data.get('bid', 0.0),
                    'ask': option_data.get('ask', 0.0),
                    'last': option_data.get('last', 0.0),
                    'volume': option_data.get('totalVolume', 0),
                    'open_interest': option_data.get('openInterest', 0),
                    'implied_vol': option_data.get('volatility', 0.0) / 100.0,
                    'delta': option_data.get('delta', 0.0),
                    'gamma': option_data.get('gamma', 0.0),
                    'theta': option_data.get('theta', 0.0),
                    'vega': option_data.get('vega', 0.0),
                })

    return options


def save_to_csv(options: List[Dict], output_file: str):
    """Save options data to CSV file."""
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
    parser = argparse.ArgumentParser(description='Fetch options data from TD Ameritrade')
    parser.add_argument('ticker', help='Stock symbol (e.g., SPY)')
    parser.add_argument('--api-key', help='TD Ameritrade API key (or set TD_API_KEY env var)')
    parser.add_argument('--from-dte', type=int, default=30, help='Minimum days to expiration')
    parser.add_argument('--to-dte', type=int, default=60, help='Maximum days to expiration')
    parser.add_argument('--output', help='Output CSV file (default: data/{TICKER}_options.csv)')

    args = parser.parse_args()

    # Get API key
    api_key = args.api_key or os.getenv('TD_API_KEY')
    if not api_key:
        print("❌ Error: No API key provided")
        print("Set TD_API_KEY environment variable or use --api-key")
        print("\nGet your API key:")
        print("1. Go to https://developer.tdameritrade.com/")
        print("2. Create an app")
        print("3. Copy your Consumer Key")
        return

    # Calculate date range
    today = date.today()
    from_date = (today + timedelta(days=args.from_dte)).strftime('%Y-%m-%d')
    to_date = (today + timedelta(days=args.to_dte)).strftime('%Y-%m-%d')

    # Fetch data
    try:
        data = fetch_option_chain(args.ticker, api_key, from_date, to_date)
        options = parse_td_option_chain(data, args.ticker)

        # Save to CSV
        output_file = args.output or f"data/{args.ticker}_options.csv"
        os.makedirs('data', exist_ok=True)
        save_to_csv(options, output_file)

        print(f"\n✅ Successfully fetched {len(options)} options")
        print(f"📁 Saved to: {output_file}")
        print(f"\nYou can now use this with the screener app!")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == '__main__':
    main()
