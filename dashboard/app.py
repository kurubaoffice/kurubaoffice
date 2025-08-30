import os
import sys
import time
import pandas as pd
import streamlit as st
from plotly.subplots import make_subplots
import plotly.graph_objects as go
#npm run dev

#streamlit run dashboard/app.py
# --- Project Paths ---
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, BASE_DIR)

from compute.apply_indicators import apply_indicators
from utils.data_loader import load_stock_data
from reporting.report_nifty_analysis import analyze_nifty

RAW_COMPANY_LIST = os.path.join(BASE_DIR, "data", "raw", "listed_companies.csv")
PROCESSED_STOCKS_DIR = os.path.join(BASE_DIR, "data", "processed", "stocks")
PROCESSED_INDEX_DIR = os.path.join(BASE_DIR, "data", "processed", "indexes")

# --- Streamlit Config ---
st.set_page_config(page_title="Tidder Dashboard", layout="wide")
st.title("Live Stock Dashboard")

# --- Auto-refresh ---
REFRESH_SEC = 30
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()
if time.time() - st.session_state.last_refresh > REFRESH_SEC:
    st.session_state.last_refresh = time.time()
    st.rerun()

# --- Helpers ---
def list_available_symbols(company_list_path: str):
    if not os.path.exists(company_list_path):
        st.error(f"Company list CSV not found: {company_list_path}")
        return []
    df = pd.read_csv(company_list_path)
    if "symbol" not in df.columns:
        st.error("CSV missing 'symbol' column.")
        return []
    return df["symbol"].dropna().unique().tolist()

# Consistent plotting column names
RENAME_MAP = {
    "supertrend": "Supertrend",
    "ema_20": "EMA20",
    "ema_50": "EMA50",
    "ema_200": "EMA200",
    "bb_upper": "BB_Upper",
    "bb_middle": "BB_Middle",
    "bb_lower": "BB_Lower",
    "macd": "MACD",
    "macd_signal": "MACD_Signal",
    "macd_histogram": "MACD_Histogram",
    "atr_14": "ATR",
}

