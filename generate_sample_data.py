"""Generate realistic sample options data for testing the Iron Condor Screener.

This creates a CSV file with realistic options chains for SPY.
"""

import csv
from datetime import date, timedelta
from math import exp, log, sqrt
from scipy.stats import norm

# Sample data parameters
TICKER = "SPY"
SPOT_PRICE = 560.0
IV_RANK = 45.0
IV_PERCENTILE = 48.0
RISK_FREE_RATE = 0.045  # 4.5%

# Expirations (35 and 42 DTE)
TODAY = date.today()
EXPIRATION_1 = TODAY + timedelta(days=35)
EXPIRATION_2 = TODAY + timedelta(days=42)

def black_scholes_greeks(spot, strike, time_to_expiry, rate, vol, option_type):
    """Calculate Black-Scholes Greeks."""
    if time_to_expiry <= 0:
        return 0.0, 0.0, 0.0, 0.0

    d1 = (log(spot / strike) + (rate + 0.5 * vol ** 2) * time_to_expiry) / (vol * sqrt(time_to_expiry))
    d2 = d1 - vol * sqrt(time_to_expiry)

    if option_type == 'call':
        delta = norm.cdf(d1)
        price = spot * norm.cdf(d1) - strike * exp(-rate * time_to_expiry) * norm.cdf(d2)
    else:  # put
        delta = -norm.cdf(-d1)
        price = strike * exp(-rate * time_to_expiry) * norm.cdf(-d2) - spot * norm.cdf(-d1)

    # Gamma (same for calls and puts)
    gamma = norm.pdf(d1) / (spot * vol * sqrt(time_to_expiry))

    # Theta (per year, divide by 365 for daily)
    if option_type == 'call':
        theta = (-spot * norm.pdf(d1) * vol / (2 * sqrt(time_to_expiry))
                 - rate * strike * exp(-rate * time_to_expiry) * norm.cdf(d2))
    else:  # put
        theta = (-spot * norm.pdf(d1) * vol / (2 * sqrt(time_to_expiry))
                 + rate * strike * exp(-rate * time_to_expiry) * norm.cdf(-d2))

    # Vega (per 1% change in vol)
    vega = spot * norm.pdf(d1) * sqrt(time_to_expiry) / 100

    return delta, gamma, theta, vega, price


def generate_option_chain(spot, expiration, dte):
    """Generate realistic option chain for given expiration."""
    options = []
    time_to_expiry = dte / 365.0

    # IV smile: higher IV for OTM options
    def get_iv(strike, spot, option_type):
        moneyness = abs(strike - spot) / spot
        base_iv = 0.22  # ATM IV
        # IV increases for OTM
        iv_adjustment = moneyness * 0.3
        return base_iv + iv_adjustment

    # Generate strikes from -15% to +15% around spot, every $5
    min_strike = int(spot * 0.85 / 5) * 5
    max_strike = int(spot * 1.15 / 5) * 5

    for strike in range(min_strike, max_strike + 1, 5):
        strike = float(strike)

        # Calculate distance from ATM (for volume/OI simulation)
        distance_pct = abs(strike - spot) / spot

        # Volume and OI decrease as we go OTM
        base_volume = max(10, int(5000 * exp(-distance_pct * 10)))
        base_oi = max(100, int(50000 * exp(-distance_pct * 8)))

        for option_type in ['put', 'call']:
            iv = get_iv(strike, spot, option_type)
            delta, gamma, theta, vega, theo_price = black_scholes_greeks(
                spot, strike, time_to_expiry, RISK_FREE_RATE, iv, option_type
            )

            # Add bid/ask spread (tighter for ATM, wider for OTM)
            spread_pct = 0.01 + distance_pct * 0.05  # 1-6% spread
            bid = max(0.01, theo_price * (1 - spread_pct))
            ask = theo_price * (1 + spread_pct)
            last = (bid + ask) / 2

            # Adjust volume (calls typically more volume than puts for equities)
            volume_multiplier = 1.2 if option_type == 'call' else 0.8
            volume = int(base_volume * volume_multiplier * (0.8 + 0.4 * abs(delta)))
            oi = int(base_oi * volume_multiplier * (0.8 + 0.4 * abs(delta)))

            options.append({
                'ticker': TICKER,
                'option_type': option_type,
                'strike': f"{strike:.1f}",
                'expiration': expiration.strftime('%Y-%m-%d'),
                'bid': f"{bid:.2f}",
                'ask': f"{ask:.2f}",
                'last': f"{last:.2f}",
                'volume': volume,
                'open_interest': oi,
                'implied_vol': f"{iv:.4f}",
                'delta': f"{delta:.4f}",
                'gamma': f"{gamma:.6f}",
                'theta': f"{theta:.4f}",
                'vega': f"{vega:.4f}",
                'iv_rank': f"{IV_RANK:.1f}",
                'iv_percentile': f"{IV_PERCENTILE:.1f}",
            })

    return options


def main():
    """Generate sample data and save to CSV."""
    print(f"Generating sample options data for {TICKER}...")
    print(f"Spot price: ${SPOT_PRICE:.2f}")
    print(f"Expirations: {EXPIRATION_1} (35 DTE), {EXPIRATION_2} (42 DTE)")

    all_options = []

    # Generate for both expirations
    all_options.extend(generate_option_chain(SPOT_PRICE, EXPIRATION_1, 35))
    all_options.extend(generate_option_chain(SPOT_PRICE, EXPIRATION_2, 42))

    # Write to CSV
    output_file = f"data/{TICKER}_sample_options.csv"

    fieldnames = [
        'ticker', 'option_type', 'strike', 'expiration',
        'bid', 'ask', 'last', 'volume', 'open_interest',
        'implied_vol', 'delta', 'gamma', 'theta', 'vega',
        'iv_rank', 'iv_percentile'
    ]

    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_options)

    print(f"\n✅ Generated {len(all_options)} options")
    print(f"📁 Saved to: {output_file}")
    print(f"\nYou can now use this file with the screener app!")
    print(f"Run: ./run_app.sh")


if __name__ == '__main__':
    main()
