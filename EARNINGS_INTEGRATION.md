# 📅 Earnings Calendar Integration

**Find your edge with earnings events!**

The screener now integrates earnings calendars to help you identify opportunities and risks around earnings announcements.

---

## 🎯 Why Earnings Matter for Iron Condors

### IV Spike Before Earnings
- Implied volatility typically **increases** 3-7 days before earnings
- Premium sellers can collect **higher credits**
- Risk: Price can gap significantly on earnings

### IV Crush After Earnings
- IV typically **collapses** after earnings announcement
- Great opportunity for post-earnings iron condors
- Lower risk of large moves after the event

### Your Edge
1. **Avoid earnings risk**: See which setups have earnings within the trade window
2. **Target post-earnings**: Find stocks that just reported (lower IV going forward)
3. **Earnings plays**: Sell premium before earnings (high risk, high reward)

---

## 🚀 Quick Start

### Step 1: Fetch Earnings Calendar
```bash
# Install yfinance (easiest method)
pip install yfinance

# Fetch earnings for your tickers
python3 fetch_earnings_calendar.py AAPL MSFT TSLA NVDA AMD

# Saves to data/earnings_calendar.csv
```

**Example Output:**
```
📅 Fetching earnings calendar for 5 ticker(s): AAPL, MSFT, TSLA, NVDA, AMD
🔗 Using yfinance (free, no API key needed)

✅ Successfully fetched 5 earnings events
📁 Saved to: data/earnings_calendar.csv

📊 Earnings Calendar Summary:
Symbol    Earnings Date       Days Until
---------------------------------------------
TSLA      2026-01-28         37 days
AAPL      2026-02-05         45 days
AMD       2026-02-10         50 days
NVDA      2026-02-18         58 days
MSFT      2026-02-20         60 days
```

### Step 2: Run the Screener
```bash
./run_app.sh
```

The app will automatically detect `data/earnings_calendar.csv` and:
- Show earnings date in the info panel
- Flag setups with earnings risk
- Display earnings dates in the results table

---

## 📊 How It Works

### Data Loading
When you screen options for a ticker:

1. App loads options from CSV
2. App checks for `data/earnings_calendar.csv`
3. If found, loads earnings dates for that ticker
4. Shows earnings info in the UI:
   ```
   ✅ Loaded 318 options for AAPL
   📅 Earnings: 2026-02-05 (45 days)
   ```

### Earnings Detection
For each iron condor candidate:

- **is_pre_earnings**: True if earnings date is within 7 days after expiration
- **earnings_date**: The actual earnings date (if available)

**Pre-earnings logic:**
```
Expiration: 2026-02-03
Earnings:   2026-02-05
Days After: 2

Result: ⚠️ PRE-EARNINGS (earnings within 7 days of expiration)
```

### Results Table
The results table shows an "Earnings" column:

| Rank | Score | DTE | Earnings         |
|------|-------|-----|------------------|
| 1    | 0.875 | 35  |                  |
| 2    | 0.842 | 42  | ⚠️ Earnings     |
| 3    | 0.819 | 35  | 📅 2026-02-05   |

**Flags:**
- **⚠️ Earnings** - Expiration is before/around earnings (HIGH RISK)
- **📅 [Date]** - Earnings date for reference (not immediate risk)
- **(empty)** - No earnings data available

---

## 🎛️ Fetching Earnings Data

### Method 1: yfinance (Recommended)
```bash
# Install (one-time)
pip install yfinance

# Fetch earnings
python3 fetch_earnings_calendar.py AAPL MSFT GOOGL AMZN

# Works for most US stocks
# Free, no API key needed
# Updates automatically
```

**Pros:**
- ✅ No API key required
- ✅ Free and unlimited
- ✅ Works for most US stocks
- ✅ Easy to use

**Cons:**
- ⚠️ Doesn't work for ETFs (SPY, QQQ, IWM don't have earnings)
- ⚠️ Some companies may have missing data

### Method 2: Tradier API (Alternative)
```bash
# Use your existing Tradier token
python3 fetch_earnings_calendar.py AAPL MSFT --tradier --sandbox
```

**Pros:**
- ✅ Same API you use for options data
- ✅ Consistent data source

**Cons:**
- ⚠️ Requires API token
- ⚠️ May have limited earnings data in sandbox

