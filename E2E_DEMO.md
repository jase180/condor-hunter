# 🎬 End-to-End Demo Workflow

**Complete walkthrough from data fetch to trade selection** - Copy/paste these commands and follow along!

---

## 🎯 What You'll Do

1. Fetch real market data from Tradier (SPY & QQQ)
2. Launch the screening app
3. Screen both tickers
4. Analyze top candidates
5. Pick a trade setup

**Time:** 5 minutes

---

## 📋 Prerequisites

```bash
# Check you have Tradier token set
echo $TRADIER_SANDBOX_TOKEN

# If empty, set it:
export TRADIER_SANDBOX_TOKEN="your_sandbox_token_here"
```

---

## 🚀 Step 1: Fetch Real Data (30 seconds)

### Command:
```bash
python3 fetch_tradier.py SPY QQQ --sandbox --from-dte 30 --to-dte 45
```

### Expected Output:
```
🔗 Using Tradier API (sandbox)
📊 Fetching 2 ticker(s): SPY, QQQ
📅 DTE range: 30-45 days

Fetching options for SPY...
Underlying price: $560.42
Found 48 total expirations
Filtered to 2 expirations in range 30-45 DTE:
  - 2026-01-23 (35 DTE)
  - 2026-01-30 (42 DTE)
Fetching option chain for 2026-01-23...
  Fetched 156 options
Fetching option chain for 2026-01-30...
  Fetched 162 options

✅ Successfully fetched 318 options for SPY
📁 Saved to: data/SPY_options.csv

Fetching options for QQQ...
Underlying price: $512.15
Found 48 total expirations
Filtered to 2 expirations in range 30-45 DTE:
  - 2026-01-23 (35 DTE)
  - 2026-01-30 (42 DTE)
Fetching option chain for 2026-01-23...
  Fetched 148 options
Fetching option chain for 2026-01-30...
  Fetched 154 options

✅ Successfully fetched 302 options for QQQ
📁 Saved to: data/QQQ_options.csv

✨ Done! You can now use these files with the screener app:
   ./run_app.sh
```

### What Just Happened:
- ✅ Connected to Tradier sandbox API
- ✅ Fetched 2 expirations for each ticker (35 DTE and 42 DTE)
- ✅ Got ~300 options per ticker (calls + puts, all strikes)
- ✅ Saved to CSV files in `data/` folder

### Verify Files Were Created:
```bash
ls -lh data/

# Expected output:
# -rw-r--r-- 1 user user 45K Dec 21 22:15 SPY_options.csv
# -rw-r--r-- 1 user user 42K Dec 21 22:15 QQQ_options.csv
# -rw-r--r-- 1 user user 14K Dec 21 21:41 SPY_sample_options.csv
```

### Quick Peek at Data:
```bash
head -5 data/SPY_options.csv

# Expected output:
# ticker,option_type,strike,expiration,bid,ask,last,volume,open_interest,implied_vol,delta,gamma,theta,vega
# SPY,put,475.0,2026-01-23,0.15,0.18,0.16,45,892,0.2455,-0.0145,0.00082,-8.42,0.065
# SPY,call,475.0,2026-01-23,85.50,86.25,85.88,156,2145,0.2455,0.9855,0.00082,-28.15,0.065
# ...
```

---

## 🎨 Step 2: Launch the App (5 seconds)

### Command:
```bash
./run_app.sh
```

### Expected Output (Terminal):
```
🦅 Starting Iron Condor Screener GUI...

The app will open in your browser at http://localhost:8501
Press Ctrl+C to stop the server

  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.1.100:8501
```

### What You'll See:
- ✅ Terminal shows "Streamlit is running"
- ✅ Browser automatically opens to http://localhost:8501
- ✅ App shows welcome screen with instructions

---

## 📊 Step 3: Screen SPY (2 minutes)

### In the App:

#### Left Sidebar:

