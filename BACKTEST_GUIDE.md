# 📊 Earnings Edge Backtesting Framework

**Validate your earnings thesis with statistical rigor.**

---

## 🎯 What This Does

The backtesting framework answers the most critical question for your iron condor strategy:

> **"Do setups that avoid earnings actually perform better?"**

Using historical simulation and statistical tests, you can validate whether your earnings-aware screening provides a measurable edge.

---

## ⚡ Quick Start (5 Minutes)

### Run the Demo

```bash
# Simulate 100 trades and generate report
python3 run_earnings_edge_backtest.py --trades 100

# View the report
cat EARNINGS_EDGE_REPORT.md
```

This demonstrates the framework with synthetic data. For real validation, you need historical options data.

---

## 🏗️ Framework Architecture

### Core Components

```
condor_screener/backtest/
├── simulator.py          # P&L simulation engine
├── metrics.py            # Performance metrics (Sharpe, win rate, drawdown)
├── earnings_analyzer.py  # Statistical comparison (pre vs post earnings)
└── report.py             # Markdown report generator
```

### What Gets Analyzed

1. **Pre-Earnings Setups** (Risky)
   - Earnings date falls 0-7 days after expiration
   - Hypothesis: These should underperform due to IV crush risk

2. **Post-Earnings Setups** (Safe)
   - Earnings date >7 days after expiration OR before entry
   - Hypothesis: These should outperform

3. **No-Earnings Data**
   - No earnings information available for ticker
   - Baseline performance

### Statistical Validation

- **Two-sample t-test** comparing returns
- **P-value < 0.05** = statistically significant
- **Effect size** measured in win rate %, avg return %, and Sharpe ratio

---

## 📊 Performance Metrics

The framework calculates:

| Metric | Description |
|--------|-------------|
| **Win Rate** | % of profitable trades |
| **Avg Return** | Mean return as % of max loss |
| **Sharpe Ratio** | Risk-adjusted return (annualized) |
| **Sortino Ratio** | Like Sharpe but uses downside deviation only |
| **Max Drawdown** | Largest peak-to-trough decline |
| **Profit Factor** | Gross profit / Gross loss |
| **Best/Worst Trade** | Extreme outcomes |
| **Avg Days Held** | Position holding period |

---

## 🎮 Exit Rules

Simulations use realistic exit logic:

```python
ExitRule(
    profit_target_pct=0.50,          # Close at 50% of max profit
    stop_loss_pct=1.0,                # Close at 100% of max loss
    min_dte_to_close=21,              # Close at 21 DTE
    close_before_earnings_days=3      # Close 3 days before earnings
)
```

**Why these matter:**
- Most traders don't hold to expiration
- Exit rules dramatically affect performance
- Framework tests realistic behavior, not theoretical extremes

---

## 🔬 Using Real Historical Data

### Step 1: Get Historical Options Data

**Option A: Tradier Historical API** (Recommended if available)
```bash
# Fetch 2 years of SPY options data
export TRADIER_SANDBOX_TOKEN="your_token"
python3 fetch_historical_tradier.py SPY --start-date 2023-01-01 --end-date 2025-01-01
```

**Option B: Manual Export from Broker**
- Export historical options data from TOS, IBKR, Schwab
- Convert to standard CSV format
- Place in `data/historical/` folder

**Option C: Use Sample Data** (For testing only)
```bash
python3 generate_sample_data.py
```

### Step 2: Fetch Earnings Calendar

```bash
pip install yfinance
python3 fetch_earnings_calendar.py SPY --historical --start-date 2023-01-01
```

Creates: `data/earnings_calendar_historical.csv`

### Step 3: Run Backtest

```python
from condor_screener.backtest import simulate_iron_condor, EarningsEdgeAnalyzer
from condor_screener.backtest.report import generate_earnings_edge_report

# Load your historical setups (iron condor candidates from past)
# Load earnings dates
# Simulate each setup with historical price data
# Analyze and generate report
```

See `examples/backtest_historical.py` for complete implementation.

---

## 📈 Interpreting Results

### Example Output

