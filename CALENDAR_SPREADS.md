# 📅 Calendar Spread Screener Guide

**Calendar spreads** (also called time spreads or horizontal spreads) are a volatility and time decay strategy.

---

## 🎯 What is a Calendar Spread?

A calendar spread involves:
- **Selling** a near-term option (short leg)
- **Buying** a longer-term option (long leg)
- **Same strike price** (typically ATM)
- **Same option type** (both calls OR both puts)

### Example:
```
Sell: SPY Jan 23 560 Call (30 DTE)  → Collect $8.50
Buy:  SPY Feb 20 560 Call (60 DTE)  → Pay $12.00
─────────────────────────────────────────────────
Net Debit: $3.50 per spread ($350 per contract)
```

---

## 💰 How Calendar Spreads Make Money

### 1. Time Decay (Theta)
- Short-term options decay **faster** than long-term options
- You sell the fast-decaying option and keep the slow-decaying option
- As time passes, the spread value increases

### 2. Volatility Expansion (Vega)
- Calendar spreads are **long vega** (benefit from IV increase)
- If IV rises after entry, long leg gains more value than short leg loses
- Great for earnings plays or event-driven setups

### 3. Price Stability
- **Max profit occurs when stock is at strike at short expiration**
- If price wanders far from strike, spread loses value
- Best when you expect low movement in the underlying

---

## 🚀 Quick Start

### Step 1: Fetch Data with All Expirations
```bash
# Fetch all available expirations (not just 30-60 DTE)
export TRADIER_SANDBOX_TOKEN="your_token"
python3 fetch_tradier.py SPY --sandbox --all-expirations
```

**Why `--all-expirations`?** Calendar spreads need multiple expirations (near-term and far-term), so you want all available dates.

### Step 2: Screen Calendar Spreads
```bash
# Screen call calendars (default)
python3 screen_calendars.py data/SPY_options.csv

# Screen put calendars
python3 screen_calendars.py data/SPY_options.csv --put

# Screen both calls and puts
python3 screen_calendars.py data/SPY_options.csv --both
```

### Step 3: Analyze Results
The screener will show:
- **Composite Score**: Overall quality (0-1, higher is better)
- **Return on Risk**: Estimated max profit / max loss
- **Theta Differential**: How much faster short leg decays
- **Vega Exposure**: Benefit from IV increase
- **Distance to Strike**: How far price is from the strike

---

## 📊 Example Output

```
================================================================================
  CALENDAR SPREAD SCREENER - SPY
  Type: CALL  |  Spot: $560.00
================================================================================

Top Calendar Spread Candidates:
Rank  Score   Strike    Short DTE   Long DTE    Debit     RoR       Theta Δ   Distance
------------------------------------------------------------------------------------
1     0.847   $560.00   28          56          $3.50     45.7%     8.25      0.0%
2     0.812   $555.00   28          56          $3.80     42.1%     7.90      0.9%
3     0.791   $565.00   35          63          $4.10     38.5%     7.15      0.9%

================================================================================

📋 Detailed Analysis - Top Candidate:
────────────────────────────────────────────────────────────────────────────

  CALL Calendar: Sell 2026-01-23 560.0 / Buy 2026-02-20 560.0 for $3.50 debit

  Composite Score:      0.847
  Return on Risk:       45.7%
  Probability of Profit: 61.2%

  Net Debit:            $3.50
  Max Profit (est):     $1.75
  Max Loss:             $3.50

  Theta Differential:   8.25
  Vega Exposure:        12.50
  Distance to Strike:   0.0%

  Breakeven Range:      $520.80 - $599.20

  Short Leg:
    CALL $560.0 exp 2026-01-23
    Bid: $8.25  Ask: $8.75
    Delta: 0.502  Theta: -12.45  Vega: 8.20

  Long Leg:
    CALL $560.0 exp 2026-02-20
    Bid: $11.50  Ask: $12.50
    Delta: 0.485  Theta: -4.20  Vega: 20.70

================================================================================
```

---

## 🎛️ Configuration Options

### Custom DTE Ranges
```bash
# Short leg: 20-30 DTE, Long leg: 50+ DTE, Min gap: 25 days
python3 screen_calendars.py data/SPY_options.csv \
    --min-short-dte 20 --max-short-dte 30 \
    --min-long-dte 50 --min-gap 25
```

### Custom Delta (Moneyness)
```bash
# ATM calendars (delta ~0.50) - most common
python3 screen_calendars.py data/SPY_options.csv --target-delta 0.50

# Slightly OTM calendars (delta ~0.40)
python3 screen_calendars.py data/SPY_options.csv --target-delta 0.40
```

### Limit Results
```bash
# Show top 5 only
python3 screen_calendars.py data/SPY_options.csv --max-results 5
```

---

## 📏 Interpreting the Metrics

### Composite Score (0-1)
- **> 0.80**: Excellent setup
- **0.70-0.80**: Good setup
- **0.60-0.70**: Acceptable
- **< 0.60**: Marginal

### Return on Risk (RoR)
- **> 50%**: Excellent
- **40-50%**: Good
- **30-40%**: Acceptable
- **< 30%**: Low

### Theta Differential
- Measures how much faster short leg decays vs long leg
- **> 10**: Strong decay advantage
- **5-10**: Good
- **< 5**: Weak

### Vega Exposure
- Positive vega = benefits from IV increase
- **> 15**: High vega (sensitive to IV changes)
- **10-15**: Moderate
- **< 10**: Low sensitivity