def show_stock_dashboard(symbol: str):
    # ----- Load & enrich -----
    try:
        df = load_stock_data(symbol, PROCESSED_STOCKS_DIR)
        if df is None or df.empty:
            st.warning(f"⚠️ No processed data found for {symbol}. Please run the pipeline.")
            return
        # ensure datetime
        df["date"] = pd.to_datetime(df["date"])
        df = apply_indicators(df)
        df.rename(columns=RENAME_MAP, inplace=True)
    except Exception as e:
        st.error(f"❌ Failed to load {symbol}: {e}")
        return

    st.subheader(f"📈 {symbol} Stock Dashboard")

    # ----- Date range controls -----
    min_date, max_date = df["date"].min(), df["date"].max()

    st.markdown("### 📅 Select Time Period")
    c1, c2, c3, c4, c5 = st.columns(5)
    quick = None
    if c1.button("1M"):
        quick = (max_date - pd.Timedelta(days=30), max_date)
    if c2.button("3M"):
        quick = (max_date - pd.Timedelta(days=90), max_date)
    if c3.button("6M"):
        quick = (max_date - pd.Timedelta(days=180), max_date)
    if c4.button("1Y"):
        quick = (max_date - pd.Timedelta(days=365), max_date)
    if c5.button("Max"):
        quick = (min_date, max_date)

    default_start = max_date - pd.Timedelta(days=90)
    s, e = st.slider(
        "Custom Date Range",
        min_value=min_date.to_pydatetime(),
        max_value=max_date.to_pydatetime(),
        value=(default_start.to_pydatetime(), max_date.to_pydatetime()),
        format="YYYY-MM-DD"
    )
    if quick:
        s, e = quick

    df = df[(df["date"] >= pd.to_datetime(s)) & (df["date"] <= pd.to_datetime(e))]

    # ----- Figure & subplots -----
    fig = make_subplots(
        rows=5, cols=1, shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.45, 0.12, 0.15, 0.16, 0.12],
        subplot_titles=("Price + Indicators", "Volume", "RSI", "MACD", "ATR")
    )

    # 1) Price: Candles + overlays
    fig.add_trace(go.Candlestick(
        x=df["date"], open=df["open"], high=df["high"],
        low=df["low"], close=df["close"], name="Price"
    ), row=1, col=1)

    if "Supertrend" in df.columns:
        fig.add_trace(go.Scatter(x=df["date"], y=df["Supertrend"],
                                 mode="lines", name="Supertrend"), row=1, col=1)

    for name in ("EMA20", "EMA50", "EMA200"):
        if name in df.columns:
            fig.add_trace(go.Scatter(x=df["date"], y=df[name],
                                     mode="lines", name=name), row=1, col=1)

    # Bollinger (fill between lower & upper)
    if {"BB_Lower", "BB_Upper"}.issubset(df.columns):
        fig.add_trace(go.Scatter(x=df["date"], y=df["BB_Lower"],
                                 name="BB Lower", line=dict(width=0),
                                 showlegend=False), row=1, col=1)
        fig.add_trace(go.Scatter(x=df["date"], y=df["BB_Upper"],
                                 name="BB Upper", line=dict(width=0),
                                 fill="tonexty", fillcolor="rgba(150,150,150,0.18)",
                                 showlegend=False), row=1, col=1)
        if "BB_Middle" in df.columns:
            fig.add_trace(go.Scatter(x=df["date"], y=df["BB_Middle"],
                                     name="BB Middle", line=dict(dash="dot")),
                          row=1, col=1)

    # 2) Volume
    if "volume" in df.columns:
        fig.add_trace(go.Bar(x=df["date"], y=df["volume"], name="Volume"),
                      row=2, col=1)

    # 3) RSI
    if "RSI" in df.columns:
        fig.add_trace(go.Scatter(x=df["date"], y=df["RSI"], name="RSI",
                                 mode="lines"), row=3, col=1)
        fig.add_hline(y=70, line_dash="dot", row=3, col=1)
        fig.add_hline(y=30, line_dash="dot", row=3, col=1)
        fig.update_yaxes(range=[0, 100], row=3, col=1)

    # 4) MACD
    if {"MACD", "MACD_Signal"}.issubset(df.columns):
        if "MACD_Histogram" in df.columns:
            fig.add_trace(go.Bar(x=df["date"], y=df["MACD_Histogram"],
                                 name="MACD Hist"), row=4, col=1)
        fig.add_trace(go.Scatter(x=df["date"], y=df["MACD"],
                                 name="MACD", mode="lines"), row=4, col=1)
        fig.add_trace(go.Scatter(x=df["date"], y=df["MACD_Signal"],
                                 name="MACD Signal", mode="lines"), row=4, col=1)
        fig.add_hline(y=0, line_dash="dot", row=4, col=1)

    # 5) ATR
    if "ATR" in df.columns:
        fig.add_trace(go.Scatter(x=df["date"], y=df["ATR"],
                                 name="ATR", mode="lines"), row=5, col=1)

    fig.update_layout(
        height=1200,
        showlegend=True,
        xaxis_rangeslider_visible=False,
        title=f"{symbol} with Indicators",
        template="plotly_white"
    )

    st.plotly_chart(fig, use_container_width=True)

# --- Sidebar: Select Stock ---
symbols = list_available_symbols(RAW_COMPANY_LIST)
selected_symbol = st.sidebar.selectbox("Select Stock", symbols, index=0)

# --- Tabs ---
tab1, tab2 = st.tabs(["📈 Stock View", "📊 NIFTY Summary"])

with tab1:
    if selected_symbol:
        st.write(f"👉 Selected stock: {selected_symbol}")
        show_stock_dashboard(selected_symbol)
    else:
        st.info("Please select a stock from the sidebar.")

with tab2:
    st.subheader("📊 NIFTY Summary")
    try:
        nifty_report = analyze_nifty(PROCESSED_INDEX_DIR, PROCESSED_STOCKS_DIR)
        st.write(nifty_report)
    except Exception as e:
        st.error(f"Error loading NIFTY summary: {e}")
