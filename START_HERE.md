# 🚀 START HERE - Complete Beginner's Guide

**Confused by all the features? This is your starting point.**

---

## 🎯 What This Tool Does

Screens thousands of option combinations to find the best iron condor trades.

**Iron Condor** = Sell 2 options, buy 2 options for protection. Collect premium. Profit if stock stays in range.

---

## ⚡ Quick Start (3 Steps)

### Step 1: Install
```bash
pip install -r requirements.txt
```

### Step 2: Generate Test Data
```bash
python3 generate_sample_data.py
```

### Step 3: Launch GUI
```bash
./run_app.sh
```

Browser opens → Click `🚀 Run Screening` → See results!

**You just screened your first iron condors.**

---

## 📊 Using Real Data

### Get Tradier API Key (Free, 2 minutes)
1. Go to: https://developer.tradier.com/user/sign_up
2. Sign up (no credit card needed)
3. Copy your **Sandbox Access Token**
4. Set it:
```bash
export TRADIER_SANDBOX_TOKEN="paste_your_token_here"
```

### Fetch Real Options Data
```bash
# Fetch SPY options (30-45 days out)
python3 fetch_tradier.py SPY --sandbox

# Or multiple tickers
python3 fetch_tradier.py SPY QQQ IWM --sandbox
```

### Screen The Data
```bash
./run_app.sh
```
Select `SPY_options.csv` → Click `🚀 Run Screening`

---

## 🎨 Understanding the GUI