```
PRE-EARNINGS PERFORMANCE:
  Win Rate: 62.3%
  Avg Return: 8.2%
  Sharpe Ratio: 0.85

POST-EARNINGS PERFORMANCE:
  Win Rate: 74.5%
  Avg Return: 15.7%
  Sharpe Ratio: 1.42

DIFFERENCES:
  Win Rate: +12.2%
  Avg Return: +7.5%
  Sharpe Ratio: +0.57

Statistical Significance: ✅ YES (p=0.0032)
```

### What This Means

✅ **Earnings edge is REAL**
- Post-earnings setups have 12.2% higher win rate
- 7.5% better average returns
- Difference is statistically significant (p < 0.05)
- **Action**: Always avoid pre-earnings setups

### Decision Framework

| Scenario | Action |
|----------|--------|
| **p < 0.05, post > pre** | ✅ Confirmed edge - avoid pre-earnings |
| **p < 0.05, pre > post** | ❌ Hypothesis wrong - investigate further |
| **p ≥ 0.05** | ⚠️ No clear edge - collect more data |
| **< 30 trades per group** | ⚠️ Insufficient data - continue testing |

---

## 🧪 Running Your Own Backtest

### Minimal Example

```python
#!/usr/bin/env python3
"""Simple backtest example."""

from datetime import date, timedelta
from condor_screener.backtest import (
    simulate_iron_condor,
    ExitRule,
    EarningsEdgeAnalyzer,
    generate_earnings_edge_report
)

# Your historical iron condors (from 2023-2024)
iron_condors = load_historical_condors("data/historical/spy_setups.csv")
earnings_dates = load_earnings_calendar("data/earnings_calendar_historical.csv")
price_data = load_historical_prices("data/historical/spy_prices.csv")

# Simulate each setup
results = []
for ic in iron_condors:
    # Get price path for this trade
    entry_date = ic.entry_date
    price_path = get_price_path(price_data, entry_date, ic.expiration)

    # Get earnings date if exists
    earnings_date = earnings_dates.get(ic.ticker)

    # Simulate trade
    result = simulate_iron_condor(
        iron_condor=ic,
        entry_date=entry_date,
        exit_rule=ExitRule(),  # Use defaults
        price_path=price_path,
        earnings_date=earnings_date
    )
    results.append(result)

# Analyze
analyzer = EarningsEdgeAnalyzer(results)
comparison = analyzer.analyze()

# Generate report
generate_earnings_edge_report(comparison, results, "MY_BACKTEST_RESULTS.md")

print(f"✅ Results: {comparison.recommendation}")
```

---

## 📋 Key Assumptions & Limitations

### Assumptions

1. **Exit Costs**: Estimated at ~25-30% of max profit when closing early
2. **Fills**: Assumes you can enter/exit at mid price
3. **No Slippage**: Doesn't account for bid/ask spread widening
4. **No Commissions**: Add ~$2-5 per leg in real trading
5. **Geometric Brownian Motion**: Price paths simulated with GBM (simplified)

### Limitations

1. **Not Walk-Forward**: Doesn't simulate real-time decision making
2. **No Adjustments**: Assumes positions closed, not adjusted/rolled
3. **No Greeks Decay**: Simplified position valuation (not full Greeks model)
4. **Single Underlying**: Framework designed for SPY/ETFs primarily

### Why It's Still Valuable

Even with these limitations:
- **Directional accuracy**: Shows if earnings matters
- **Order of magnitude**: Reveals size of edge (if it exists)
- **Statistical rigor**: P-values tell you if results are real
- **Risk awareness**: Max drawdown shows worst-case scenarios

---

## 🎯 Production Workflow

### Monthly Routine

1. **Update Historical Data**
   ```bash
   python3 fetch_historical_tradier.py SPY --last-30-days
   python3 fetch_earnings_calendar.py SPY --last-30-days
   ```

2. **Run Updated Backtest**
   ```bash
   python3 run_earnings_edge_backtest.py --real-data
   ```

3. **Review Report**
   - Check if p-value still < 0.05
   - Monitor if edge is degrading
   - Adjust strategy if needed

4. **Document Findings**
   - Archive report with timestamp
   - Track edge over time
   - Share with trading journal

### Red Flags

⚠️ **Stop Trading If:**
- Sharpe ratio < 0.5 (poor risk-adjusted returns)
- Max drawdown > 30% (too volatile)
- P-value > 0.10 (edge may not be real)
- Win rate < 55% (not enough edge)

