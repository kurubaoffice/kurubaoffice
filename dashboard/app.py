import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import pandas as pd
import streamlit as st
from compute.apply_indicators import apply_indicators
from utils import load_stock_data

import plotly.graph_objects as go

#streamlit run app.py
# --- Project paths ---

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
RAW_COMPANY_LIST = os.path.join(BASE_DIR, "data", "raw", "listed_companies.csv")
PROCESSED_STOCKS_DIR = os.path.join(BASE_DIR, "data", "processed", "stocks")
PROCESSED_INDEX_DIR = os.path.join(BASE_DIR, "data", "processed", "indexes")

# Add project root to sys.path
sys.path.insert(0, BASE_DIR)

from utils.data_loader import load_stock_data
from reporting.report_nifty_analysis import analyze_nifty


def list_available_symbols(company_list_path):
    """Read company list CSV and return list of stock symbols."""
    abs_path = os.path.abspath(company_list_path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"Company list CSV not found: {abs_path}")

    df = pd.read_csv(abs_path)
    print(df.columns)
    return df["symbol"].dropna().unique().tolist()
def show_stock_dashboard(symbol, data_dir):
    try:
        df = load_stock_data(symbol, data_dir)
    except Exception as e:
        st.error(str(e))
        return

    # If not enough data, show indicator table instead
    if df.empty or df.shape[0] < 10:
        st.warning(f"Not enough price data for {symbol}. Showing indicator values instead.")
        indicators_df = apply_indicators(symbol)  # from Tidder 2.0
        st.dataframe(indicators_df)
    else:
        date_col = "Date" if "Date" in df.columns else "date"
        st.line_chart(df.set_index(date_col)["Close"])

# --- Streamlit Config ---
st.set_page_config(page_title="Tidder Dashboard", layout="wide")
st.title("📊 Tidder 2.0 — Stock Dashboard")

# Tabs
tab1, tab2 = st.tabs(["📈 Stock View", "📊 NIFTY Summary"])

with tab1:
    # List symbols from company list CSV
    symbols = list_available_symbols(RAW_COMPANY_LIST)
    selected_symbol = st.sidebar.selectbox("Select Stock", symbols)

    if selected_symbol:
        try:
            # Load symbol-specific CSV from processed stocks folder
            df = load_stock_data(selected_symbol, PROCESSED_STOCKS_DIR)

            # Price Chart
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=df["date"], open=df["open"], high=df["high"], low=df["low"], close=df["close"],
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
            st.error(f"Data file for {selected_symbol} not found in {PROCESSED_STOCKS_DIR}")

with tab2:
    st.subheader("NIFTY Summary Report")
    try:
        nifty_report = analyze_nifty(output_mode="dict")
        st.json(nifty_report)
    except Exception as e:
        st.error(f"Error loading NIFTY report: {e}")
