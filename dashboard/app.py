import sys
import os
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, BASE_DIR)
import time
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from compute.apply_indicators import apply_indicators
from utils.data_loader import load_stock_data
from reporting.report_nifty_analysis import analyze_nifty

# --- Project Paths ---
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, BASE_DIR)

RAW_COMPANY_LIST = os.path.join(BASE_DIR, "data", "raw", "listed_companies.csv")
PROCESSED_STOCKS_DIR = os.path.join(BASE_DIR, "data", "processed", "stocks")
PROCESSED_INDEX_DIR = os.path.join(BASE_DIR, "data", "processed", "indexes")

# --- Streamlit Config ---
st.set_page_config(page_title="Tidder Dashboard", layout="wide")
st.title("📊 Tidder 2.0 — Live Stock Dashboard")

# --- Auto-refresh using built-in Streamlit ---
refresh_interval = 15  # seconds
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()

if time.time() - st.session_state.last_refresh > refresh_interval:
    st.session_state.last_refresh = time.time()
    st.experimental_rerun()

# --- Utility Functions ---
def list_available_symbols(company_list_path):
    if not os.path.exists(company_list_path):
        st.error(f"Company list CSV not found: {company_list_path}")
        return []
    df = pd.read_csv(company_list_path)
    if "symbol" not in df.columns:
        st.error("CSV missing 'symbol' column.")
        return []
    return df["symbol"].dropna().unique().tolist()

def show_stock_dashboard(symbol):
    try:
        df = load_stock_data(symbol, PROCESSED_STOCKS_DIR)
    except Exception as e:
        st.error(str(e))
        return

    st.subheader(f"📈 {symbol} Stock Dashboard")

    # Candlestick Chart with Supertrend
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df["date"], open=df["open"], high=df["high"],
        low=df["low"], close=df["close"], name="Price"
    ))
    if "Supertrend" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["date"], y=df["Supertrend"], mode="lines",
            name="Supertrend", line=dict(color="orange")
        ))
    fig.update_layout(title=f"{symbol} Price Chart", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    # RSI
    if "RSI" in df.columns:
        st.subheader("RSI")
        st.line_chart(df.set_index("date")["RSI"])

    # MACD
    if "MACD" in df.columns:
        st.subheader("MACD")
        st.line_chart(df.set_index("date")[["MACD", "MACD_Signal"]])

    # Confidence
    if "Confidence" in df.columns:
        st.metric("Confidence Score", f"{df['Confidence'].iloc[-1]:.2f}%")

# --- Sidebar: Select Stock ---
symbols = list_available_symbols(RAW_COMPANY_LIST)
selected_symbol = st.sidebar.selectbox("Select Stock", symbols)

# --- Tabs ---
tab1, tab2 = st.tabs(["📈 Stock View", "📊 NIFTY Summary"])

# ---