---

## 🔍 Advanced Features

### Custom Exit Rules

```python
# Aggressive profit-taking
aggressive_exit = ExitRule(
    profit_target_pct=0.25,  # Close at 25% profit
    stop_loss_pct=0.50,       # Stop at 50% loss
    min_dte_to_close=30,      # Close earlier
    close_before_earnings_days=7  # More conservative
)

# Let winners run
passive_exit = ExitRule(
    profit_target_pct=0.75,  # Wait for 75% profit
    stop_loss_pct=1.0,        # Full loss
    min_dte_to_close=14,      # Hold longer
    close_before_earnings_days=0  # Don't auto-close
)
```

### Position Sizing Validation

```python
from condor_screener.risk import calculate_kelly_fraction

# Kelly criterion for optimal sizing
kelly = calculate_kelly_fraction(
    win_rate=0.74,
    avg_win=0.157,
    avg_loss=0.092
)
print(f"Optimal position size: {kelly:.1%} of capital")
```

### Monte Carlo Sensitivity

```python
# Test 1000 different price paths
for i in range(1000):
    price_path = generate_gbm_path(spot=560, days=35, vol=0.15)
    result = simulate_iron_condor(ic, entry, exit_rule, price_path)
    # Aggregate results
```

---

## 📚 Files Reference

| File | Purpose |
|------|---------|
| `condor_screener/backtest/simulator.py` | Core P&L simulation logic |
| `condor_screener/backtest/metrics.py` | Performance metrics calculator |
| `condor_screener/backtest/earnings_analyzer.py` | Statistical comparison engine |
| `condor_screener/backtest/report.py` | Markdown report generator |
| `condor_screener/tests/test_backtest.py` | 16 unit tests |
| `run_earnings_edge_backtest.py` | CLI demo script |
| `BACKTEST_GUIDE.md` | This document |

---

## 🧪 Testing

```bash
# Run backtest unit tests
python3 -m pytest condor_screener/tests/test_backtest.py -v

# Run all tests (251 total)
python3 -m pytest condor_screener/tests/ -v

# Generate coverage report
pytest --cov=condor_screener.backtest --cov-report=html
```

**Current Status:** ✅ All 251 tests passing (235 original + 16 new)

---

## 🚀 Next Steps

### Immediate (This Week)

1. Run demo backtest to understand output
2. Review generated report structure
3. Understand exit rules and their impact

### Short-Term (This Month)

1. Collect 6-12 months of historical data
2. Run real backtest with actual setups
3. Validate if earnings edge exists for YOUR strategy

### Long-Term (Next Quarter)

1. Expand to multiple tickers (QQQ, IWM)
2. Test different exit rules
3. Implement walk-forward validation
4. Build Monte Carlo simulator

---

## ⚠️ Important Disclaimers

1. **Past Performance ≠ Future Results**
   - Historical backtests can't predict future performance
   - Market regimes change
   - Past edges can disappear

2. **Simulation vs Reality**
   - Real trading has slippage, commissions, and emotional factors
   - Always paper trade before risking real money
   - Start small even if backtest looks perfect

3. **Data Quality Matters**
   - Garbage in = garbage out
   - Verify historical data accuracy
   - Check for survivorship bias

4. **Statistical Significance ≠ Certainty**
   - p < 0.05 means 95% confidence, not 100%
   - Outliers can skew results
   - Need large sample sizes for reliability

---

## 💡 Pro Tips

1. **Sample Size**: Aim for 50+ trades per group (pre/post earnings) minimum
2. **Time Periods**: Test across multiple market regimes (bull, bear, high vol, low vol)
3. **Cross-Validation**: Split data into training/testing periods
4. **Sensitivity Analysis**: Test different exit rules and parameters
5. **Document Everything**: Keep backtest reports with timestamps for auditing

---

## 📧 Support

Questions about the backtesting framework?

1. Check `condor_screener/tests/test_backtest.py` for usage examples
2. Review the generated `EARNINGS_EDGE_REPORT.md` for output format
3. Read the code - it's well-documented!

---

**Ready to validate your edge?** 🦅

Run your first backtest:
```bash
python3 run_earnings_edge_backtest.py --trades 100
```
