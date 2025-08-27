"""
backtest/ziplime_runner.py

Ziplime-based backtesting integration for Tidder 2.0
---------------------------------------------------
- Loads NSE stock/index data from stored CSVs
- Registers custom Ziplime bundles for backtest
- Runs strategy logic (Tidder 2.0 indicators)
- Produces performance reports (PnL, Sharpe ratio, etc.)
"""

import os
import pandas as pd
from ziplime.api import run_algorithm
from ziplime.data.bundles import register_bundle

# --- 1. Register custom NSE bundle (reads from your CSVs) ---
def nse_csv_bundle(environ, asset_db_writer, minute_bar_writer,
                   daily_bar_writer, adjustment_writer, calendar,
                   start_session, end_session, cache, show_progress, output_dir):
    data_dir = "data/processed/stocks"
    files = [f for f in os.listdir(data_dir) if f.endswith(".csv")]

    assets = []
    for f in files:
        symbol = f.replace(".csv", "").upper()
        df = pd.read_csv(os.path.join(data_dir, f), parse_dates=["Date"])
        df = df.rename(columns={
            "Date": "date", "Open": "open", "High": "high",
            "Low": "low", "Close": "close", "Volume": "volume"
        })
        df.set_index("date", inplace=True)
        assets.append((symbol, df))

    daily_bar_writer.write(assets)

register_bundle("nse_csv", nse_csv_bundle)

# --- 2. Example Strategy Wrapper ---
def initialize(context):
    # Example: Pick a single stock (extendable later)
    context.asset = "RELIANCE"  # placeholder
    context.lookback = 14

def handle_data(context, data):
    # Placeholder for your Tidder 2.0 indicators
    # e.g., RSI/MACD from compute/apply_indicators
    price = data.current(context.asset, "price")
    # TODO: call your indicator functions here

    # Example: Buy if price > 2000
    if price > 2000:
        context.order_target_percent(context.asset, 1.0)
    else:
        context.order_target_percent(context.asset, 0.0)

# --- 3. Run Backtest ---
def run_backtest(symbol="RELIANCE", start="2021-01-01", end="2023-01-01", capital=100000):
    import pandas as pd

    result = run_algorithm(
        start=pd.Timestamp(start, tz="utc"),
        end=pd.Timestamp(end, tz="utc"),
        initialize=initialize,
        handle_data=handle_data,
        capital_base=capital,
        data_frequency="1d",
        bundle="nse_csv"
    )
    return result

# --- 4. Utility for Report ---
def generate_report(result):
    summary = {
        "Total Return": result["portfolio_value"].iloc[-1] / result["portfolio_value"].iloc[0] - 1,
        "Max Drawdown": result["drawdown"].min() if "drawdown" in result else None,
        "Sharpe Ratio": result["sharpe"].mean() if "sharpe" in result else None
    }
    return summary
