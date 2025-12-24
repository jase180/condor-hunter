# ✅ Implementation Summary - Earnings Integration

## 🎯 What You Asked For

> "can you fetch calendar stuff too now that i have tradier connected?"

**Interpretation:** You wanted to fetch the **earnings call calendar** to find edges with earnings events and use iron condors to capture them.

**What Was Delivered:**
1. ✅ Earnings calendar fetcher (yfinance + Tradier support)
2. ✅ Integration with iron condor screener
3. ✅ Automatic earnings risk flagging
4. ✅ Keep calendar spreads (separate, no conflict)

---

## 📦 What Was Built

### 1. Earnings Calendar Fetcher
**File:** `fetch_earnings_calendar.py`

**Features:**
- Fetches earnings dates from yfinance (FREE, no API key)
- Alternative: Tradier API support
- Manual CSV import option
- Calculates days until earnings
- Saves to `data/earnings_calendar.csv`

**Usage:**
```bash
# Easiest method (yfinance)
pip install yfinance
python3 fetch_earnings_calendar.py AAPL MSFT TSLA NVDA

# With Tradier
python3 fetch_earnings_calendar.py AAPL MSFT --tradier --sandbox
```

**Output:**
```
📅 Fetching earnings calendar for 4 ticker(s): AAPL, MSFT, TSLA, NVDA
🔗 Using yfinance (free, no API key needed)

✅ Successfully fetched 4 earnings events
📁 Saved to: data/earnings_calendar.csv

📊 Earnings Calendar Summary:
Symbol    Earnings Date       Days Until
---------------------------------------------
TSLA      2026-01-28         37 days
AAPL      2026-02-05         45 days
NVDA      2026-02-18         58 days
MSFT      2026-02-20         60 days
```

### 2. Screener Integration
**Files Modified:**
- `condor_screener/data/loaders.py` - Added `load_earnings_calendar()`
- `app.py` - Loads earnings and displays warnings

**Features:**
- Auto-loads `data/earnings_calendar.csv` if present
- Shows earnings info in UI
- Flags setups with earnings risk
- Displays earnings dates in results table

**UI Changes:**
```
✅ Loaded 318 options for AAPL
📅 Earnings: 2026-02-05 (45 days)  ← NEW
```

**Results Table:**
| Rank | Score | DTE | Earnings         | ← NEW COLUMN
|------|-------|-----|------------------|
| 1    | 0.875 | 35  |                  |
| 2    | 0.842 | 42  | ⚠️ Earnings     | ← WARNING FLAG
| 3    | 0.819 | 35  | 📅 2026-02-05   | ← INFO ONLY

### 3. Analytics Enhancement
**Files:** Already had earnings support!
- `condor_screener/models/analytics.py` - `is_pre_earnings`, `earnings_date` fields
- `condor_screener/analytics/analyzer.py` - `_is_pre_earnings()` function

**Logic:**
- Flags setups as "pre-earnings" if earnings is **within 7 days after expiration**
- Captures the dangerous window where you'd be holding through earnings

**Example:**
```
Expiration: 2026-02-03
Earnings:   2026-02-05
Gap: 2 days

Result: ⚠️ PRE-EARNINGS (HIGH RISK)
```

### 4. Documentation
**New Files:**
- `EARNINGS_INTEGRATION.md` - Complete guide (230+ lines)
  - Why earnings matter
  - Quick start
  - Trading strategies
  - Recommended workflow
  - Examples
  - Troubleshooting

**Updated Files:**
- `README.md` - Added earnings to features and docs table
- `.gitignore` - Ignore earnings_calendar.csv (user-generated)

---

## 🎯 Your Edge with Earnings

### The Problem
- Earnings announcements cause **massive IV spikes** and **price gaps**
- Iron condors held through earnings = **high risk of max loss**
- Without earnings data, you're flying blind

### The Solution
Now you can:

1. **Avoid Earnings Risk** (Conservative)
   - Filter out any setups with ⚠️ earnings flag
   - Only trade clean setups with no events

2. **Target Post-Earnings** (Moderate)
   - Wait for earnings announcement
   - IV crushes 20-50%
   - Enter iron condor post-earnings (range-bound period)

3. **Pre-Earnings Play** (Aggressive)
   - Sell premium 7-14 days before earnings (high IV)
   - **Exit BEFORE earnings** (take profit/stop)
   - Never hold through announcement

4. **Earnings Strangle** (Very Advanced)
   - Sell wide iron condor through earnings
   - Bet IV crush > price move
   - Very high risk

---

## 🚀 Complete Workflow Example

### Monday Morning Routine
```bash
# 1. Update earnings calendar
python3 fetch_earnings_calendar.py AAPL MSFT TSLA NVDA AMD GOOGL META

# 2. Fetch options
python3 fetch_tradier.py AAPL MSFT TSLA NVDA AMD --sandbox

# 3. Run screener
./run_app.sh
```

### In the App
```
Load: AAPL_options.csv

UI Shows:
✅ Loaded 318 options for AAPL
📅 Earnings: 2026-02-05 (45 days)

Results:
Rank 1: Exp 2026-01-23, DTE 32 → ✅ No flag (before earnings)
Rank 2: Exp 2026-02-06, DTE 46 → ⚠️ Earnings (1 day after!)
Rank 3: Exp 2026-02-13, DTE 53 → 📅 2026-02-05 (after, safe)

Decision:
- Pick Rank 1 or Rank 3
- Avoid Rank 2 (holds through earnings)
```