When you open the GUI (http://localhost:8501):

### Left Sidebar = Configuration

**📁 Data Source**
- Which CSV file to screen

**🔍 Filtering** (Usually leave defaults)
- Min IV Rank: 30
- Min IV Percentile: 30

**🎯 Strategy** (Adjust these)
- **DTE Range**: 30-45 days (how far out options expire)
- **Target Delta**: 0.15 (15 delta = ~15% chance of being ITM)
- **Wing Width**: $5 (spread width)

**📊 Scoring** (Usually leave defaults)
- Weights for ranking candidates

### Main Area = Results

**Top Table** - Your candidates ranked best to worst
- Rank 1 = Best setup
- Score closer to 1.0 = Better
- Click any row to see details

**Bottom** - P&L Diagram
- Shows profit/loss at expiration
- Green line = Current stock price
- Yellow zone = Expected move
- Want price in middle, expected move inside breakevens

---

## 💰 Example Workflow

### Monday Morning
```bash
# 1. Fetch fresh data
python3 fetch_tradier.py SPY QQQ IWM --sandbox

# 2. Launch screener
./run_app.sh
```

### Screen SPY
1. Select `SPY_options.csv`
2. Click `🚀 Run Screening`
3. Wait 2-3 seconds
4. View top 20 candidates

### Pick a Trade
Looking at Rank #1:
```
Score: 0.875 (excellent)
Expiration: 2026-01-23 (35 DTE)
Put Spread: 540/545
Call Spread: 575/580
Credit: $4.25
Max Profit: $425
Max Loss: $75
RoR: 566% (Return on Risk)
PoP: 73% (Probability of Profit)
```

**Read this as:**
- Sell 545 put, buy 540 put (protection)
- Sell 575 call, buy 580 call (protection)
- Collect $4.25 per spread ($425 per contract)
- Risk $0.75 per spread ($75 per contract)
- Make max profit if SPY stays between 536-579

### Verify on P&L Diagram
1. Select "Rank #1" from dropdown
2. See the butterfly-shaped profit curve
3. Check:
   - ✅ Green line (current price) in middle
   - ✅ Yellow zone (expected move) inside breakevens
   - ✅ Symmetric shape

### Execute in Your Broker
Open Fidelity/Schwab/TastyTrade/etc:
```
Strategy: Iron Condor
Underlying: SPY
Expiration: Jan 23, 2026

Buy to Open:  540 Put  (1 contract)
Sell to Open: 545 Put  (1 contract)
Sell to Open: 575 Call (1 contract)
Buy to Open:  580 Call (1 contract)

Quantity: 1 (or more based on account size)
Order Type: Limit
Price: $4.25 credit (or current mid price)
```

---

## 📅 Adding Earnings Detection (Optional)

Want to avoid holding through earnings?

### Install yfinance
```bash
pip install yfinance
```

### Fetch Earnings Calendar
```bash
python3 fetch_earnings_calendar.py AAPL MSFT TSLA NVDA
```

This creates `data/earnings_calendar.csv`

### Now When You Screen
The GUI will show:
- **At top**: "📅 Earnings: 2026-02-05 (45 days)"
- **In results**: "⚠️ Earnings" if risky, "📅 Date" if safe

**⚠️ Earnings Flag** = Expires right before/after earnings (avoid!)
**📅 Date** = Earnings exist but not risky (trade normally)

---

## 🎛️ Adjusting Strategy

### Conservative (Higher Win Rate)
In sidebar:
- Target Delta: **0.10** (10 delta)
- Wing Width: **$7**
- DTE: **40-50** days

### Aggressive (Higher Returns)
In sidebar:
- Target Delta: **0.20** (20 delta)
- Wing Width: **$3**
- DTE: **20-30** days

---

## 📋 Files You Need to Know

### Use These Daily
```
fetch_tradier.py       → Get options data
run_app.sh             → Launch GUI
```

### Optional
```
fetch_earnings_calendar.py  → Get earnings dates
generate_sample_data.py     → Create test data
```

### Don't Touch
```
condor_screener/     → Core engine (219 tests)
app.py              → GUI code
```

---

## ❓ Common Questions

### "What ticker should I screen?"
Start with liquid ETFs: SPY, QQQ, IWM

### "What's a good score?"
- **> 0.80**: Excellent, trade these
- **0.70-0.80**: Good
- **0.60-0.70**: Marginal
- **< 0.60**: Pass

### "How many contracts should I sell?"
Rule of thumb: Risk 2% of account per trade
```
Account: $50,000
Risk 2%: $1,000
Max loss per contract: $75
Contracts: 1000 / 75 = 13 contracts
```

### "When should I close?"
- **50% max profit**: Take it (common strategy)
- **21 days to expiration**: Close regardless
- **Earnings coming**: Exit before
- **Price near strike**: Manage/adjust

### "Can I screen individual stocks?"
Yes! But add earnings calendar:
```bash
python3 fetch_earnings_calendar.py AAPL
python3 fetch_tradier.py AAPL --sandbox
./run_app.sh
```
Watch for ⚠️ earnings flags!

---

## 🚨 Troubleshooting

### "No CSV files found"
```bash
python3 generate_sample_data.py
```

### "No iron condors found"
Lower the filters:
- Min IV Rank: 20 (was 30)
- Delta Tolerance: 0.10 (was 0.05)

### "API Error 401"
```bash
# Check token
echo $TRADIER_SANDBOX_TOKEN

# Set if empty
export TRADIER_SANDBOX_TOKEN="your_token"
```

### "Module not found"
```bash
pip install -r requirements.txt
```

---

## 🎓 3-Day Learning Plan

### Day 1: Learn the Tool
1. Generate sample data
2. Launch GUI
3. Run screening
4. Look at results table
5. View P&L diagrams
6. Don't trade yet!

### Day 2: Real Data
1. Get Tradier API key
2. Fetch SPY data
3. Screen it
4. Compare to sample
5. Still don't trade!

### Day 3: Paper Trade
1. Find good setup in screener
2. Write down the trade
3. Track it in spreadsheet
4. See if it would have worked
5. Repeat for a week

### Week 2: Real Money
1. Start with 1 contract
2. Use proven screener setups
3. Close at 50% profit
4. Build confidence

---

## 🎯 The 3 Core Commands

Memorize these:

```bash
# 1. Get data
python3 fetch_tradier.py SPY --sandbox

# 2. Screen it
./run_app.sh

# 3. Pick best setup from results table
```

Everything else is optional.

---

## 📚 Documentation Guide

Overwhelmed by .md files? Here's what to read:

1. **START_HERE.md** ← You are here (read this first)
2. **TRADIER_SETUP.md** ← If API key doesn't work
3. **EARNINGS_INTEGRATION.md** ← When you want earnings
4. **README.md** ← Project overview

Ignore the rest until you need them.

---

## ✅ Checklist: Ready to Trade?

Before real money:

- [ ] Generated sample data successfully
- [ ] Ran GUI and saw results
- [ ] Understand P&L diagram basics
- [ ] Got Tradier API key
- [ ] Fetched real data for SPY
- [ ] Screened real data
- [ ] Found setup with score > 0.75
- [ ] Checked P&L diagram looks good
- [ ] Verified in your broker before executing
- [ ] Paper traded for at least 1 week

---

## 💡 Pro Tips

1. **Start with SPY** - Most liquid, easiest to fill
2. **Check earnings** - Always run earnings calendar for stocks
3. **Verify prices** - Data is 15-min delayed, check broker before trading
4. **Take profits early** - 50% of max profit is a win
5. **Don't get greedy** - Close before expiration
6. **Size properly** - Risk 1-2% per trade max

---

## 🎬 Your First Real Trade

### Complete Walkthrough

**Monday 9:35 AM:**
```bash
export TRADIER_SANDBOX_TOKEN="your_token"
python3 fetch_tradier.py SPY --sandbox
./run_app.sh
```

**In GUI:**
1. Select `SPY_options.csv`
2. Leave defaults
3. Click `🚀 Run Screening`

**Analyze Rank #1:**
- Score: 0.875 ✅
- RoR: 566% ✅
- PoP: 73% ✅
- No earnings flag ✅
- DTE: 35 days ✅

**View P&L:**
- Current price centered ✅
- Expected move inside breakevens ✅
- Symmetric shape ✅

**Verify in Broker:**
- SPY currently: $560.00 ✅
- 545 put bid: $2.00 ✅
- 575 call bid: $2.25 ✅
- Total credit: ~$4.25 ✅

**Execute:**
```
Iron Condor on SPY Jan 23, 2026
Buy 540 put
Sell 545 put
Sell 575 call
Buy 580 call
Quantity: 1 contract
Limit price: $4.25 credit
```

**Confirm order** → **Done!**

---

**You're ready to screen iron condors like a pro!** 🦅

Questions? Read TRADIER_SETUP.md or EARNINGS_INTEGRATION.md for specific issues.
