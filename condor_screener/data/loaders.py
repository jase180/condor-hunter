"""Data loaders for option chains from various sources."""

import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import List

from ..models.option import Option
from ..utils.error_handling import DataValidationError

logger = logging.getLogger("condor_screener.loaders")


def load_options_from_csv(csv_path: str | Path) -> List[Option]:
    """Load option chain from CSV file.

    Expected CSV format:
        ticker,strike,expiration,option_type,bid,ask,last,volume,open_interest,
        delta,gamma,theta,vega,implied_vol

    Args:
        csv_path: Path to CSV file

    Returns:
        List of Option objects

    Raises:
        FileNotFoundError: If CSV file doesn't exist
        ValueError: If CSV has invalid data or missing required fields
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        logger.error("CSV file not found: %s", csv_path)
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    logger.info("Loading option chain from CSV: %s", csv_path)

    options = []
    required_fields = {
        'ticker', 'strike', 'expiration', 'option_type', 'bid', 'ask',
        'volume', 'open_interest', 'delta', 'implied_vol'
    }

    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)

            # Validate headers
            if not required_fields.issubset(set(reader.fieldnames or [])):
                missing = required_fields - set(reader.fieldnames or [])
                logger.error("CSV missing required fields: %s", missing)
                raise DataValidationError(f"CSV missing required fields: {missing}")

            skipped_rows = 0
            for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                try:
                    option = _parse_option_row(row)
                    options.append(option)
                except Exception as e:
                    logger.warning(
                        "Skipping row %d in %s due to error: %s",
                        row_num, csv_path.name, e
                    )
                    skipped_rows += 1
                    continue

            if skipped_rows > 0:
                logger.warning(
                    "Skipped %d invalid rows out of %d total rows in %s",
                    skipped_rows, row_num - 1, csv_path.name
                )

    except FileNotFoundError:
        raise
    except DataValidationError:
        raise
    except Exception as e:
        logger.error("Error reading CSV file %s: %s", csv_path, e)
        raise DataValidationError(f"Failed to read CSV file {csv_path}: {e}")

    if not options:
        logger.error("No valid options found in %s", csv_path)
        raise DataValidationError(f"No valid options found in {csv_path}")

    logger.info("Successfully loaded %d options from %s", len(options), csv_path.name)
    return options


def _parse_option_row(row: dict) -> Option:
    """Parse a single CSV row into an Option object.

    Args:
        row: Dictionary from csv.DictReader

    Returns:
        Option object

    Raises:
        ValueError: If required fields are missing or invalid
    """
    # Parse expiration date (supports multiple formats)
    exp_str = row['expiration'].strip()
    try:
        # Try ISO format first (YYYY-MM-DD)
        expiration = datetime.strptime(exp_str, '%Y-%m-%d').date()
    except ValueError:
        try:
            # Try MM/DD/YYYY format
            expiration = datetime.strptime(exp_str, '%m/%d/%Y').date()
        except ValueError:
            raise ValueError(f"Invalid expiration date format: {exp_str}")

    # Parse option type
    option_type = row['option_type'].strip().lower()
    if option_type not in ('call', 'put'):
        raise ValueError(f"Invalid option_type: {option_type}")

    # Parse optional fields (gamma, theta, vega)
    def parse_optional_float(value: str) -> float | None:
        value = value.strip()
        if not value or value.lower() in ('', 'null', 'none', 'nan'):
            return None
        return float(value)

    # Parse last price (optional)
    last_str = row.get('last', '').strip()
    last = parse_optional_float(last_str)

    return Option(
        ticker=row['ticker'].strip().upper(),
        strike=float(row['strike']),
        expiration=expiration,
        option_type=option_type,  # type: ignore
        bid=float(row['bid']),
        ask=float(row['ask']),
        last=last,
        volume=int(row['volume']),
        open_interest=int(row['open_interest']),
        delta=float(row['delta']),
        gamma=parse_optional_float(row.get('gamma', '')),
        theta=parse_optional_float(row.get('theta', '')),
        vega=parse_optional_float(row.get('vega', '')),
        implied_vol=float(row['implied_vol']),
    )


class OptionChainData:
    """Container for option chain data with metadata."""

    def __init__(self, options: List[Option], spot_price: float,
                 historical_ivs: List[float] | None = None,
                 historical_prices: List[tuple[float, float, float, float]] | None = None,
                 earnings_date: str | None = None):
        """Initialize option chain data.

        Args:
            options: List of Option objects
            spot_price: Current underlying price
            historical_ivs: Optional list of historical IVs (for IV rank/percentile)
            historical_prices: Optional list of (open, high, low, close) tuples
                for realized volatility calculation
            earnings_date: Optional earnings date (ISO format string)
        """
        self.options = options
        self.spot_price = spot_price
        self.historical_ivs = historical_ivs or []
        self.historical_prices = historical_prices or []
        self.earnings_date = earnings_date

    @property
    def ticker(self) -> str:
        """Get ticker symbol (assumes all options have same ticker)."""
        if not self.options:
            raise ValueError("No options in chain")
        return self.options[0].ticker


def load_earnings_calendar(csv_path: str | Path) -> dict[str, dict]:
    """Load earnings calendar from CSV file.

    Expected CSV format:
        symbol,earnings_date,days_until_earnings,source

    Args:
        csv_path: Path to earnings calendar CSV file

    Returns:
        Dictionary mapping ticker symbols to earnings data:
        {
            'SPY': {'date': '2026-01-30', 'days_until': 42},
            'AAPL': {'date': '2026-02-05', 'days_until': 48},
            ...
        }

    Example:
        >>> earnings = load_earnings_calendar('data/earnings_calendar.csv')
        >>> aapl_earnings = earnings.get('AAPL')
        >>> if aapl_earnings:
        ...     print(f"AAPL reports in {aapl_earnings['days_until']} days")
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        logger.warning("Earnings calendar file not found: %s", csv_path)
        return {}

    logger.info("Loading earnings calendar from: %s", csv_path)

    earnings_map = {}

    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)

            for row in reader:
                try:
                    symbol = row['symbol'].strip().upper()
                    earnings_date = row.get('earnings_date', '').strip()
                    days_until_str = row.get('days_until_earnings', '').strip()

                    # Parse days until
                    days_until = None
                    if days_until_str and days_until_str.lower() not in ('', 'none', 'null'):
                        try:
                            days_until = int(float(days_until_str))
                        except ValueError:
                            pass

                    if earnings_date and earnings_date.lower() not in ('', 'none', 'null', 'unknown'):
                        earnings_map[symbol] = {
                            'date': earnings_date,
                            'days_until': days_until
                        }

                except (KeyError, ValueError) as e:
                    logger.warning("Skipping invalid earnings row: %s", e)
                    continue

    except Exception as e:
        logger.error("Error reading earnings calendar %s: %s", csv_path, e)
        return {}

    logger.info("Loaded earnings data for %d symbols", len(earnings_map))
    return earnings_map
