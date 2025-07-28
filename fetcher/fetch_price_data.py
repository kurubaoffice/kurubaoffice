import os
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from storage.db_writer import insert_price_data, get_latest_date_for_symbol  # NEW
import sys
import time
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data/raw/price_data"
CSV_PATH = BASE_DIR / "data/raw/company_info.csv"
DEFAULT_START_DATE = "2023-01-01"
END_DATE = datetime.today().strftime("%Y-%m-%d")

def fetch_price_for_symbol(symbol, start_date):
    try:
        yf_symbol = symbol + ".NS"
        df = yf.download(yf_symbol, start=start_date, end=END_DATE, progress=False, auto_adjust=False)
        if df.empty:
            print(f"[SKIP] No data for {symbol}")
            return None
        df.reset_index(inplace=True)
        df["Symbol"] = symbol
        return df[["Date", "Symbol", "Open", "High", "Low", "Close", "Adj Close", "Volume"]]
    except Exception as e:
        print(f"[ERROR] Failed for {symbol}: {e}")
        return None

def main():
    print("[START] Fetching historical price data...")
    os.makedirs(DATA_DIR, exist_ok=True)

    df_companies = pd.read_csv(CSV_PATH)
    print("[INFO] Columns in company_info.csv:", df_companies.columns.tolist())
    if "Symbol" in df_companies.columns:
        symbols = df_companies["Symbol"].dropna().unique()
    else:
        symbols = df_companies.iloc[:, 0].dropna().unique()

    fetched = 0
    for idx, symbol in enumerate(symbols, 1):
        print(f"[{idx}/{len(symbols)}] Checking: {symbol}")
        latest_date = get_latest_date_for_symbol(symbol)

        if latest_date:
            start_date = (latest_date + timedelta(days=1)).strftime("%Y-%m-%d")
            if start_date > END_DATE:
                print(f"[SKIP] {symbol} already up-to-date.")
                continue
        else:
            start_date = DEFAULT_START_DATE

        print(f"[{idx}] Fetching from {start_date} to {END_DATE} for {symbol}")
        df = fetch_price_for_symbol(symbol, start_date)

        if df is not None:
            csv_file = os.path.join(DATA_DIR, f"{symbol}.csv")
            df.to_csv(csv_file, index=False)

            insert_price_data(symbol, df)
            fetched += 1
            time.sleep(1)

            if idx % 10 == 0:
                print(f"[INFO] Processed {idx} symbols so far...")

    print(f"[DONE] Price data updated for {fetched}/{len(symbols)} symbols.")

if __name__ == "__main__":
    main()
