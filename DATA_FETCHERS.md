# 📊 Data Fetchers - Getting Options Data

This guide shows you how to get options data into the Iron Condor Screener.

## 🎯 Quick Start

### **Fastest: Use Sample Data (Testing)**
```bash
python3 generate_sample_data.py
# Creates: data/SPY_sample_options.csv
```
✅ Ready to test immediately
✅ No API keys needed
✅ Realistic data for development

---

## 🔄 Real Data Sources

### Option 1: Tradier Sandbox API (⭐ RECOMMENDED)

**Best for:** Everyone - Free unlimited data, no broker account needed

#### Setup (2 minutes)
1. Go to https://developer.tradier.com/user/sign_up
2. Sign up (completely free, no credit card)
3. Go to Applications dashboard
4. Copy your **Sandbox API Token**

#### Usage
```bash
# Export API key
export TRADIER_SANDBOX_TOKEN="your_sandbox_token"

# Fetch SPY options (30-60 DTE)
python3 fetch_tradier.py SPY --sandbox --from-dte 30 --to-dte 60

# Or pass API key directly
python3 fetch_tradier.py SPY --sandbox --api-key YOUR_TOKEN

# Multiple tickers at once
python3 fetch_tradier.py SPY QQQ IWM --sandbox
```

**Output:** `data/SPY_options.csv`, `data/QQQ_options.csv`, etc.

**Pros:**
- ✅ **100% Free** - No broker account needed
- ✅ **Unlimited API calls** - No rate limits
- ✅ **Real market data** - 15-minute delayed (perfect for screening)
- ✅ **Complete Greeks** - Delta, gamma, theta, vega included
- ✅ **Fast** - Fetches full chain in seconds
- ✅ **2-minute signup** - Easiest setup

**Cons:**
- ❌ 15-minute delay (but you verify in your broker before trading anyway)

**Note:** Sandbox is separate from production. You don't need a Tradier brokerage account!

---

### Option 2: TD Ameritrade API

**Best for:** Free unlimited data if you already have TD account

#### Setup (5 minutes)
1. Go to https://developer.tdameritrade.com/
2. Sign in with your TD Ameritrade credentials
3. Click "Create App"
4. Fill in:
   - App Name: Iron Condor Screener
   - Callback URL: https://localhost
   - Description: Options screening tool
5. Copy your **Consumer Key** (this is your API key)

#### Usage
```bash
# Export API key
export TD_API_KEY="your_consumer_key_here"

# Fetch SPY options (30-45 DTE)
python3 fetch_td_ameritrade.py SPY --from-dte 30 --to-dte 45

# Or pass API key directly
python3 fetch_td_ameritrade.py SPY --api-key YOUR_KEY
```

**Output:** `data/SPY_options.csv`

**Pros:**
- ✅ Free unlimited calls
- ✅ Real-time data
- ✅ Complete Greeks included
- ✅ No rate limits

**Cons:**
- ❌ Requires TD Ameritrade account
- ❌ 5-minute setup

---

### Option 2: Polygon.io API (Free Tier)

**Best for:** No broker account needed

#### Setup (2 minutes)
1. Go to https://polygon.io
2. Sign up (free tier available)
3. Dashboard → API Keys → Copy your key

#### Usage
```bash
# Export API key
export POLYGON_API_KEY="your_api_key_here"

# Fetch SPY options
python3 fetch_polygon.py SPY --from-dte 30 --to-dte 45

# Or pass API key directly
python3 fetch_polygon.py SPY --api-key YOUR_KEY
```

**Output:** `data/SPY_options.csv`

**Pros:**
- ✅ No broker account needed
- ✅ Real-time data
- ✅ Simple signup

**Cons:**
- ❌ Free tier: 5 calls/minute (slow)
- ❌ Takes several minutes per ticker
- ❌ Limited to 500 calls/month free

---

### Option 3: Manual Export + Converter

**Best for:** Already exporting from your broker

#### From thinkorswim
1. Open thinkorswim desktop
2. **Analyze** tab
3. Select ticker (e.g., SPY)
4. Right-click option chain → **Export to CSV**
5. Save file

