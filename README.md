# 🦅 Iron Condor & Calendar Spread Screener

## Everything vibed with Claude with minimal edits so far to play around vibing ability and learn production Python


**Production-grade options screening platform** for iron condor and calendar spread strategies with interactive GUI, advanced analytics, and portfolio risk management.

[![Tests](https://img.shields.io/badge/tests-219%20passing-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)]()
[![License](https://img.shields.io/badge/license-MIT-blue)]()

---

## ⚡ Quick Start (60 Seconds)

```bash
# 1. Install dependencies
pip3 install streamlit plotly

# 2. Generate sample data
python3 generate_sample_data.py

# 3. Launch GUI
./run_app.sh
```

**Done!** App opens at http://localhost:8501

---

## ✨ Features

### 🎨 Interactive GUI (Streamlit)
- **Web-based interface** - No terminal wrestling
- **P&L diagrams** - Visual profit/loss curves with all key markers
- **Real-time screening** - Configure, run, analyze in seconds
- **Sortable tables** - Click to sort by any metric
- **Parameter tuning** - Sliders for DTE, delta, scoring weights

### 📊 Advanced Analytics
- **Greeks calculation** - Black-Scholes with automatic validation
- **Expected move** - Straddle-based and IV-based estimates
- **Volatility analysis** - IV rank, IV percentile, IV/RV ratio
- **Probability of Profit** - Statistical edge assessment
- **Liquidity scoring** - Bid/ask spread, volume, OI composite
- **Earnings calendar** - Automatic earnings detection and risk flagging

### 🎯 Smart Screening
- **Multi-strategy support** - Iron condors AND calendar spreads
- **Multi-factor scoring** - 5 weighted components (fully customizable)
- **Hard filters** - IV rank, bid/ask spread, volume/OI gates
- **DTE range** - Target specific expiration windows
- **Delta targeting** - 10Δ to 25Δ short strikes for ICs, ATM for calendars
- **Wing width** - Symmetric or asymmetric spreads

### 🛡️ Risk Management
- **Portfolio tracking** - Aggregate Greeks across positions
- **Margin calculation** - Know your capital requirements
- **Position sizing** - Kelly Criterion, fixed fractional, optimal-f
- **Risk limits** - Enforce delta, gamma, theta, vega, margin constraints
- **Concentration analysis** - Track exposure by ticker

### 📡 Data Sources
- **Tradier API** - Free sandbox with unlimited calls (recommended)
- **TD Ameritrade** - Real-time data if you have account
- **Polygon.io** - Free tier available
- **Manual export** - Convert from any broker (TOS, IBKR, Schwab)
- **Sample data** - Realistic test data generator included

### 🏗️ Production Ready
- **219 tests** - 100% passing (comprehensive test suite)
- **Structured logging** - Production-grade error handling
- **Error recovery** - Automatic Greeks fallback
- **Type safety** - Full type hints with Python 3.10+
- **Immutable models** - Frozen dataclasses prevent bugs

---

## 📊 What You Get

### CLI Output
```
================================================================================
  IRON CONDOR SCREENER - SPY
  Spot Price: $560.00
================================================================================

Top Iron Condor Candidates:
Rank | Score | DTE | Put Spread | Call Spread | Credit | RoR  | PoP  | Distance
-----|-------|-----|------------|-------------|--------|------|------|----------
  1  | 0.875 | 35  | 540/545    | 575/580     | $4.00  | 45%  | 72%  | 8.5%
  2  | 0.832 | 35  | 535/540    | 580/585     | $3.50  | 38%  | 68%  | 9.2%
```

### GUI Interface
- **Results table** with top 20 candidates
- **Interactive P&L chart** showing profit/loss at expiration
- **Detailed metrics** panel with all analytics
- **Configuration sidebar** for real-time parameter tuning

---

## 🚀 Installation

### Option 1: Quick Install
```bash
pip3 install -r requirements.txt
```

### Option 2: Minimal (CLI Only)
```bash
pip3 install pyyaml numpy scipy
```

### Option 3: Full (GUI + Risk + Testing)
```bash
pip3 install -r requirements.txt
```

**Requirements:**
- Python 3.10+ (uses `|` union syntax)
- numpy, scipy (for Black-Scholes Greeks)
- streamlit, plotly (for GUI - optional)
- pytest (for testing - optional)

---

## 📖 Usage

### GUI Workflow (Recommended)

1. **Get data:**
```bash
# Option A: Use Tradier (free, unlimited)
export TRADIER_SANDBOX_TOKEN="your_token"
python3 fetch_tradier.py SPY --sandbox

# Option B: Use sample data
python3 generate_sample_data.py
```

2. **Launch app:**
```bash
./run_app.sh
```

3. **Screen:**
   - Select CSV file
   - Configure parameters (DTE, delta, filters)
   - Click "Run Screening"
   - Analyze results and P&L diagrams

### CLI Workflow

```python
from condor_screener import *

# Load data
options = load_options_from_csv("data/SPY_options.csv")

# Filter options
filtered = filter_options(options, FilterConfig(min_iv_rank=30))

# Generate candidates
candidates = list(generate_iron_condors(filtered, StrategyConfig()))

# Analyze
analytics = [analyze_iron_condor(ic, spot=560.0) for ic in candidates]

# Score and rank
ranked = rank_analytics(analytics, ScoringConfig())

# Display top 10
for i, a in enumerate(ranked[:10]):
    print(f"#{i+1}: {a.iron_condor} - Score: {a.composite_score:.3f}")
```

### Calendar Spread Workflow

```bash
# 1. Fetch data with ALL expirations (calendars need multiple DTEs)
export TRADIER_SANDBOX_TOKEN="your_token"
python3 fetch_tradier.py SPY --sandbox --all-expirations

# 2. Screen calendar spreads
python3 screen_calendars.py data/SPY_options.csv

# 3. Screen both calls and puts
python3 screen_calendars.py data/SPY_options.csv --both

# 4. Customize parameters
python3 screen_calendars.py data/SPY_options.csv \
    --min-short-dte 25 --max-short-dte 35 \
    --min-long-dte 50 --min-gap 20
```

See [CALENDAR_SPREADS.md](CALENDAR_SPREADS.md) for complete calendar spread guide.

---

## 🗂️ Project Structure

```
condor-hunter/
├── app.py                          # Streamlit GUI
├── run_app.sh                      # GUI launcher
├── screen_calendars.py             # Calendar spread CLI screener
├── fetch_tradier.py                # Tradier API fetcher
├── fetch_td_ameritrade.py          # TD Ameritrade fetcher
├── fetch_polygon.py                # Polygon.io fetcher
├── convert_broker_export.py        # Convert manual exports
├── generate_sample_data.py         # Sample data generator
│
├── condor_screener/                # Core library
│   ├── models/                     # Data models
│   │   ├── option.py               # Option dataclass
│   │   ├── iron_condor.py          # IronCondor dataclass
│   │   └── analytics.py            # Analytics dataclass
│   │
│   ├── data/                       # Data loading & filtering
│   │   ├── loaders.py              # CSV loader
│   │   └── validators.py           # Hard filters
│   │
│   ├── builder/                    # Strategy construction
│   │   ├── strategy.py             # Iron condor generator
│   │   └── calendar_spreads.py     # Calendar spread generator
│   │
│   ├── analytics/                  # Analysis modules
│   │   ├── analysis.py             # Main analyzer
│   │   ├── calendar_analytics.py   # Calendar spread analytics
│   │   ├── greeks.py               # Black-Scholes Greeks
│   │   └── metrics.py              # Expected move, IV, etc.
│   │
│   ├── scoring/                    # Ranking system
│   │   └── scorer.py               # Multi-factor scoring
│   │
│   ├── risk/                       # Risk management
│   │   ├── margin.py               # Margin calculations
│   │   ├── portfolio.py            # Portfolio risk manager
│   │   └── position_sizing.py      # Kelly, fixed fractional
│   │
│   ├── utils/                      # Infrastructure
│   │   ├── logging_config.py       # Structured logging
│   │   ├── error_handling.py       # Error recovery
│   │   └── cache.py                # Performance caching
│   │
│   └── tests/                      # Comprehensive test suite
│       ├── test_analytics.py       # 36 tests
│       ├── test_greeks.py          # 29 tests
│       ├── test_risk.py            # 45 tests
│       └── ...                     # 219 total tests
│
├── data/                           # Your CSV files
├── docs/                           # Documentation
│   ├── QUICKSTART.md               # 60-second guide
│   ├── E2E_DEMO.md                 # End-to-end demo walkthrough
│   ├── GUI_USAGE.md                # Complete app guide
│   ├── CALENDAR_SPREADS.md         # Calendar spread guide
│   ├── TRADIER_SETUP.md            # API setup (2 mins)
│   ├── DATA_FETCHERS.md            # All data sources
│   └── CRITIQUE.md                 # Technical deep dive
│
└── requirements.txt                # Dependencies
```

---

## 🎛️ Configuration

### Strategy Parameters
```python
strategy_config = StrategyConfig(
    min_dte=30,
    max_dte=45,
    target_delta=0.15,      # 15 delta short strikes
    delta_tolerance=0.05,    # ±5 delta acceptable
    wing_width=5.0,          # $5 wide spreads
)
```

### Filtering
```python
filter_config = FilterConfig(
    min_iv_rank=30.0,
    min_iv_percentile=30.0,
    max_bid_ask_spread_pct=0.15,
    min_volume=1,
    min_open_interest=100,
)
```

### Scoring Weights
```python
scoring_config = ScoringConfig(
    weight_return_on_risk=0.30,
    weight_pop=0.25,
    weight_expected_move_safety=0.20,
    weight_liquidity=0.15,
    weight_iv_rank=0.10,
)
```

---

## 📊 Data Sources

### Tradier Sandbox (⭐ Recommended)
```bash
# Free, unlimited, no broker account needed
export TRADIER_SANDBOX_TOKEN="your_token"
python3 fetch_tradier.py SPY --sandbox
```
[Setup guide](TRADIER_SETUP.md) | [Get free token](https://developer.tradier.com/)

### TD Ameritrade
```bash
# Real-time, requires TD account
export TD_API_KEY="your_key"
python3 fetch_td_ameritrade.py SPY
```

### Manual Export
```bash
# Works with any broker
python3 convert_broker_export.py your_export.csv --auto-detect
```

See [DATA_FETCHERS.md](DATA_FETCHERS.md) for complete guide.

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest condor_screener/tests/test_greeks.py -v

# Run with coverage
pytest --cov=condor_screener --cov-report=html
```

**Test Coverage:**
- 219 tests total
- 100% pass rate
- Covers: analytics, Greeks, risk management, data loading, scoring

---

## 🎯 Use Cases

### Conservative Iron Condors
- Target delta: 0.10 (10Δ)
- Wing width: $7-10
- Min DTE: 40-50
- Emphasize: Expected move cushion, PoP

### Aggressive Income
- Target delta: 0.20-0.25 (20-25Δ)
- Wing width: $3-5
- Min DTE: 20-30
- Emphasize: Return on risk

### Portfolio Management
```python
from condor_screener.risk import PortfolioRiskManager, Position

portfolio = PortfolioRiskManager(
    positions=[pos1, pos2, pos3],
    account_value=100000
)

# Check risk limits
violations = portfolio.check_risk_limits(
    max_delta=100,
    max_margin_pct=50.0
)

# Get portfolio summary
summary = portfolio.portfolio_summary()
print(f"Portfolio Delta: {summary['total_delta']}")
print(f"Margin Used: {summary['margin_utilization_pct']:.1f}%")
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [QUICKSTART.md](QUICKSTART.md) | Get running in 60 seconds |
| [E2E_DEMO.md](E2E_DEMO.md) | Complete end-to-end demo walkthrough |
| [EARNINGS_INTEGRATION.md](EARNINGS_INTEGRATION.md) | Earnings calendar integration guide |
| [GUI_USAGE.md](GUI_USAGE.md) | Complete app user guide |
| [CALENDAR_SPREADS.md](CALENDAR_SPREADS.md) | Calendar spread screening guide |
| [TRADIER_SETUP.md](TRADIER_SETUP.md) | API setup (2 minutes) |
| [DATA_FETCHERS.md](DATA_FETCHERS.md) | All data source options |
| [CRITIQUE.md](CRITIQUE.md) | Technical deep dive & architecture |

---

## 🔧 Development

### Run Tests
```bash
pytest
```

### Type Checking
```bash
mypy condor_screener/
```

### Code Style
```bash
black condor_screener/
flake8 condor_screener/
```

---

## 🗺️ Roadmap

### ✅ Completed
- Core screening engine (iron condors & calendar spreads)
- Black-Scholes Greeks calculator
- Portfolio risk management
- Position sizing (Kelly, fixed fractional)
- Streamlit GUI with P&L diagrams
- Tradier/TD/Polygon data fetchers with full expiration support
- 219 comprehensive tests
- Production logging & error handling
- Calendar spread screener with theta/vega analysis

### 🔄 In Progress
- Volatility surface modeling
- Backtesting framework
- Real-time Greeks updates

### 📋 Planned
- Monte Carlo P&L simulation
- Additional strategies (butterflies, diagonals, ratio spreads)
- Trade journal integration
- Broker API execution (paper trading)

---

## ⚠️ Disclaimer

**This tool is for educational and research purposes only.**

- Not financial advice
- No guarantees of profitability
- Options trading involves substantial risk
- Verify all calculations independently
- Past performance ≠ future results

**Always paper trade first. Never risk more than you can afford to lose.**

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🙏 Credits

Built with:
- [Streamlit](https://streamlit.io/) - Interactive GUI
- [Plotly](https://plotly.com/) - P/L visualizations
- [NumPy](https://numpy.org/) & [SciPy](https://scipy.org/) - Greeks calculations
- [Tradier](https://developer.tradier.com/) - Free market data API

---

## 📧 Support

- **Issues:** Open an issue on GitHub
- **Documentation:** Check the `docs/` folder
- **Quick help:** See [QUICKSTART.md](QUICKSTART.md)

---

**Happy screening!** 🦅📈
