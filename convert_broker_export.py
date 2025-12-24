"""Convert broker option exports to Iron Condor Screener CSV format.

Supports:
- TD Ameritrade / thinkorswim exports
- Interactive Brokers (IBKR) exports
- Schwab exports
- Generic CSV with column mapping

Usage:
    python3 convert_broker_export.py input.csv --broker thinkorswim
    python3 convert_broker_export.py input.csv --broker ibkr
    python3 convert_broker_export.py input.csv --auto-detect
"""

import argparse
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional


# Column mapping for different brokers
BROKER_MAPPINGS = {
    'thinkorswim': {
        'ticker': ['Symbol', 'Underlying', 'Stock'],
        'option_type': ['Type', 'Call/Put', 'Option Type'],
        'strike': ['Strike', 'Strike Price'],
        'expiration': ['Exp Date', 'Expiration', 'Expiry'],
        'bid': ['Bid', 'Bid Price'],
        'ask': ['Ask', 'Ask Price'],
        'last': ['Last', 'Last Price', 'Mark'],
        'volume': ['Volume', 'Vol'],
        'open_interest': ['Open Int', 'OpenInt', 'OI', 'Open Interest'],
        'implied_vol': ['IV', 'Impl Vol', 'ImpVol', 'Implied Volatility'],
        'delta': ['Delta'],
        'gamma': ['Gamma'],
        'theta': ['Theta'],
        'vega': ['Vega'],
    },
    'ibkr': {
        'ticker': ['Underlying Symbol', 'Symbol'],
        'option_type': ['Right', 'Type'],
        'strike': ['Strike'],
        'expiration': ['Expiration', 'Last Trading Date'],
        'bid': ['Bid'],
        'ask': ['Ask'],
        'last': ['Last', 'Close'],
        'volume': ['Volume'],
        'open_interest': ['Open Interest'],
        'implied_vol': ['Implied Volatility'],
        'delta': ['Delta'],
        'gamma': ['Gamma'],
        'theta': ['Theta'],
        'vega': ['Vega'],
    },
    'schwab': {
        'ticker': ['Symbol', 'Underlying'],
        'option_type': ['Call/Put'],
        'strike': ['Strike'],
        'expiration': ['Expiration Date'],
        'bid': ['Bid'],
        'ask': ['Ask'],
        'last': ['Last'],
        'volume': ['Volume'],
        'open_interest': ['Open Interest'],
        'implied_vol': ['Volatility'],
        'delta': ['Delta'],
        'gamma': ['Gamma'],
        'theta': ['Theta'],
        'vega': ['Vega'],
    },
}


def detect_broker(headers: List[str]) -> Optional[str]:
    """Auto-detect broker from CSV headers.

    Args:
        headers: List of column names from CSV

    Returns:
        Broker name or None
    """
    headers_lower = [h.lower() for h in headers]

    # Check for unique indicators
    if 'impl vol' in headers_lower or 'theo price' in headers_lower:
        return 'thinkorswim'
    elif 'right' in headers_lower and 'underlying symbol' in headers_lower:
        return 'ibkr'
    elif 'call/put' in headers_lower:
        return 'schwab'

    return None


def find_column(headers: List[str], possible_names: List[str]) -> Optional[str]:
    """Find column name from list of possibilities.

    Args:
        headers: CSV column headers
        possible_names: List of possible names for this field

    Returns:
        Matching column name or None
    """
    headers_lower = {h.lower(): h for h in headers}

    for name in possible_names:
        if name.lower() in headers_lower:
            return headers_lower[name.lower()]

    return None


def normalize_option_type(value: str) -> str:
    """Normalize option type to 'call' or 'put'.

    Args:
        value: Raw option type value

    Returns:
        'call' or 'put'
    """
    value_lower = str(value).lower().strip()

    if value_lower in ['c', 'call', 'calls']:
        return 'call'
    elif value_lower in ['p', 'put', 'puts']:
        return 'put'
    else:
        raise ValueError(f"Unknown option type: {value}")


