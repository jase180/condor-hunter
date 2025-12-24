"""Streamlit GUI for Iron Condor Screener.

Run with: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date
from pathlib import Path
from typing import List

from condor_screener.data.loaders import load_options_from_csv, load_earnings_calendar
from condor_screener.data.validators import filter_options, FilterConfig
from condor_screener.builder.strategy import generate_iron_condors, StrategyConfig
from condor_screener.analytics.analyzer import analyze_iron_condor
from condor_screener.analytics.expected_move import calculate_expected_move
from condor_screener.scoring.scorer import rank_analytics, ScoringConfig
from condor_screener.models.analytics import Analytics

# Page config
st.set_page_config(
    page_title="Iron Condor Screener",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title
st.title("🦅 Iron Condor Screener")
st.markdown("*Screen, analyze, and rank iron condor candidates with ease*")

# Sidebar - Configuration
st.sidebar.header("⚙️ Configuration")

# File selection
st.sidebar.subheader("📁 Data Source")
data_method = st.sidebar.radio(
    "Select method:",
    ["Upload CSV", "Select from folder"]
)

csv_file = None
if data_method == "Upload CSV":
    uploaded_file = st.sidebar.file_uploader(
        "Upload options CSV",
        type=['csv'],
        help="CSV file with option chain data"
    )
    if uploaded_file:
        # Save temporarily
        temp_path = Path("/tmp") / uploaded_file.name
        with open(temp_path, 'wb') as f:
            f.write(uploaded_file.getbuffer())
        csv_file = temp_path
else:
    # Look for CSV files in current directory and data/ subdirectory
    csv_files = []
    for pattern in ["*.csv", "data/*.csv"]:
        csv_files.extend(list(Path(".").glob(pattern)))

    if csv_files:
        csv_names = [f.name for f in csv_files]
        selected = st.sidebar.selectbox("Select CSV file:", csv_names)
        csv_file = [f for f in csv_files if f.name == selected][0]
    else:
        st.sidebar.warning("No CSV files found in current directory or data/")

# Filter Configuration
st.sidebar.subheader("🔍 Filtering")
min_iv_rank = st.sidebar.slider(
    "Min IV Rank",
    min_value=0.0,
    max_value=100.0,
    value=30.0,
    step=5.0,
    help="Minimum implied volatility rank"
)

min_iv_percentile = st.sidebar.slider(
    "Min IV Percentile",
    min_value=0.0,
    max_value=100.0,
    value=30.0,
    step=5.0,
    help="Minimum implied volatility percentile"
)

# Strategy Configuration
st.sidebar.subheader("🎯 Strategy Parameters")

min_dte = st.sidebar.slider(
    "Min DTE",
    min_value=7,
    max_value=60,
    value=30,
    step=1,
    help="Minimum days to expiration"
)

max_dte = st.sidebar.slider(
    "Max DTE",
    min_value=7,
    max_value=90,
    value=45,
    step=1,
    help="Maximum days to expiration"
)

target_delta = st.sidebar.slider(
    "Target Delta",
    min_value=0.05,
    max_value=0.30,
    value=0.15,
    step=0.01,
    help="Target delta for short strikes"
)

delta_tolerance = st.sidebar.slider(
    "Delta Tolerance",
    min_value=0.01,
    max_value=0.10,
    value=0.05,
    step=0.01,
    help="Acceptable delta range around target"
)

wing_width = st.sidebar.slider(
    "Wing Width",
    min_value=3.0,
    max_value=10.0,
    value=5.0,
    step=1.0,
    help="Width of spreads in dollars"
)

# Scoring Configuration
st.sidebar.subheader("📊 Scoring Weights")

weight_ror = st.sidebar.slider("Return on Risk", 0.0, 1.0, 0.30, 0.05)
weight_pop = st.sidebar.slider("Probability of Profit", 0.0, 1.0, 0.25, 0.05)
weight_expected_move = st.sidebar.slider("Expected Move Cushion", 0.0, 1.0, 0.20, 0.05)
weight_liquidity = st.sidebar.slider("Liquidity", 0.0, 1.0, 0.15, 0.05)
weight_iv_rank = st.sidebar.slider("IV Rank", 0.0, 1.0, 0.10, 0.05)

# Main area
if csv_file and st.sidebar.button("🚀 Run Screening", type="primary"):

    with st.spinner("Loading options data..."):
        try:
            options = load_options_from_csv(str(csv_file))
            ticker = options[0].ticker if options else "UNKNOWN"
            st.success(f"✅ Loaded {len(options)} options for {ticker}")
        except Exception as e:
            st.error(f"❌ Error loading CSV: {e}")
            st.stop()

    # Load earnings calendar (optional)
    earnings_map = {}
    earnings_file = Path("data/earnings_calendar.csv")
    if earnings_file.exists():
        try:
            earnings_map = load_earnings_calendar(earnings_file)
            if ticker in earnings_map:
                earnings_info = earnings_map[ticker]
                st.info(f"📅 Earnings: {earnings_info['date']} ({earnings_info['days_until']} days)")
            else:
                st.info(f"ℹ️ No earnings data for {ticker}")
        except Exception as e:
            st.warning(f"⚠️ Could not load earnings calendar: {e}")

    # Filter options
    with st.spinner("Filtering options..."):
        filter_config = FilterConfig(
            min_iv_rank=min_iv_rank,
            min_iv_percentile=min_iv_percentile,
        )
        filtered = filter_options(options, filter_config)
        st.info(f"📋 {len(filtered)} options passed filters")

    if len(filtered) == 0:
        st.warning("No options passed filtering criteria. Try relaxing the filters.")
        st.stop()

    # Generate iron condors
    with st.spinner("Generating iron condor candidates..."):
        strategy_config = StrategyConfig(
            min_dte=min_dte,
            max_dte=max_dte,
            target_delta=target_delta,
            delta_tolerance=delta_tolerance,
            wing_width=wing_width,
        )
        candidates = list(generate_iron_condors(filtered, strategy_config))
        st.info(f"🎯 Generated {len(candidates)} iron condor candidates")

    if len(candidates) == 0:
        st.warning("No valid iron condors found. Try adjusting strategy parameters.")
        st.stop()

    # Analyze candidates
    with st.spinner("Analyzing candidates..."):
        # Get spot price from options
        spot_price = sum(opt.last for opt in filtered if opt.last) / len([opt for opt in filtered if opt.last])
        
        # Collect historical IVs for IV rank calculation
        historical_ivs = [opt.implied_vol for opt in options if opt.implied_vol > 0]
        
        # Simple realized volatility estimate (20-day)
        realized_vol_20d = 0.20  # Default 20% annualized
        
        # Get earnings date for this ticker
        earnings_date = None
        if ticker in earnings_map:
            earnings_date = earnings_map[ticker]['date']

        analytics_list: List[Analytics] = []
        for ic in candidates:
            analytics = analyze_iron_condor(
                iron_condor=ic,
                spot_price=spot_price,
                historical_ivs=historical_ivs,
                realized_vol_20d=realized_vol_20d,
                earnings_date=earnings_date,
                expected_move_method='straddle',
            )
            analytics_list.append(analytics)

    # Score and rank
    with st.spinner("Scoring and ranking..."):
        scoring_config = ScoringConfig(
            weight_return_on_risk=weight_ror,
            weight_pop=weight_pop,
            weight_expected_move_safety=weight_expected_move,
            weight_liquidity=weight_liquidity,
            weight_iv_rank=weight_iv_rank,
        )

        scored = [score_analytics(a, scoring_config) for a in analytics_list]
        ranked = rank_analytics(scored, scoring_config)

    st.success(f"✅ Screening complete! Found {len(ranked)} ranked candidates")

    # Display results table
    st.header("📊 Results")

    # Create DataFrame for display
    results_data = []
    for i, analytics in enumerate(ranked[:20]):  # Top 20
        ic = analytics.iron_condor
        # Earnings flag
        earnings_flag = ""
        if analytics.is_pre_earnings:
            earnings_flag = "⚠️ Earnings"
        elif analytics.earnings_date:
            earnings_flag = f"📅 {analytics.earnings_date}"
            
        results_data.append({
            'Rank': i + 1,
            'Score': f"{analytics.composite_score:.3f}" if analytics.composite_score else "N/A",
            'Expiration': ic.expiration.strftime('%Y-%m-%d'),
            'DTE': ic.short_put.dte,
            'Put Spread': f"{ic.long_put.strike:.0f}/{ic.short_put.strike:.0f}",
            'Call Spread': f"{ic.short_call.strike:.0f}/{ic.long_call.strike:.0f}",
            'Credit': f"${ic.net_credit:.2f}",
            'Max Profit': f"${ic.max_profit:.2f}",
            'Max Loss': f"${ic.max_loss:.2f}",
            'RoR': f"{ic.return_on_risk:.1f}%",
            'PoP': f"{analytics.probability_of_profit:.1f}%",
            'Earnings': earnings_flag,
        })

    df = pd.DataFrame(results_data)

    # Display interactive table
    st.dataframe(
        df,
        use_container_width=True,
        height=400,
        hide_index=True,
    )

    # P&L Diagram Section
    st.header("📈 Profit/Loss Diagram")

    # Select which condor to visualize
    if len(ranked) > 0:
        selected_rank = st.selectbox(
            "Select iron condor to visualize:",
            options=list(range(1, min(len(ranked) + 1, 21))),
            format_func=lambda x: f"Rank #{x} - Score: {ranked[x-1].composite_score:.3f if ranked[x-1].composite_score else 'N/A'}"
        )

        selected_analytics = ranked[selected_rank - 1]
        selected_ic = selected_analytics.iron_condor

        # Create P&L diagram
        def plot_profit_loss(ic, spot_price, expected_move):
            """Create profit/loss diagram for iron condor."""
            # Price range: ±30% from current spot
            price_min = spot_price * 0.70
            price_max = spot_price * 1.30
            prices = [price_min + (price_max - price_min) * i / 100 for i in range(101)]

            # Calculate P&L at each price
            profits = []
            for price in prices:
                if price <= ic.long_put.strike:
                    # Max loss on put side
                    profit = -ic.max_loss
                elif price <= ic.short_put.strike:
                    # Between long and short put
                    profit = ic.net_credit - (ic.short_put.strike - price)
                elif price <= ic.short_call.strike:
                    # Max profit zone
                    profit = ic.max_profit
                elif price <= ic.long_call.strike:
                    # Between short and long call
                    profit = ic.net_credit - (price - ic.short_call.strike)
                else:
                    # Max loss on call side
                    profit = -ic.max_loss

                profits.append(profit * 100)  # Convert to dollars

            # Create figure
            fig = go.Figure()

            # Add P&L line
            fig.add_trace(go.Scatter(
                x=prices,
                y=profits,
                mode='lines',
                name='P&L',
                line=dict(color='blue', width=3),
                fill='tozeroy',
                fillcolor='rgba(0, 100, 255, 0.1)',
            ))

            # Add zero line
            fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)

            # Add current price
            fig.add_vline(
                x=spot_price,
                line_dash="solid",
                line_color="green",
                annotation_text=f"Current: ${spot_price:.2f}",
                annotation_position="top"
            )

            # Add expected move range
            if expected_move:
                fig.add_vrect(
                    x0=spot_price - expected_move,
                    x1=spot_price + expected_move,
                    fillcolor="yellow",
                    opacity=0.1,
                    line_width=0,
                    annotation_text="Expected Move",
                    annotation_position="top left"
                )

            # Add breakevens
            fig.add_vline(
                x=ic.breakeven_lower,
                line_dash="dot",
                line_color="red",
                annotation_text=f"BE: ${ic.breakeven_lower:.2f}",
                annotation_position="bottom left"
            )
            fig.add_vline(
                x=ic.breakeven_upper,
                line_dash="dot",
                line_color="red",
                annotation_text=f"BE: ${ic.breakeven_upper:.2f}",
                annotation_position="bottom right"
            )

            # Add strike markers
            for strike, label in [
                (ic.long_put.strike, "LP"),
                (ic.short_put.strike, "SP"),
                (ic.short_call.strike, "SC"),
                (ic.long_call.strike, "LC"),
            ]:
                fig.add_vline(
                    x=strike,
                    line_dash="dash",
                    line_color="purple",
                    opacity=0.3,
                    annotation_text=label,
                    annotation_position="top"
                )

            # Layout
            fig.update_layout(
                title=f"Iron Condor P&L - {ic.ticker} {ic.expiration.strftime('%Y-%m-%d')}",
                xaxis_title="Underlying Price at Expiration",
                yaxis_title="Profit/Loss ($)",
                hovermode='x unified',
                height=500,
                showlegend=True,
            )

            return fig

        # Plot
        fig = plot_profit_loss(
            selected_ic,
            spot_price,
            expected_move_data.get('average', 0.0)
        )
        st.plotly_chart(fig, use_container_width=True)

        # Show detailed metrics for selected condor
        st.subheader("📋 Detailed Metrics")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Composite Score", f"{selected_analytics.composite_score:.3f}" if selected_analytics.composite_score else "N/A")
            st.metric("Max Profit", f"${selected_ic.max_profit * 100:.2f}")
            st.metric("Max Loss", f"${selected_ic.max_loss * 100:.2f}")

        with col2:
            st.metric("Return on Risk", f"{selected_ic.return_on_risk:.1f}%")
            st.metric("Probability of Profit", f"{selected_analytics.pop:.1f}%" if selected_analytics.pop else "N/A")
            st.metric("Days to Expiration", selected_ic.short_put.dte)

        with col3:
            st.metric("Net Credit", f"${selected_ic.net_credit:.2f}")
            st.metric("Breakeven Lower", f"${selected_ic.breakeven_lower:.2f}")
            st.metric("Breakeven Upper", f"${selected_ic.breakeven_upper:.2f}")

        with col4:
            st.metric("Wing Width", f"${selected_ic.put_side_width:.0f} / ${selected_ic.call_side_width:.0f}")
            st.metric("Distance to Shorts", f"{selected_analytics.avg_distance_to_short:.1f}%" if selected_analytics.avg_distance_to_short else "N/A")
            st.metric("Expected Move Safety", f"{selected_analytics.expected_move_safety:.1f}%" if selected_analytics.expected_move_safety else "N/A")

else:
    # Show welcome message
    st.info("👈 Configure screening parameters and upload a CSV file to get started")

    st.markdown("""
    ### How to use:

    1. **Upload data**: Upload an options chain CSV file or select from available files
    2. **Configure filters**: Set IV rank/percentile minimums to filter options
    3. **Set strategy**: Choose DTE range, target delta, and wing width
    4. **Adjust scoring**: Weight the factors that matter most to you
    5. **Run screening**: Click the "Run Screening" button
    6. **Analyze results**: Review ranked candidates and P&L diagrams

    ### CSV Format:

    Your CSV should include these columns:
    - `ticker`, `option_type`, `strike`, `expiration`
    - `bid`, `ask`, `last`, `volume`, `open_interest`
    - `implied_vol` (optional: `delta`, `gamma`, `theta`, `vega`)
    - Optional: `iv_rank`, `iv_percentile`

    ### Example data:
    See `data/` folder for sample CSV files.
    """)

    # Show example of expected CSV format
    st.subheader("📋 Example CSV Format")
    example_df = pd.DataFrame([
        {
            'ticker': 'SPY',
            'option_type': 'put',
            'strike': 545.0,
            'expiration': '2025-02-21',
            'bid': 2.90,
            'ask': 3.10,
            'last': 3.00,
            'volume': 200,
            'open_interest': 2000,
            'implied_vol': 0.24,
            'delta': -0.15,
        },
        {
            'ticker': 'SPY',
            'option_type': 'call',
            'strike': 575.0,
            'expiration': '2025-02-21',
            'bid': 2.90,
            'ask': 3.10,
            'last': 3.00,
            'volume': 200,
            'open_interest': 2000,
            'implied_vol': 0.24,
            'delta': 0.15,
        }
    ])
    st.dataframe(example_df, use_container_width=True)