**1. Data Source**
```
📁 Data Source
● Select from folder
[Dropdown] → Select: SPY_options.csv
```

**2. Filtering**
```
🔍 Filtering
Min IV Rank: 30.0         [====|--------]
Min IV Percentile: 30.0   [====|--------]
```

**3. Strategy Parameters**
```
🎯 Strategy Parameters
Min DTE: 30               [===========|--]
Max DTE: 45               [=============|]
Target Delta: 0.15        [======|-------]
Delta Tolerance: 0.05     [==|-----------]
Wing Width: 5.0           [=====|---------]
```

**4. Scoring Weights**
```
📊 Scoring Weights
Return on Risk: 0.30      [======|-------]
Probability of Profit: 0.25
Expected Move Cushion: 0.20
Liquidity: 0.15
IV Rank: 0.10
```

**5. Click the Button**
```
[🚀 Run Screening]  ← CLICK THIS
```

### Expected App Output:

**Progress Messages:**
```
⏳ Loading options data...
✅ Loaded 318 options for SPY

⏳ Filtering options...
📋 268 options passed filters

⏳ Generating iron condor candidates...
🎯 Generated 24 iron condor candidates

⏳ Analyzing candidates...
⏳ Scoring and ranking...

✅ Screening complete! Found 24 ranked candidates
```

### Results Table:
```
📊 Results

Rank | Score | Expiration | DTE | Put Spread  | Call Spread | Credit | Max Profit | Max Loss | RoR   | PoP  | Break Even        | Distance
-----|-------|------------|-----|-------------|-------------|--------|------------|----------|-------|------|-------------------|----------
  1  | 0.875 | 2026-01-23 | 35  | 540/545    | 575/580     | $4.25  | $425.00    | $75.00   | 566%  | 73%  | 536.25 - 578.75   | 8.5%
  2  | 0.842 | 2026-01-30 | 42  | 535/540    | 580/585     | $3.80  | $380.00    | $120.00  | 317%  | 69%  | 531.80 - 583.20   | 9.2%
  3  | 0.819 | 2026-01-23 | 35  | 545/550    | 570/575     | $4.50  | $450.00    | $50.00   | 900%  | 71%  | 541.50 - 573.50   | 7.8%
...
```

**Sortable!** Click any column header to sort.

---

## 📈 Step 4: Analyze Top Candidate

### Select a Condor to Visualize:

```
📈 Profit/Loss Diagram

Select iron condor to visualize:
[Dropdown] → Rank #1 - Score: 0.875
```

### P&L Diagram Shows:

**Visual Elements:**
- **Blue Curve** - Your profit/loss at expiration
- **Green Vertical Line** - Current SPY price ($560.42)
- **Yellow Shaded Zone** - Expected move range (±$25)
- **Red Dotted Lines** - Breakeven points ($536.25 and $578.75)
- **Purple Dashed Lines** - Your strikes:
  - LP (Long Put): $540
  - SP (Short Put): $545
  - SC (Short Call): $575
  - LC (Long Call): $580

**What Good Looks Like:**
- ✅ Current price (green) centered in max profit zone
- ✅ Yellow zone (expected move) well inside breakevens
- ✅ Symmetric butterfly shape
- ✅ Flat top = max profit zone

### Detailed Metrics Panel:

```
📋 Detailed Metrics

Composite Score    Max Profit        Max Loss
    0.875            $425.00          $75.00

Return on Risk     Probability       Days to Exp
    566%              73%               35

Net Credit         Breakeven Lower   Breakeven Upper
   $4.25              $536.25          $578.75

Wing Width         Distance          EM Safety
  $5 / $5            8.5%              112%
```

**Key Metrics:**
- **Score 0.875** = Excellent (>0.800 is strong)
- **RoR 566%** = $4.25 profit on $0.75 risk (very high)
- **PoP 73%** = 73% probability of profit
- **Distance 8.5%** = Shorts are 8.5% away from current price
- **EM Safety 112%** = Strikes are 12% beyond expected move

