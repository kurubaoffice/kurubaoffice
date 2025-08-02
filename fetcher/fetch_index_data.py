# modules/indexes/fetch_index_data.py

import pandas as pd
import yfinance as yf
from nsepython import nsefetch
from datetime import datetime

# Index codes for display/logging
INDEX_SYMBOLS = {
    "NIFTY 50": "NIFTY",
    "BANK NIFTY": "BANKNIFTY",
}

def get_index_constituents(index_name):
    """
    Returns list of constituent symbols for NIFTY or BANKNIFTY.
    """
    url_map = {
        "NIFTY 50": "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%2050",
        "BANK NIFTY": "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20BANK"
    }

    try:
        url = url_map[index_name]
        data = nsefetch(url)
        symbols = [item["symbol"] for item in data["data"]]
        # Remove index label if present
        symbols = [s for s in symbols if s.upper() != index_name.upper()]
        return symbols
    except Exception as e:
        print(f"[ERROR] Fetching constituents for {index_name}: {e}")
        return []

def get_index_historical(index_name, period="6mo", interval="1d"):
    """
    Returns historical OHLCV data using yfinance (for indicators).
    """
    symbol_map = {
        "NIFTY 50": "^NSEI",
        "BANK NIFTY": "^NSEBANK",
    }

    try:
        symbol = symbol_map[index_name]
        df = yf.download(symbol, period=period, interval=interval, progress=False, auto_adjust=False)
        df.dropna(inplace=True)
        df.reset_index(inplace=True)
        return df
    except Exception as e:
        print(f"[ERROR] Failed to fetch historical data for {index_name}: {e}")
        return pd.DataFrame()

# Example usage
if __name__ == "__main__":
    index = "NIFTY 50"

    print("📋 Fetching constituents...")
    constituents = get_index_constituents(index)
    print(f"{index} has {len(constituents)} stocks:")
    print(constituents)

    print("📈 Fetching historical data...")
    df = get_index_historical(index)
    print(df.tail())
