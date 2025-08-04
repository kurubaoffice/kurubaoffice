import os
import pandas as pd
import yfinance as yf
from nsepython import nsefetch
from datetime import datetime
from pathlib import Path

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_INDEX_DIR = BASE_DIR / "data" / "processed" / "index"
PROCESSED_STOCK_DIR = BASE_DIR / "data" / "processed" / "stocks"

# Ensure folders exist
RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_INDEX_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_STOCK_DIR.mkdir(parents=True, exist_ok=True)


def get_index_constituents(index_name="NIFTY 50"):
    url = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%2050"
    try:
        data = nsefetch(url)
        symbols = [item["symbol"] for item in data["data"]]
        symbols = [s for s in symbols if s.upper() != index_name.upper()]
        return symbols
    except Exception as e:
        print(f"[ERROR] Fetching constituents failed: {e}")
        return []


def fetch_and_save_index_data(symbol="^NSEI", filename="NIFTY.csv"):
    print(f"[📈] Downloading index data for: {symbol}")
    try:
        df = yf.download(symbol, period="6mo", interval="1d", progress=False)
        df.dropna(inplace=True)
        df.reset_index(inplace=True)
        df.to_csv(PROCESSED_INDEX_DIR / filename, index=False)
        print(f"[💾] Saved index data to: {PROCESSED_INDEX_DIR / filename}")
    except Exception as e:
        print(f"[ERROR] Failed to fetch index data: {e}")


def fetch_and_save_stock_data(symbols):
    for sym in symbols:
        try:
            print(f"[📊] Downloading: {sym}")
            df = yf.download(f"{sym}.NS", period="6mo", interval="1d", progress=False)
            df.dropna(inplace=True)
            df.reset_index(inplace=True)
            df.to_csv(PROCESSED_STOCK_DIR / f"{sym}.csv", index=False)
        except Exception as e:
            print(f"[ERROR] {sym}: {e}")


if __name__ == "__main__":
    index_name = "NIFTY 50"

    # 1. Fetch & Save Constituents
    symbols = get_index_constituents(index_name)
    pd.DataFrame({"symbol": symbols}).to_csv(RAW_DIR / "nifty_constituents.csv", index=False)
    print(f"[✅] Saved constituents list to: {RAW_DIR / 'nifty_constituents.csv'}")

    # 2. Fetch & Save Index Historical
    fetch_and_save_index_data(symbol="^NSEI", filename="NIFTY.csv")

    # 3. Fetch & Save Stocks
    fetch_and_save_stock_data(symbols)