---

## 🎯 Step 5: Screen QQQ (Compare)

### In the App:

**1. Change Data Source**
```
📁 Data Source
[Dropdown] → Select: QQQ_options.csv
```

**2. Click Run Again**
```
[🚀 Run Screening]
```

### Expected QQQ Results:
```
✅ Loaded 302 options for QQQ
📋 255 options passed filters
🎯 Generated 18 iron condor candidates

📊 Results

Rank | Score | Expiration | DTE | Put Spread  | Call Spread | Credit | RoR   | PoP
-----|-------|------------|-----|-------------|-------------|--------|-------|------
  1  | 0.861 | 2026-01-23 | 35  | 495/500    | 525/530     | $3.90  | 481%  | 71%
  2  | 0.834 | 2026-01-30 | 42  | 490/495    | 530/535     | $3.50  | 355%  | 68%
...
```

---

## 🔍 Step 6: Decision Making

### Compare Your Top Candidates:

| Ticker | Rank | Score | Credit | RoR  | PoP | Distance | DTE |
|--------|------|-------|--------|------|-----|----------|-----|
| SPY    | #1   | 0.875 | $4.25  | 566% | 73% | 8.5%     | 35  |
| SPY    | #2   | 0.842 | $3.80  | 317% | 69% | 9.2%     | 42  |
| QQQ    | #1   | 0.861 | $3.90  | 481% | 71% | 8.2%     | 35  |

### Pick Your Trade:

**Let's say you pick SPY #1:**
- **Put spread:** Buy 540P / Sell 545P
- **Call spread:** Sell 575C / Buy 580C
- **Expiration:** 2026-01-23 (35 DTE)
- **Credit:** ~$4.25 per spread
- **Max profit:** $425 (per 1 contract)
- **Max loss:** $75 (per 1 contract)
- **Breakevens:** $536.25 - $578.75

---

## 💰 Step 7: Position Sizing (Optional)

### Calculate How Many Contracts:

**In Python (optional):**
```python
from condor_screener.risk.position_sizing import PositionSizer

# Your account value
account_value = 50000

# Your risk tolerance (2% of account)
risk_dollars = account_value * 0.02  # $1,000

# Max loss per contract = $75
contracts = int(risk_dollars / 75)

print(f"Trade {contracts} contracts")  # Trade 13 contracts
print(f"Max risk: ${contracts * 75}")  # Max risk: $975
print(f"Max profit: ${contracts * 425}")  # Max profit: $5,525
```

**Simple Math:**
- Account: $50,000
- Risk 2%: $1,000
- Max loss per contract: $75
- **Contracts:** 1000 / 75 = 13 contracts

---

## 📝 Step 8: Execute in Your Broker

### In Fidelity Active Trader Pro (or your broker):

**1. Verify Current Prices:**
- Check SPY is still around $560
- Verify option prices haven't changed much

**2. Build the Order:**
```
Order Type: Iron Condor
Underlying: SPY
Expiration: Jan 23, 2026

Buy to Open:  540 Put   (1 contract)
Sell to Open: 545 Put   (1 contract)
Sell to Open: 575 Call  (1 contract)
Buy to Open:  580 Call  (1 contract)

Quantity: 13 (or your calculated amount)
Order: Limit at $4.25 credit (or current mid)
```

**3. Review Order:**
- Max profit: $5,525 (if SPY stays 536-579)
- Max loss: $975 (if SPY goes below 536 or above 579)
- Margin required: ~$975
- Probability: ~73%

**4. Submit Order**

---

## 📊 What You Just Did

✅ Fetched real market data (SPY & QQQ) from Tradier
✅ Screened 600+ options across 2 tickers
✅ Generated 40+ iron condor candidates
✅ Ranked by 5-factor composite score
✅ Analyzed top candidates with P&L diagrams
✅ Compared different strikes and expirations
✅ Calculated position size based on risk
✅ Ready to execute in your broker

