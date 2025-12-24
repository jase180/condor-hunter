# 🚀 Tradier Sandbox Setup - 2 Minute Guide

**Tradier Sandbox is the recommended data source** - Free, unlimited, no broker account needed.

---

## ⚡ Quick Setup (2 Minutes)

### Step 1: Sign Up (1 minute)
1. Go to https://developer.tradier.com/user/sign_up
2. Fill in:
   - Email
   - Password
   - First/Last Name
3. Click **Create Account**
4. Verify your email (check inbox)

**Note:** This is completely free. No credit card needed. No broker account needed.

---

### Step 2: Get API Token (30 seconds)
1. Log in to https://developer.tradier.com/
2. Click **Applications** in top menu
3. You'll see your default application
4. Copy the **Sandbox Access Token**

It looks like: `xXxXxXxXxXxXxXxXxXxXxX`

---

### Step 3: Set Environment Variable (30 seconds)

**Linux/Mac/WSL:**
```bash
# Add to your ~/.bashrc or ~/.zshrc
export TRADIER_SANDBOX_TOKEN="paste_your_token_here"

# Or just for this session
export TRADIER_SANDBOX_TOKEN="paste_your_token_here"
```

**Windows (PowerShell):**
```powershell
$env:TRADIER_SANDBOX_TOKEN = "paste_your_token_here"
```

**Windows (CMD):**
```cmd
set TRADIER_SANDBOX_TOKEN=paste_your_token_here
```

---

### Step 4: Fetch Data (10 seconds)
```bash
python3 fetch_tradier.py SPY --sandbox
```

**Output:**
```
🔗 Using Tradier API (sandbox)
📊 Fetching 1 ticker(s): SPY
📅 DTE range: 30-60 days

Fetching options for SPY...
Underlying price: $560.25
Found 48 total expirations
Filtered to 2 expirations in range 30-60 DTE:
  - 2025-01-25 (35 DTE)
  - 2025-02-01 (42 DTE)
Fetching option chain for 2025-01-25...
  Fetched 124 options
Fetching option chain for 2025-02-01...
  Fetched 118 options

✅ Successfully fetched 242 options for SPY
📁 Saved to: data/SPY_options.csv
```

---

### Step 5: Run Screener
```bash
./run_app.sh
```

Select `SPY_options.csv` and start screening!

---

## 🔁 Daily Workflow

Once set up, your daily routine is:

```bash
# Morning: Fetch fresh data
python3 fetch_tradier.py SPY QQQ IWM --sandbox

# Run screener
./run_app.sh

# Analyze and trade in your broker
```

**That's it!** Takes ~30 seconds each morning.

---

## 💡 Tips & Tricks

### Multiple Tickers at Once
```bash
# Fetch several tickers in one command
python3 fetch_tradier.py SPY QQQ IWM DIA --sandbox
```

### Custom DTE Range
```bash
# Weekly options (7-14 DTE)
python3 fetch_tradier.py SPY --sandbox --from-dte 7 --to-dte 14

# Monthly options (30-45 DTE)
python3 fetch_tradier.py SPY --sandbox --from-dte 30 --to-dte 45

# LEAPS (180-365 DTE)
python3 fetch_tradier.py SPY --sandbox --from-dte 180 --to-dte 365
```

### Pass API Key Directly (No Env Var)
```bash
python3 fetch_tradier.py SPY --sandbox --api-key YOUR_TOKEN
```

### Automate with Cron (Linux/Mac)
```bash
# Add to crontab for daily 9:00 AM fetch
crontab -e

# Add this line:
0 9 * * 1-5 cd /path/to/condor-hunter && /usr/bin/python3 fetch_tradier.py SPY QQQ --sandbox
```

---

## 🆚 Sandbox vs Production

| Feature | Sandbox (FREE) | Production (Requires Account) |
|---------|----------------|-------------------------------|
| Cost | Free | Requires Tradier brokerage account |
| Data Delay | 15 minutes | Real-time |
| API Calls | Unlimited | Unlimited |
| Greeks | Included | Included |
| Account Needed | No | Yes (Tradier brokerage) |
| Best For | Screening | Live trading |

**For screening iron condors:** Sandbox is perfect. The 15-minute delay doesn't matter because you verify setups in your real broker before trading anyway.

---

## ❓ Troubleshooting

### "API Error 401: Unauthorized"
- Check you copied the **Sandbox Access Token** (not Account Access Token)
- Verify the token is in your environment: `echo $TRADIER_SANDBOX_TOKEN`
- Make sure you're using `--sandbox` flag

### "No expirations found in DTE range"
- Widen your DTE range: `--from-dte 7 --to-dte 90`
- Check the ticker is correct and has options

### "Could not get quote"
- Check ticker symbol is correct (e.g., SPY not $SPY)
- Verify you have internet connection
- Try again (sometimes API has hiccups)

### Environment variable not persisting
**Linux/Mac:**
```bash
# Add to ~/.bashrc permanently
echo 'export TRADIER_SANDBOX_TOKEN="your_token"' >> ~/.bashrc
source ~/.bashrc
```

**Windows:**
Set it as a system environment variable through Control Panel

---

## 📊 What Data You Get

From Tradier sandbox, you get:
- ✅ All strikes for each expiration
- ✅ Bid/Ask/Last prices
- ✅ Volume and Open Interest
- ✅ Implied Volatility
- ✅ All Greeks (Delta, Gamma, Theta, Vega)
- ✅ Real market data (15-min delayed)

**Everything the screener needs!**

---

## 🔐 API Token Security

Your API token is like a password:
- ✅ **DO:** Keep it in environment variables
- ✅ **DO:** Use `.env` files (add to `.gitignore`)
- ❌ **DON'T:** Commit it to git
- ❌ **DON'T:** Share it publicly

**Sandbox tokens are low-risk** (they can't access brokerage accounts), but still keep them private.

---

## 🎯 Next Steps

1. ✅ Sign up at developer.tradier.com
2. ✅ Copy your Sandbox Access Token
3. ✅ Set `TRADIER_SANDBOX_TOKEN` environment variable
4. ✅ Run `python3 fetch_tradier.py SPY --sandbox`
5. ✅ Launch app: `./run_app.sh`
6. ✅ Start screening!

---

## 🆘 Support

- **Tradier Docs:** https://documentation.tradier.com/brokerage-api
- **API Reference:** https://documentation.tradier.com/brokerage-api/reference
- **Developer Forum:** https://developer.tradier.com/forum

---

**You're all set!** 🚀

The Tradier sandbox gives you professional-grade options data for free, with no limitations. Perfect for daily screening.
