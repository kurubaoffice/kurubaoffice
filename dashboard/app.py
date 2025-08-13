import sys
import os

import pandas as pd

# Add project root (parent of dashboard) to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import plotly.graph_objects as go

from utils.data_loader import list_available_symbols, load_stock_data
from reporting.report_nifty_analysis import analyze_nifty

# Paths
COMPANY_LIST_CSV = "../data/raw/listed_companies.csv"     # For dropdown list
STOCK_DATA_FOLDER = "../data/processed/stocks"           # Where OHLCV CSVs are stored


def list_available_symbols(company_list_path):
    """Read company list CSV and return list of stock symbols."""
    abs_path = os.path.abspath(company_list_path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"Company list CSV not found: {abs_path}")

    df = pd.read_csv(abs_path)
    return df["symbol"].dropna().unique().tolist()
COMPANY_LIST_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "listed_companies.csv")
symbols = list_available_symbols(COMPANY_LIST_CSV)

st.set_page_config(page_title="Tidder Dashboard", layout="wide")
st.title("📊 Tidder 2.0 — Stock Dashboard")

# Tabs
tab1, tab2 = st.tabs(["📈 Stock View", "📊 NIFTY Summary"])

with tab1:
    # List symbols from company list CSV
    symbols = list_available_symbols(COMPANY_LIST_CSV)
    selected_symbol = st.sidebar.selectbox("Select Stock", symbols)

    if selected_symbol:
        try:
            # Load symbol-specific CSV from data folder
            df = load_stock_data(selected_symbol, STOCK_DATA_FOLDER)

            # Price Chart
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=df["Date"], open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
                name="Price"
            ))

            if "Supertrend" in df.columns:
                fig.add_trace(go.Scatter(
                    x=df["Date"], y=df["Supertrend"], mode="lines", name="Supertrend",
                    line=dict(color="orange")
                ))

            fig.update_layout(title=f"{selected_symbol} Price Chart", xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

            # RSI
            if "RSI" in df.columns:
                st.subheader("RSI")
                st.line_chart(df.set_index("Date")["RSI"])

            # MACD
            if "MACD" in df.columns:
                st.subheader("MACD")
                st.line_chart(df.set_index("Date")[["MACD", "MACD_Signal"]])

            # Confidence
            if "Confidence" in df.columns:
                st.metric("Confidence Score", f"{df['Confidence'].iloc[-1]:.2f}%")

        except FileNotFoundError:
            st.error(f"Data file for {selected_symbol} not found in {STOCK_DATA_FOLDER}")

with tab2:
    st.subheader("NIFTY Summary Report")
    try:
        nifty_report = analyze_nifty(output_mode="dict")
        st.json(nifty_report)
    except Exception as e:
        st.error(f"Error loading NIFTY report: {e}")