**Total time:** ~5 minutes

---

## 🔄 Daily Workflow (After First Setup)

```bash
# Morning routine (30 seconds)
python3 fetch_tradier.py SPY QQQ IWM --sandbox
./run_app.sh

# Screen, analyze, trade (5 minutes)
# Done!
```

---

## 🎛️ Experiment with Parameters

### More Conservative:
```
Target Delta: 0.10      (10 delta shorts)
Wing Width: $7
Min DTE: 40
Scoring: Increase "Expected Move Cushion" weight
```

### More Aggressive:
```
Target Delta: 0.20-0.25 (20-25 delta shorts)
Wing Width: $3
Min DTE: 25
Scoring: Increase "Return on Risk" weight
```

### High IV Only:
```
Min IV Rank: 50
Min IV Percentile: 50
```

---

## 📸 Expected Screenshots

### Main Interface:
```
┌─────────────────────────────────────────────────────────────────┐
│ 🦅 Iron Condor Screener                                         │
│ Iron condor screening with ease                                │
├──────────────┬──────────────────────────────────────────────────┤
│ ⚙️ Config    │ 📊 Results                                       │
│              │                                                  │
│ 📁 Data      │ [Table with 20 candidates]                       │
│ SPY ▼        │ Rank | Score | Strikes | Credit | RoR | PoP     │
│              │ ───────────────────────────────────────────────  │
│ 🔍 Filters   │  1   | 0.875 | 540/545 - 575/580 | $4.25 | ...  │
│ IV Rank: 30  │  2   | 0.842 | 535/540 - 580/585 | $3.80 | ...  │
│              │                                                  │
│ 🎯 Strategy  │ 📈 Profit/Loss Diagram                           │
│ DTE: 30-45   │                                                  │
│ Delta: 0.15  │ [Interactive P&L chart with green/yellow/red    │
│              │  markers showing current price, expected move,   │
│ 📊 Scoring   │  and breakevens overlaid on profit curve]       │
│ RoR: 30%     │                                                  │
│              │ 📋 Detailed Metrics                              │
│ [🚀 Run]     │ Score: 0.875  RoR: 566%  PoP: 73%               │
└──────────────┴──────────────────────────────────────────────────┘
```

---

## 🐛 Troubleshooting

### "No options passed filters"
```bash
# Lower IV thresholds in sidebar
Min IV Rank: 20 (instead of 30)
Min IV Percentile: 20 (instead of 30)
```

### "No iron condors found"
```bash
# Widen parameters
Delta Tolerance: 0.10 (instead of 0.05)
Max DTE: 60 (instead of 45)
```

### "API Error 401"
```bash
# Check token is set
echo $TRADIER_SANDBOX_TOKEN

# Re-export if needed
export TRADIER_SANDBOX_TOKEN="your_token"
```

---

## 💡 Pro Tips

1. **Compare Multiple DTE Ranges:**
   - Run once with 30-45 DTE
   - Run again with 45-60 DTE
   - Pick best overall setup

2. **Check Multiple Tickers:**
   - SPY, QQQ, IWM usually have good setups
   - Compare scores across tickers

3. **Verify Before Trading:**
   - Data is 15-min delayed (sandbox)
   - Always check current prices in your broker
   - Make sure IV hasn't spiked/dropped

4. **Use P&L Diagram:**
   - Visualize your actual risk
   - Check if current price is centered
   - Verify breakevens make sense

---

## 📚 Next Steps

**You're now ready to:**
- ✅ Screen daily for new setups
- ✅ Compare across multiple tickers
- ✅ Experiment with parameters
- ✅ Track your trades

**Want more?**
- Portfolio tracking: Track open positions
- Position sizing: Kelly Criterion calculator
- Risk management: Portfolio Greeks aggregation

See `GUI_USAGE.md` for advanced features!

---

**Happy screening!** 🦅📈