### Distance to Strike
- **0-2%**: Ideal (very close to ATM)
- **2-5%**: Acceptable
- **> 5%**: Far from ideal strike

---

## 💡 Calendar Spread Strategies

### 1. Standard ATM Calendar (Conservative)
```bash
python3 screen_calendars.py data/SPY_options.csv \
    --target-delta 0.50 \
    --min-short-dte 25 --max-short-dte 35
```
**When to use:**
- Expect low volatility
- Stock will stay near current price
- Want theta decay profit

### 2. Earnings Calendar (Aggressive)
```bash
# Before earnings: Sell weekly, buy monthly
python3 screen_calendars.py data/SPY_options.csv \
    --min-short-dte 7 --max-short-dte 14 \
    --min-long-dte 30 --min-gap 20
```
**When to use:**
- Earnings coming up
- Expect IV crush in short term
- Long-term IV stays elevated

### 3. Double Calendar
Run calendar screener twice:
- Once for calls
- Once for puts
- Enter both (synthetically creates an iron condor calendar)

---

## ⚠️ Risk Management

### Max Loss
- **Max loss = net debit paid**
- Occurs if stock moves far from strike by short expiration
- Example: Pay $3.50 debit → Max loss is $350 per contract

### Max Profit
- Max profit is **hard to calculate precisely** (depends on future IV)
- **Rule of thumb**: 40-60% return on debit is realistic
- Occurs when stock is exactly at strike at short expiration

### Managing the Trade

**Before Short Expiration:**
1. **If profitable (40%+ gain)**: Consider closing early
2. **If at max profit zone**: Take profits, don't get greedy
3. **If losing**: Consider closing or rolling short leg

**At Short Expiration:**
1. **If short expires worthless**: Great! You can now:
   - Sell another short leg (create new calendar)
   - Close the long leg and take profit
2. **If short is ITM**: You may get assigned, plan accordingly

---

## 📈 When to Use Calendars vs Iron Condors

| Scenario | Better Strategy |
|----------|-----------------|
| Expect low movement | Calendar |
| Expect moderate movement but directional uncertainty | Iron Condor |
| Expect IV to increase | Calendar (long vega) |
| Expect IV to decrease | Iron Condor (short vega) |
| Want defined max profit | Iron Condor |
| Want to benefit from time decay + vega | Calendar |
| Smaller capital requirement | Calendar (lower debit) |
| Wider profit range | Iron Condor |

---

## 🔄 Daily Workflow

```bash
# Monday morning: Fetch data with all expirations
python3 fetch_tradier.py SPY QQQ IWM --sandbox --all-expirations

# Screen for both calls and puts
python3 screen_calendars.py data/SPY_options.csv --both
python3 screen_calendars.py data/QQQ_options.csv --both
python3 screen_calendars.py data/IWM_options.csv --both

# Pick top candidates
# Verify in broker
# Execute trades
```

---

## 📚 Advanced Tips

### 1. Optimal DTE Gap
- **Sweet spot**: 3-4 weeks between expirations
- Too narrow (< 2 weeks): Low theta differential
- Too wide (> 6 weeks): Higher debit, lower RoR

### 2. Strike Selection
- **ATM (0.50 delta)**: Max theta, most common
- **Slightly OTM (0.40-0.45 delta)**: Lower cost, directional bias
- **Far OTM (< 0.30 delta)**: Not recommended for calendars

### 3. Combining with Technical Analysis
Calendar spreads work best when:
- Price near support/resistance
- Consolidation pattern
- After a big move (expect mean reversion)

### 4. Earnings Plays
- **3-5 days before earnings**: Enter calendar
- **Day after earnings**: IV crush hits short leg hard
- **Exit**: Close for profit or hold through short expiration

---

## 🐛 Troubleshooting

### "No calendar spreads found"
**Solutions:**
```bash
# Widen DTE ranges
--min-short-dte 15 --max-short-dte 45

# Reduce minimum gap
--min-gap 15

# Widen delta tolerance
# (This is hardcoded to 0.10, but you can edit calendar_spreads.py)
```

### "Need more expirations"
**Solution:**
```bash
# Make sure you fetched with --all-expirations
python3 fetch_tradier.py SPY --sandbox --all-expirations
```

### "Only finding far OTM calendars"
**Solution:**
```bash
# Use --target-delta to focus on ATM
--target-delta 0.50
```

---

## 📖 Additional Resources

### In This Repo
- `condor_screener/builder/calendar_spreads.py` - Calendar builder logic
- `condor_screener/analytics/calendar_analytics.py` - Analytics engine
- `screen_calendars.py` - CLI screener script

### Further Learning
- **Calendar Spread Mechanics**: Options playbook, tastytrade
- **IV and Vega**: Understand volatility impact on calendars
- **Earnings Strategies**: Using calendars around earnings

---

## ⚡ Quick Reference

```bash
# Fetch data for calendars
python3 fetch_tradier.py SPY --sandbox --all-expirations

# Screen calendars
python3 screen_calendars.py data/SPY_options.csv [--call|--put|--both]

# Custom parameters
--min-short-dte 20        # Min DTE for short leg
--max-short-dte 35        # Max DTE for short leg
--min-long-dte 45         # Min DTE for long leg
--min-gap 20              # Min days between expirations
--max-gap 40              # Max days between expirations
--target-delta 0.50       # Target delta (ATM)
--max-results 10          # Limit output
```

---

**Happy calendar spread hunting!** 📅📈