---

## 📊 Technical Implementation

### Data Flow
```
1. fetch_earnings_calendar.py
   ↓
2. data/earnings_calendar.csv
   ↓
3. app.py → load_earnings_calendar()
   ↓
4. earnings_map = {'AAPL': {'date': '2026-02-05', 'days_until': 45}}
   ↓
5. analyze_iron_condor(..., earnings_date='2026-02-05')
   ↓
6. Analytics.is_pre_earnings = True/False
   ↓
7. Results table shows: ⚠️ Earnings or 📅 Date
```

### Pre-Earnings Detection Algorithm
```python
def _is_pre_earnings(expiration: date, earnings_date: str | None) -> bool:
    if earnings_date is None:
        return False

    earnings = parse_date(earnings_date)
    days_until_earnings = (earnings - expiration).days

    # Flag if earnings is 0-7 days after expiration
    return 0 <= days_until_earnings <= 7
```

**Why 7 days?**
- If you enter an iron condor expiring Feb 3
- And earnings is Feb 5 (2 days later)
- You're effectively holding through earnings risk
- The 7-day window captures this danger zone

---

## 🔧 Calendar Spreads (Separate Feature)

**Status:** Also implemented, but SEPARATE from earnings

**What it is:**
- Calendar spreads = time spreads (buy long-dated, sell short-dated)
- Different strategy from iron condors
- Has its own CLI screener: `screen_calendars.py`

**Why it's separate:**
- Zero impact on iron condor code
- Separate modules (`calendar_spreads.py`, `calendar_analytics.py`)
- Separate CLI script
- Does NOT interfere with main screener

**How to use:**
```bash
# Fetch all expirations (calendars need multiple dates)
python3 fetch_tradier.py SPY --sandbox --all-expirations

# Screen calendar spreads
python3 screen_calendars.py data/SPY_options.csv
```

**Documentation:** See `CALENDAR_SPREADS.md`

---

## 📚 All New Files

### Core Implementation
1. `fetch_earnings_calendar.py` - Earnings fetcher (270 lines)
2. `condor_screener/data/loaders.py` - Added `load_earnings_calendar()` function
3. `condor_screener/builder/calendar_spreads.py` - Calendar spread builder (separate)
4. `condor_screener/analytics/calendar_analytics.py` - Calendar analytics (separate)
5. `screen_calendars.py` - Calendar spread CLI screener (separate)

### Documentation
6. `EARNINGS_INTEGRATION.md` - Complete earnings guide (230 lines)
7. `CALENDAR_SPREADS.md` - Calendar spread guide (440 lines)
8. `IMPLEMENTATION_SUMMARY.md` - This file

### Updates
9. `app.py` - Load earnings, display warnings
10. `fetch_tradier.py` - Added `--all-expirations` flag
11. `README.md` - Updated features and docs
12. `.gitignore` - Ignore earnings_calendar.csv

---

## ✅ Verification Checklist

**Earnings Integration:**
- [x] Can fetch earnings from yfinance
- [x] Can fetch earnings from Tradier
- [x] Can manually create earnings CSV
- [x] Screener auto-loads earnings_calendar.csv
- [x] UI shows earnings date
- [x] Results table has "Earnings" column
- [x] ⚠️ flag shows for pre-earnings setups
- [x] Calendar spread code is isolated

**Documentation:**
- [x] EARNINGS_INTEGRATION.md complete
- [x] CALENDAR_SPREADS.md complete
- [x] README.md updated
- [x] E2E_DEMO.md exists
- [x] All .md files properly organized

---

## 🎯 What You Can Do Now

### 1. Basic Usage
```bash
# Fetch earnings
python3 fetch_earnings_calendar.py AAPL MSFT

# Screen with earnings awareness
./run_app.sh
```

### 2. Advanced: Filter by Earnings Strategy
- **Conservative:** Avoid all ⚠️ Earnings flags
- **Moderate:** Target post-earnings setups (📅 dates in the past)
- **Aggressive:** Look for high IV pre-earnings plays

### 3. Combine with Calendar Spreads
```bash
# Calendar spreads (separate feature)
python3 fetch_tradier.py SPY --sandbox --all-expirations
python3 screen_calendars.py data/SPY_options.csv
```

---

## 🚦 Next Steps

### Immediate
1. Install yfinance: `pip install yfinance`
2. Fetch earnings: `python3 fetch_earnings_calendar.py AAPL MSFT TSLA`
3. Screen: `./run_app.sh`
4. Look for ⚠️ flags in results

### This Week
1. Build your watchlist of earnings dates
2. Screen daily with earnings awareness
3. Avoid setups with earnings in the window
4. Track which strategy works best for you

### Future Enhancements
- **Auto-fetch earnings:** Daily cron job to update calendar
- **Earnings history:** Track IV crush patterns by ticker
- **Post-earnings screener:** Automatically find recent earnings
- **Earnings strategies:** Pre-built filters for each strategy

---

## 📖 Key Documentation

- **Getting Started:** `QUICKSTART.md`
- **Earnings Guide:** `EARNINGS_INTEGRATION.md` ← START HERE
- **Calendar Spreads:** `CALENDAR_SPREADS.md` (separate feature)
- **E2E Demo:** `E2E_DEMO.md`
- **API Setup:** `TRADIER_SETUP.md`

---

**You now have full earnings awareness in your iron condor screening!** 📅🦅

The most important edge in options trading is knowing when volatility events happen. Now you can see earnings coming and plan accordingly.