### Method 3: Manual Entry
Create `data/earnings_calendar.csv` manually:

```csv
symbol,earnings_date,days_until_earnings,source
AAPL,2026-02-05,45,manual
MSFT,2026-02-20,60,manual
TSLA,2026-01-28,37,manual
```

**Pros:**
- ✅ Full control
- ✅ Can add any ticker

**Cons:**
- ⚠️ Manual updates required
- ⚠️ Time-consuming for many tickers

---

## 💡 Trading Strategies with Earnings

### 1. Avoid Earnings Risk (Conservative)
**Goal:** Only trade setups with NO earnings in the trade window

**Steps:**
1. Fetch earnings calendar for your tickers
2. Run screener
3. **Filter out** any setups marked "⚠️ Earnings"
4. Focus on clean setups with no earnings events

**Example:**
```
✅ Trade:  Exp 2026-01-23 (no earnings until March)
❌ Avoid: Exp 2026-02-05 (earnings on 2026-02-08)
```

### 2. Post-Earnings Opportunity (Moderate Risk)
**Goal:** Enter iron condors AFTER earnings (IV crush opportunity)

**Steps:**
1. Wait for earnings announcement
2. IV drops significantly (20-50%)
3. Stock typically stays range-bound post-earnings
4. Enter iron condor to capture remaining premium

**Example:**
```
Earnings: 2026-01-28
Wait until: 2026-01-29 or later
Entry: Sell iron condor with Feb expiration
Rationale: IV crushed, stock in digestion mode
```

### 3. Pre-Earnings Play (Aggressive)
**Goal:** Sell premium before earnings to capture IV spike

**Steps:**
1. Identify stocks with high IV into earnings
2. Sell iron condor 7-14 days before earnings
3. **Exit BEFORE earnings** (take profit or stop loss)
4. Never hold through earnings announcement

**Example:**
```
Earnings: 2026-02-05
Entry: 2026-01-22 (14 days before)
Exit: 2026-02-04 (1 day before earnings)
Risk: Must actively manage - can't hold through announcement
```

⚠️ **Warning:** This is HIGH RISK. Earnings can gap the stock past your strikes.

### 4. Earnings Strangle/Straddle (Advanced)
**Goal:** Sell iron condor across earnings, betting on IV crush

**Steps:**
1. Sell wide iron condor before earnings (high premium)
2. **Hold through earnings**
3. Bet that IV crush offsets potential price move
4. Very wide strikes required

⚠️ **Warning:** VERY HIGH RISK. Not recommended unless you have significant experience.

---

## 📈 Recommended Workflow

### Daily Screening Routine
```bash
# Monday morning:

# 1. Update earnings calendar
python3 fetch_earnings_calendar.py AAPL MSFT TSLA NVDA AMD GOOGL META AMZN

# 2. Fetch options data
python3 fetch_tradier.py AAPL MSFT TSLA NVDA AMD --sandbox

# 3. Run screener
./run_app.sh

# 4. In the app:
#    - Load each ticker's options
#    - Check earnings flag in results
#    - Filter by strategy (avoid, target post-earnings, etc.)
#    - Pick best setups
```

### Weekly Planning
```bash
# Sunday evening:

# 1. Check earnings calendar for the week
python3 fetch_earnings_calendar.py <your watchlist>

# 2. Note which companies report this week
grep -E "7 days|6 days|5 days|4 days|3 days|2 days|1 days" data/earnings_calendar.csv

# 3. Plan trades:
#    - Close any positions with earnings this week
#    - Identify post-earnings opportunities
#    - Look for high IV pre-earnings (if doing earnings plays)
```

---

## 🔧 Advanced Usage

### Filter by Earnings Timing
```bash
# Find tickers with earnings in next 14 days
awk -F, '$3 <= 14 && $3 > 0 {print $1,$2,$3}' data/earnings_calendar.csv

# Find tickers with NO earnings in next 60 days
awk -F, '$3 > 60 || $3 == "" {print $1}' data/earnings_calendar.csv
```

### Automate Earnings Updates
```bash
# Add to crontab for daily updates
0 8 * * 1-5 cd /path/to/condor-hunter && python3 fetch_earnings_calendar.py AAPL MSFT TSLA NVDA AMD
```

### Custom Earnings Window
The app flags setups as "pre-earnings" if earnings is within **7 days** after expiration.