```bash
# Convert to screener format
python3 convert_broker_export.py thinkorswim_export.csv --broker thinkorswim

# Or let it auto-detect
python3 convert_broker_export.py thinkorswim_export.csv --auto-detect
```

#### From Interactive Brokers (IBKR)
1. Trader Workstation → Option Chain
2. Select ticker
3. Export → CSV

```bash
python3 convert_broker_export.py ibkr_export.csv --broker ibkr
```

#### From Schwab
1. StreetSmart Edge → Options Chain
2. Export to Excel/CSV

```bash
python3 convert_broker_export.py schwab_export.csv --broker schwab
```

**Pros:**
- ✅ Works with any broker
- ✅ No API setup needed
- ✅ Familiar workflow

**Cons:**
- ❌ Manual process each time
- ❌ Not automated

---

## 📋 Data Requirements

Your CSV must include these columns (names can vary):

### Required
- `ticker` - Symbol (e.g., "SPY")
- `option_type` - "call" or "put"
- `strike` - Strike price
- `expiration` - Date (YYYY-MM-DD or MM/DD/YYYY)
- `bid` - Bid price
- `ask` - Ask price
- `last` - Last traded price
- `volume` - Trading volume
- `open_interest` - Open interest

### Optional (Recommended)
- `implied_vol` - Implied volatility (decimal, e.g., 0.25 = 25%)
- `delta`, `gamma`, `theta`, `vega` - Option Greeks
- `iv_rank`, `iv_percentile` - IV metrics

**Note:** Missing Greeks will be calculated using Black-Scholes.

---

## 🎯 Recommended Workflow

### For Active Trading (Daily Use)
**Use TD Ameritrade API** - One-time 5-minute setup, then:
```bash
# Morning routine - fetch fresh data
python3 fetch_td_ameritrade.py SPY --from-dte 30 --to-dte 45
python3 fetch_td_ameritrade.py QQQ --from-dte 30 --to-dte 45

# Run screener
./run_app.sh
```

### For Occasional Use
**Use Polygon.io** - Quick signup, use when needed:
```bash
python3 fetch_polygon.py SPY --api-key YOUR_KEY
./run_app.sh
```

### For Testing/Development
**Use Sample Data** - Instant testing:
```bash
python3 generate_sample_data.py
./run_app.sh
```

---

## 🔧 Troubleshooting

### "API Error 401: Unauthorized"
- Check your API key is correct
- For TD: Ensure you're using the **Consumer Key**, not Client ID

### "API Error 429: Rate Limit"
- **Polygon.io**: Free tier has 5 calls/minute
- Wait a minute and try again
- Consider upgrading or using TD API

### "Could not parse date"
- Check expiration date format
- Supported: YYYY-MM-DD, MM/DD/YYYY, YYYYMMDD
- Use converter script to normalize

### "No options passed filtering"
- Your CSV might be missing `iv_rank`/`iv_percentile`
- Lower IV thresholds in app sidebar
- Or add IV metrics to your data

---

## 💡 Tips

### Multiple Tickers
```bash
# Fetch multiple tickers
for ticker in SPY QQQ IWM; do
    python3 fetch_td_ameritrade.py $ticker
done
```

### Automation (Cron Job)
```bash
# Add to crontab for daily 9:00 AM fetch
0 9 * * 1-5 cd /path/to/condor-hunter && python3 fetch_td_ameritrade.py SPY
```

### Custom DTE Ranges
```bash
# Weekly options (7-14 days)
python3 fetch_td_ameritrade.py SPY --from-dte 7 --to-dte 14

# Quarterly options (60-90 days)
python3 fetch_td_ameritrade.py SPY --from-dte 60 --to-dte 90
```

---

## 📚 Next Steps

1. **Get data:** Choose one method above
2. **Run screener:** `./run_app.sh`
3. **Analyze:** Review ranked candidates
4. **Trade:** Execute best setups in your broker

---

## ⚙️ Dependencies

All fetchers require:
```bash
pip3 install requests
```

Or install everything:
```bash
pip3 install -r requirements.txt
```

---

## 🆘 Support

- **TD API Issues:** https://developer.tdameritrade.com/content/getting-started
- **Polygon.io Issues:** https://polygon.io/docs
- **Converter Issues:** Check CSV format matches broker mapping in script

---

**Happy screening!** 🦅📈
