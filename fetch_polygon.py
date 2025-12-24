"""Fetch options data from Polygon.io API.

Requirements:
    pip install requests

Setup:
    1. Sign up at https://polygon.io (free tier available)
    2. Get your API key from dashboard
    3. Save in .env or pass via --api-key

Free tier limits: 5 API calls/minute

Usage:
    python3 fetch_polygon.py SPY --api-key YOUR_KEY
    python3 fetch_polygon.py SPY --from-dte 30 --to-dte 45
"""

import argparse
import csv
import os
import time
from datetime import date, timedelta
from typing import List, Dict
import requests


def get_option_contracts(ticker: str, api_key: str, expiration_date: str) -> List[str]:
    """Get list of option contracts for a given expiration.

    Args:
        ticker: Stock symbol
        api_key: Polygon.io API key
        expiration_date: Expiration date (YYYY-MM-DD)

    Returns:
        List of option contract symbols
    """
    url = f"https://api.polygon.io/v3/reference/options/contracts"

    params = {
        'underlying_ticker': ticker,
        'expiration_date': expiration_date,
        'limit': 1000,
        'apiKey': api_key
    }

    response = requests.get(url, params=params)

    if response.status_code != 200:
        raise Exception(f"API Error {response.status_code}: {response.text}")

    data = response.json()
    return [contract['ticker'] for contract in data.get('results', [])]


def get_option_snapshot(contract: str, api_key: str) -> Dict:
    """Get snapshot data for an option contract.

    Args:
        contract: Option contract symbol
        api_key: Polygon.io API key

    Returns:
        Option data dictionary
    """
    url = f"https://api.polygon.io/v3/snapshot/options/{contract}"

    params = {'apiKey': api_key}

    response = requests.get(url, params=params)

    if response.status_code != 200:
        return None

    return response.json().get('results')


def parse_option_contract_symbol(symbol: str, ticker: str) -> Dict:
    """Parse Polygon option contract symbol.

    Format: O:SPY250117C00550000
    O: = option
    SPY = underlying
    250117 = expiration (YYMMDD)
    C/P = call/put
    00550000 = strike ($550.00)

    Args:
        symbol: Polygon contract symbol
        ticker: Underlying ticker

    Returns:
        Dictionary with parsed data
    """
    # Remove "O:" prefix
    symbol = symbol.replace('O:', '')

    # Extract components
    underlying = ticker
    exp_str = symbol[len(ticker):len(ticker)+6]
    option_type = 'call' if symbol[len(ticker)+6] == 'C' else 'put'
    strike_str = symbol[len(ticker)+7:]

    # Parse expiration (YYMMDD -> YYYY-MM-DD)
    exp_year = 2000 + int(exp_str[0:2])
    exp_month = int(exp_str[2:4])
    exp_day = int(exp_str[4:6])
    expiration = f"{exp_year:04d}-{exp_month:02d}-{exp_day:02d}"

    # Parse strike (remove leading zeros and divide by 1000)
    strike = float(strike_str) / 1000.0

    return {
        'ticker': underlying,
        'option_type': option_type,
        'strike': strike,
        'expiration': expiration
    }