def normalize_date(value: str) -> str:
    """Normalize date to YYYY-MM-DD format.

    Args:
        value: Raw date string

    Returns:
        Date in YYYY-MM-DD format
    """
    # Try various date formats
    formats = [
        '%Y-%m-%d',
        '%m/%d/%Y',
        '%m/%d/%y',
        '%Y%m%d',
        '%d-%b-%Y',
        '%d-%b-%y',
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(value.strip(), fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue

    raise ValueError(f"Could not parse date: {value}")


def normalize_number(value: str, default: float = 0.0) -> float:
    """Parse number, handling various formats.

    Args:
        value: Raw number string
        default: Default value if parsing fails

    Returns:
        Float value
    """
    if not value or value.strip() == '':
        return default

    try:
        # Remove commas, dollar signs, etc.
        cleaned = str(value).replace(',', '').replace('$', '').strip()
        return float(cleaned)
    except ValueError:
        return default


def convert_csv(input_file: str, broker: str, output_file: str):
    """Convert broker CSV to screener format.

    Args:
        input_file: Input CSV file path
        broker: Broker name ('thinkorswim', 'ibkr', 'schwab', or 'auto')
        output_file: Output CSV file path
    """
    # Read input CSV
    with open(input_file, 'r') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames

        if not headers:
            raise ValueError("CSV has no headers")

        # Auto-detect broker if needed
        if broker == 'auto':
            broker = detect_broker(headers)
            if not broker:
                raise ValueError("Could not auto-detect broker format. Specify --broker manually.")
            print(f"Auto-detected broker: {broker}")

        # Get column mapping
        mapping = BROKER_MAPPINGS.get(broker)
        if not mapping:
            raise ValueError(f"Unknown broker: {broker}")

        # Find column names
        columns = {}
        for field, possible_names in mapping.items():
            col = find_column(headers, possible_names)
            if col:
                columns[field] = col

        print(f"Mapped {len(columns)} fields:")
        for field, col in columns.items():
            print(f"  {field}: {col}")

        # Convert rows
        converted = []
        skipped = 0

        for row in reader:
            try:
                option = {}

                # Required fields
                option['ticker'] = row.get(columns.get('ticker', ''), '').strip().upper()
                option['option_type'] = normalize_option_type(row.get(columns.get('option_type', ''), ''))
                option['strike'] = normalize_number(row.get(columns.get('strike', ''), ''))
                option['expiration'] = normalize_date(row.get(columns.get('expiration', ''), ''))

                # Pricing fields
                option['bid'] = normalize_number(row.get(columns.get('bid', ''), ''))
                option['ask'] = normalize_number(row.get(columns.get('ask', ''), ''))
                option['last'] = normalize_number(row.get(columns.get('last', ''), ''))

                # Volume/OI
                option['volume'] = int(normalize_number(row.get(columns.get('volume', ''), '0')))
                option['open_interest'] = int(normalize_number(row.get(columns.get('open_interest', ''), '0')))

                # Greeks (optional)
                option['implied_vol'] = normalize_number(row.get(columns.get('implied_vol', ''), ''), 0.0)
                option['delta'] = normalize_number(row.get(columns.get('delta', ''), ''), 0.0)
                option['gamma'] = normalize_number(row.get(columns.get('gamma', ''), ''), 0.0)
                option['theta'] = normalize_number(row.get(columns.get('theta', ''), ''), 0.0)
                option['vega'] = normalize_number(row.get(columns.get('vega', ''), ''), 0.0)

                # Skip if missing critical data
                if not option['ticker'] or option['strike'] == 0:
                    skipped += 1
                    continue

                converted.append(option)

            except Exception as e:
                print(f"Warning: Skipping row due to error: {e}")
                skipped += 1
                continue

    # Write output CSV
    fieldnames = [
        'ticker', 'option_type', 'strike', 'expiration',
        'bid', 'ask', 'last', 'volume', 'open_interest',
        'implied_vol', 'delta', 'gamma', 'theta', 'vega'
    ]

    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(converted)

    return len(converted), skipped


def main():
    parser = argparse.ArgumentParser(description='Convert broker option exports to screener format')
    parser.add_argument('input_file', help='Input CSV file from broker')
    parser.add_argument('--broker', choices=['thinkorswim', 'ibkr', 'schwab', 'auto'],
                        default='auto', help='Broker format (default: auto-detect)')
    parser.add_argument('--output', help='Output CSV file (default: data/{TICKER}_converted.csv)')

    args = parser.parse_args()

    if not Path(args.input_file).exists():
        print(f"❌ Error: File not found: {args.input_file}")
        return

    # Determine output file
    output_file = args.output
    if not output_file:
        # Try to extract ticker from filename
        ticker = Path(args.input_file).stem.split('_')[0].upper()
        output_file = f"data/{ticker}_converted.csv"

    # Create output directory
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    print(f"Converting {args.input_file}...")
    print(f"Broker: {args.broker}")

    try:
        count, skipped = convert_csv(args.input_file, args.broker, output_file)

        print(f"\n✅ Successfully converted {count} options")
        if skipped > 0:
            print(f"⚠️  Skipped {skipped} invalid rows")
        print(f"📁 Saved to: {output_file}")
        print(f"\nYou can now use this with the screener app!")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == '__main__':
    main()