To customize, edit `condor_screener/analytics/analyzer.py`:

```python
def _is_pre_earnings(expiration: date, earnings_date: str | None) -> bool:
    # Change this threshold
    days_until_earnings = (earnings - expiration).days
    return 0 <= days_until_earnings <= 14  # Changed from 7 to 14 days
```

---

## 📊 Examples

### Example 1: Conservative Screening (No Earnings Risk)
```bash
# Fetch earnings
python3 fetch_earnings_calendar.py SPY IWM TLT GLD

# Screen
./run_app.sh
# Load SPY_options.csv
# Result: No earnings flag (ETFs don't have earnings)
# ✅ Safe to trade
```

### Example 2: Tech Stock with Earnings
```bash
# Fetch earnings
python3 fetch_earnings_calendar.py AAPL

# Output:
# AAPL      2026-02-05         45 days

# Fetch options
python3 fetch_tradier.py AAPL --sandbox

# Screen
./run_app.sh
# Load AAPL_options.csv
# UI shows: 📅 Earnings: 2026-02-05 (45 days)

# Results:
# Rank 1: Exp 2026-01-23, DTE 32 → ✅ Safe (before earnings)
# Rank 2: Exp 2026-02-06, DTE 46 → ⚠️ Earnings (1 day after earnings!)
# Rank 3: Exp 2026-02-13, DTE 53 → 📅 2026-02-05 (after earnings, safe)
```

### Example 3: Post-Earnings Opportunity
```bash
# Suppose TSLA reported earnings yesterday

# Check current IV vs historical
python3 fetch_tradier.py TSLA --sandbox

# Screen
./run_app.sh
# IV will be lower (post-earnings crush)
# Strikes are tighter (less expected move)
# Good opportunity for iron condors
```

---

## 🐛 Troubleshooting

### "No earnings data for TICKER"
**Causes:**
- Ticker is an ETF (SPY, QQQ, IWM don't have earnings)
- Ticker not in earnings_calendar.csv
- Earnings data not available from yfinance

**Solutions:**
- Check if ticker is an ETF (ETFs don't report earnings)
- Re-run fetch_earnings_calendar.py for that ticker
- Try manual entry in CSV

### "Could not load earnings calendar"
**Causes:**
- earnings_calendar.csv doesn't exist
- CSV has wrong format

**Solutions:**
- Run fetch_earnings_calendar.py to create it
- Check CSV format matches: symbol,earnings_date,days_until_earnings,source

### Earnings Date Shows But No Flag
**Explanation:**
- The setup is NOT flagged as "pre-earnings" because:
  - Earnings is MORE than 7 days after expiration
  - This is actually SAFE to trade

**Example:**
```
Expiration: 2026-01-23
Earnings:   2026-02-05
Gap: 13 days

Result: Shows "📅 2026-02-05" for info, but NO ⚠️ warning
```

---

## 📚 Files and Integration

### New Files
- `fetch_earnings_calendar.py` - Fetches earnings from yfinance or Tradier
- `data/earnings_calendar.csv` - Stores earnings dates (auto-generated)

### Updated Files
- `condor_screener/data/loaders.py` - Added `load_earnings_calendar()`
- `app.py` - Loads earnings and displays warnings
- `condor_screener/analytics/analyzer.py` - Already had earnings support

### Existing Files (Unchanged)
- `condor_screener/models/analytics.py` - Already had `is_pre_earnings` and `earnings_date` fields
- All screening logic (strategy.py, scorer.py, etc.) - No changes needed

---

## 🎯 Summary

✅ **What you can now do:**
- Fetch earnings calendars automatically with yfinance
- See earnings dates in the screener UI
- Get warnings for setups with earnings risk
- Identify post-earnings opportunities
- Avoid accidentally holding through earnings

✅ **Key Features:**
- **Automatic detection**: App auto-loads earnings_calendar.csv
- **Visual warnings**: ⚠️ flag for pre-earnings setups
- **Flexible**: Works with yfinance, Tradier, or manual CSV
- **Zero impact on existing code**: Calendar spread code is separate, no conflicts

---

**Use earnings events to find your edge!** 📅📈

The #1 risk factor for iron condors is surprise moves - and earnings are the most predictable source of volatility. Now you can see them coming.
