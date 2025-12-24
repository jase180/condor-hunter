# 🦅 Iron Condor Screener - GUI Usage

## Quick Start

### 1. Install GUI Dependencies

```bash
pip3 install streamlit plotly
```

Or install all dependencies:
```bash
pip3 install -r requirements.txt
```

### 2. Run the Streamlit App

```bash
streamlit run app.py
```

This will:
- Start a local web server
- Automatically open your browser to `http://localhost:8501`
- Show the Iron Condor Screener interface

### 3. Using the App

#### Left Sidebar - Configuration

**📁 Data Source**
- **Upload CSV**: Upload an options chain CSV file
- **Select from folder**: Choose from CSV files in current directory or `data/` folder

**🔍 Filtering**
- **Min IV Rank**: Filter options by implied volatility rank (0-100)
- **Min IV Percentile**: Filter options by IV percentile (0-100)

**🎯 Strategy Parameters**
- **Min/Max DTE**: Days to expiration range (e.g., 30-45 days)
- **Target Delta**: Desired delta for short strikes (e.g., 0.15 = 15 delta)
- **Delta Tolerance**: Acceptable range around target delta
- **Wing Width**: Width of spreads in dollars (e.g., $5 wide)

**📊 Scoring Weights**
Adjust how much each factor contributes to the composite score:
- **Return on Risk**: Higher RoR = better profit potential
- **Probability of Profit**: Higher PoP = safer trade
- **Expected Move Cushion**: More distance from expected move = safer
- **Liquidity**: Tighter bid/ask spreads and higher volume
- **IV Rank**: Higher IV = better premium collection

#### Main Area - Results

**📊 Results Table**
- Shows top 20 ranked iron condor candidates
- Sortable by any column (click column header)
- Shows: strikes, credit, max profit/loss, RoR, PoP, breakevens

**📈 Profit/Loss Diagram**
- Interactive chart showing P&L at expiration
- **Green line**: Current underlying price
- **Yellow zone**: Expected move range
- **Red dotted lines**: Breakeven points
- **Purple dashed lines**: Strike prices (LP/SP/SC/LC)
- **Blue curve**: Profit/loss at each price

**📋 Detailed Metrics**
- Complete breakdown of selected iron condor
- Shows all key metrics in organized layout

## CSV Format Requirements

Your CSV file must include these columns:

### Required Columns
- `ticker` - Stock/ETF symbol (e.g., "SPY")
- `option_type` - "call" or "put"
- `strike` - Strike price (e.g., 550.0)
- `expiration` - Expiration date (YYYY-MM-DD or MM/DD/YYYY)
- `bid` - Bid price
- `ask` - Ask price
- `last` - Last traded price
- `volume` - Trading volume
- `open_interest` - Open interest
- `implied_vol` - Implied volatility (e.g., 0.25 = 25%)

### Optional Columns (Recommended)
- `delta` - Option delta
- `gamma` - Option gamma
- `theta` - Option theta
- `vega` - Option vega
- `iv_rank` - IV rank (0-100)
- `iv_percentile` - IV percentile (0-100)

**Note**: If Greeks are missing, the screener will calculate them using Black-Scholes.

## Example Workflow

1. **Start the app**: `streamlit run app.py`

2. **Load data**:
   - Upload your options CSV or select from `data/` folder

3. **Configure strategy**:
   - Set DTE range: 30-45 days
   - Target delta: 0.15 (15 delta)
   - Wing width: $5

4. **Adjust filters**:
   - Min IV Rank: 30
   - Min IV Percentile: 30

5. **Tune scoring**:
   - Emphasize RoR if you want aggressive trades
   - Emphasize PoP/Expected Move for conservative trades

6. **Run screening**:
   - Click "🚀 Run Screening"
   - Wait for results (usually < 5 seconds)

7. **Analyze results**:
   - Browse ranked candidates in table
   - Select one to view P&L diagram
   - Review detailed metrics

8. **Export or trade**:
   - Note down the strikes and parameters
   - Verify in your trading platform
   - Execute the trade

## Tips

### Getting Good Results

**High IV Environment** (VIX > 20):
- Use higher IV rank threshold (40+)
- Can be more aggressive with delta (0.20)
- Favor shorter DTE (30-35 days)

**Low IV Environment** (VIX < 15):
- Lower IV rank threshold acceptable (25+)
- Be more conservative with delta (0.10-0.12)
- Consider longer DTE (45-60 days)

**Conservative Strategy**:
- Target delta: 0.10-0.12
- Emphasize Expected Move Cushion weight
- Wider wings ($7-10)

**Aggressive Strategy**:
- Target delta: 0.18-0.25
- Emphasize Return on Risk weight
- Narrower wings ($3-5)

### Keyboard Shortcuts (Streamlit)

- `Ctrl+R` or `Cmd+R` - Rerun the app
- `C` - Clear cache
- `?` - Show keyboard shortcuts

### Performance Tips

- Limit CSV to 1-2 expirations for faster screening
- Start with tighter filters to reduce candidates
- Reduce delta tolerance for fewer combinations

## Troubleshooting

### "No options passed filtering"
- Lower your IV rank/percentile thresholds
- Check that your CSV has `iv_rank` and `iv_percentile` columns

### "No valid iron condors found"
- Widen delta tolerance
- Expand DTE range
- Check that you have both calls and puts in CSV

### "Error loading CSV"
- Verify CSV format matches requirements
- Check date format (YYYY-MM-DD or MM/DD/YYYY)
- Ensure `option_type` is exactly "call" or "put" (lowercase)

### App is slow
- Reduce number of options in CSV (filter to 1-2 expirations)
- Use tighter filtering criteria
- Close and restart the app

## Advanced Usage

### Running on Remote Server

```bash
# SSH into server
ssh user@your-server

# Start Streamlit with network access
streamlit run app.py --server.address 0.0.0.0 --server.port 8501

# Access from your local machine
# Open browser to: http://your-server:8501
```

### Custom Port

```bash
streamlit run app.py --server.port 8080
```

### Dark Theme

Streamlit will use your system theme by default. To force dark mode:

Settings (top right) → Theme → Dark

## Sample Data

Sample CSV files are available in the `data/` directory (if present).

To create your own CSV:
1. Export options chain from your broker (TDA, IBKR, etc.)
2. Ensure column names match requirements
3. Save as CSV
4. Upload to the app

## Support

For issues or questions:
- Check CRITIQUE.md for known limitations
- Review test files in `condor_screener/tests/` for examples
- Open an issue on GitHub

---

**Happy screening!** 🦅📈