def fetch_options_for_expiration(ticker: str, api_key: str, expiration: date) -> List[Dict]:
    """Fetch all options for a specific expiration date.

    Args:
        ticker: Stock symbol
        api_key: Polygon.io API key
        expiration: Expiration date

    Returns:
        List of option dictionaries
    """
    exp_str = expiration.strftime('%Y-%m-%d')
    print(f"Fetching options for {ticker} expiring {exp_str}...")

    # Get contract list
    contracts = get_option_contracts(ticker, api_key, exp_str)
    print(f"Found {len(contracts)} contracts")

    options = []

    # Free tier: 5 calls/minute, so add delay
    delay = 12  # 12 seconds = 5 calls/minute

    for i, contract in enumerate(contracts):
        if i > 0 and i % 5 == 0:
            print(f"Processed {i}/{len(contracts)} (rate limiting...)")
            time.sleep(delay)

        # Get snapshot for this contract
        snapshot = get_option_snapshot(contract, api_key)

        if not snapshot:
            continue

        # Parse contract symbol
        parsed = parse_option_contract_symbol(contract, ticker)

        # Extract pricing and Greeks
        day_data = snapshot.get('day', {})
        greeks = snapshot.get('greeks', {})
        details = snapshot.get('details', {})

        option = {
            'ticker': parsed['ticker'],
            'option_type': parsed['option_type'],
            'strike': parsed['strike'],
            'expiration': parsed['expiration'],
            'bid': day_data.get('last_quote', {}).get('bid', 0.0),
            'ask': day_data.get('last_quote', {}).get('ask', 0.0),
            'last': day_data.get('close', 0.0),
            'volume': day_data.get('volume', 0),
            'open_interest': details.get('open_interest', 0),
            'implied_vol': greeks.get('implied_volatility', 0.0),
            'delta': greeks.get('delta', 0.0),
            'gamma': greeks.get('gamma', 0.0),
            'theta': greeks.get('theta', 0.0),
            'vega': greeks.get('vega', 0.0),
        }

        options.append(option)

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


def get_next_fridays(from_dte: int, to_dte: int) -> List[date]:
    """Get list of Fridays within DTE range (most options expire on Fridays).

    Args:
        from_dte: Minimum days to expiration
        to_dte: Maximum days to expiration

    Returns:
        List of expiration dates
    """
    today = date.today()
    start_date = today + timedelta(days=from_dte)
    end_date = today + timedelta(days=to_dte)

    fridays = []
    current = start_date

    while current <= end_date:
        # Friday is weekday 4
        if current.weekday() == 4:
            fridays.append(current)
        current += timedelta(days=1)

    return fridays


def main():
    parser = argparse.ArgumentParser(description='Fetch options data from Polygon.io')
    parser.add_argument('ticker', help='Stock symbol (e.g., SPY)')
    parser.add_argument('--api-key', help='Polygon.io API key (or set POLYGON_API_KEY env var)')
    parser.add_argument('--from-dte', type=int, default=30, help='Minimum days to expiration')
    parser.add_argument('--to-dte', type=int, default=45, help='Maximum days to expiration')
    parser.add_argument('--output', help='Output CSV file (default: data/{TICKER}_options.csv)')

    args = parser.parse_args()

    # Get API key
    api_key = args.api_key or os.getenv('POLYGON_API_KEY')
    if not api_key:
        print("❌ Error: No API key provided")
        print("Set POLYGON_API_KEY environment variable or use --api-key")
        print("\nGet your free API key:")
        print("1. Go to https://polygon.io")
        print("2. Sign up (free tier available)")
        print("3. Get your API key from dashboard")
        print("\nNote: Free tier has 5 API calls/minute limit")
        return

    # Get expiration dates (Fridays)
    expirations = get_next_fridays(args.from_dte, args.to_dte)

    if not expirations:
        print("❌ No expiration dates found in range")
        return

    print(f"Will fetch options for {len(expirations)} expirations:")
    for exp in expirations:
        print(f"  - {exp.strftime('%Y-%m-%d')} ({(exp - date.today()).days} DTE)")

    print("\n⚠️  Warning: This will make many API calls")
    print("Free tier limit: 5 calls/minute")
    print("Estimated time: Several minutes\n")

    # Fetch data for all expirations
    all_options = []

    try:
        for exp in expirations:
            options = fetch_options_for_expiration(args.ticker, api_key, exp)
            all_options.extend(options)

        # Save to CSV
        output_file = args.output or f"data/{args.ticker}_options.csv"
        os.makedirs('data', exist_ok=True)
        save_to_csv(all_options, output_file)

        print(f"\n✅ Successfully fetched {len(all_options)} options")
        print(f"📁 Saved to: {output_file}")
        print(f"\nYou can now use this with the screener app!")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == '__main__':
    main()
