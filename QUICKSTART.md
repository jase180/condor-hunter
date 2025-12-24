# ⚡ Quick Start Guide - Iron Condor Screener

## 🚀 Get Running in 60 Seconds

### Step 1: Install Dependencies (if not already done)
```bash
pip3 install streamlit plotly
```

### Step 2: Generate Sample Data
```bash
python3 generate_sample_data.py
```

### Step 3: Launch the App
```bash
./run_app.sh
```

**Done!** The app opens at http://localhost:8501

---

## 📊 Using the App

### 1. Load Data
- Sidebar → **Select from folder** → Choose `SPY_sample_options.csv`

### 2. Configure Strategy
- **DTE Range**: 30-45 days
- **Target Delta**: 0.15 (15 delta)
- **Wing Width**: $5

### 3. Run Screening
- Click **🚀 Run Screening**
- Wait ~2 seconds

### 4. Analyze Results
- **Results Table**: Browse top 20 candidates
- **Select one**: Choose from dropdown to view P&L diagram
- **Review metrics**: Check score, RoR, PoP, breakevens

---

## 🎯 What to Look For

### Good Iron Condor Candidates
✅ **Score**: > 0.700
✅ **Return on Risk**: > 30%
✅ **Probability of Profit**: > 65%
✅ **Distance to Shorts**: > 8% from current price
✅ **Expected Move Safety**: > 100% (strikes outside expected move)

### Red Flags
❌ Score < 0.500
❌ RoR < 20%
❌ Distance < 5%
❌ Expected Move Safety < 80%

---

## 📈 P&L Diagram Guide

```
Profit
  ↑
  │     ╱‾‾‾‾‾╲
  │    ╱       ╲
──┼───╱─────────╲────→ Price
  │  ╱           ╲
  │ ╱             ╲
  ↓
Loss
```

**Key Markers:**
- **Green Line**: Current underlying price
- **Yellow Zone**: Expected move range (1 SD)
- **Red Dotted**: Breakeven points
- **Purple Dashed**: Strike prices (LP/SP/SC/LC)
- **Blue Curve**: Your P&L at expiration

**Ideal Setup:**
- Current price in middle of yellow zone
- Breakevens well outside yellow zone
- Symmetric profit curve

---

## 🔄 Getting Real Data

### Option A: Tradier Sandbox (⭐ RECOMMENDED - Free & Unlimited)
```bash
# One-time setup (2 mins): Get free sandbox token from developer.tradier.com
export TRADIER_SANDBOX_TOKEN="your_sandbox_token"
python3 fetch_tradier.py SPY --sandbox
./run_app.sh
```
**Why Tradier:**
- ✅ No broker account needed
- ✅ Unlimited API calls (no rate limits!)
- ✅ Real data (15-min delayed - fine for screening)
- ✅ Includes all Greeks
- ✅ Easiest setup

### Option B: TD Ameritrade (If You Have Account)
```bash
# One-time setup (5 mins): Get API key from developer.tdameritrade.com
export TD_API_KEY="your_key"
python3 fetch_td_ameritrade.py SPY
./run_app.sh
```

### Option C: Manual Export
```bash
# Export from thinkorswim/IBKR/Schwab/Fidelity
python3 convert_broker_export.py your_export.csv --auto-detect
./run_app.sh
```

See **DATA_FETCHERS.md** for detailed instructions.

---

## 🎛️ Tuning Your Strategy

### Conservative (High Win Rate)
- Target Delta: **0.10** (10 delta)
- Wing Width: **$7-10**
- Min DTE: **40-50 days**
- Scoring: Emphasize **Expected Move** and **PoP**

### Moderate (Balanced)
- Target Delta: **0.15** (15 delta) ← Default
- Wing Width: **$5**
- Min DTE: **30-45 days**
- Scoring: Balanced weights

### Aggressive (Higher Returns)
- Target Delta: **0.20-0.25** (20-25 delta)
- Wing Width: **$3-5**
- Min DTE: **20-30 days**
- Scoring: Emphasize **Return on Risk**

---

## 📁 Files You Need to Know

| File | Purpose |
|------|---------|
| `app.py` | Main Streamlit app |
| `run_app.sh` | Launch script |
| `generate_sample_data.py` | Create test data |
| `fetch_td_ameritrade.py` | Get real data (TD API) |
| `fetch_polygon.py` | Get real data (Polygon API) |
| `convert_broker_export.py` | Convert manual exports |
| `data/` | Your CSV files go here |

---

## 🐛 Common Issues

### "No CSV files found"
→ Run `python3 generate_sample_data.py` first

### "No options passed filtering"
→ Lower IV Rank/Percentile sliders in sidebar

### "No valid iron condors found"
→ Widen delta tolerance or expand DTE range

### App won't start
→ Check streamlit is installed: `pip3 install streamlit plotly`

---

## 💡 Pro Tips

1. **Start with sample data** to learn the app
2. **Experiment with scoring weights** to match your style
3. **Check P&L diagram** before trading anything
4. **Compare multiple expirations** for best setup
5. **Save screenshots** of good setups for your records

---

## 📚 Full Documentation

- **GUI_USAGE.md** - Complete app user guide
- **DATA_FETCHERS.md** - Getting real options data
- **CRITIQUE.md** - Technical deep dive
- **CRITICAL_WORK_COMPLETE.md** - Implementation details

---

## ⚡ That's It!

You now have a production-grade iron condor screener with:
- ✅ Interactive GUI
- ✅ Real options data (or realistic samples)
- ✅ Advanced analytics and scoring
- ✅ Beautiful P&L visualizations
- ✅ Portfolio risk management tools

**Start screening:**
```bash
./run_app.sh
```

**Happy trading!** 🦅📈
