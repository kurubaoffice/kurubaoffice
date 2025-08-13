import os
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DATA_PATH = os.path.join(BASE_DIR, "data", "raw", "listed_companies.csv")
PROCESSED_STOCKS_DIR = os.path.join(BASE_DIR, "data", "processed", "stocks")
PROCESSED_INDEX_DIR = os.path.join(BASE_DIR, "data", "processed", "indexes")

# Ensure output folders exist
os.makedirs(PROCESSED_STOCKS_DIR, exist_ok=True)
os.makedirs(PROCESSED_INDEX_DIR, exist_ok=True)

# Yahoo Finance mapping
SYMBOL_MAP = {
    "NIFTY": "^NSEI",
    "BANKNIFTY": "^NSEBANK"
}


def fetch_and_save(symbol, is_index=False):
    """Fetch last ~3 years of data for a symbol and save to CSV with clean standardized format."""
    try:
        yf_symbol = SYMBOL_MAP.get(symbol, f"{symbol}.NS" if not is_index else symbol)
        start_date = datetime.now() - timedelta(days=1000)

        data = yf.download(
            yf_symbol,
            start=start_date,
            end=datetime.now(),
            progress=False,
            auto_adjust=False
        )

        # --- Defensive: handle tuple or unexpected return ---
        if isinstance(data, tuple):
            print(f"[WARN] yfinance returned tuple for {symbol}, unpacking first element")
            data = data[0]

        if not isinstance(data, pd.DataFrame):
            raise TypeError(f"[ERROR] Expected DataFrame, got {type(data)}")

        if data.empty:
            raise ValueError("No data fetched")

        # --- Standardize DataFrame ---
        data.reset_index(inplace=True)

        # Flatten MultiIndex columns if present
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = [col[0] if isinstance(col, tuple) else col for col in data.columns]

        # Lowercase column names
        data.columns = [str(c).lower() for c in data.columns]

        # Rename to standard columns
        col_map = {
            "date": "date",
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "adj close": "adj_close",
            "volume": "volume",
            "price": "price"  # fallback
        }
        for old, new in col_map.items():
            if old in data.columns:
                data.rename(columns={old: new}, inplace=True)

        # Ensure all required columns exist
        required_cols = ["date", "open", "high", "low", "close", "adj_close", "volume"]
        for col in required_cols:
            if col not in data.columns:
                data[col] = pd.NA

        # Convert date column and sort
        data['date'] = pd.to_datetime(data['date'], errors='coerce')
        data = data.dropna(subset=['date']).sort_values('date')

        # --- Save CSV ---
        save_dir = PROCESSED_INDEX_DIR if is_index else PROCESSED_STOCKS_DIR
        os.makedirs(save_dir, exist_ok=True)
        file_path = os.path.join(save_dir, f"{symbol}.csv")
        data.to_csv(file_path, index=False)

        print(f"✅ Saved: {symbol} ({len(data)} rows)")
        return True

    except Exception as e:
        print(f"❌ Failed: {symbol} - {e}")
        return False


def main():
    companies_df = pd.read_csv(RAW_DATA_PATH)
    symbols = companies_df["symbol"].dropna().unique().tolist()

    indexes = ["NIFTY", "BANKNIFTY"]

    success_count, fail_count = 0, 0
    failed_symbols = []

    print("\n=== Fetching Stock Data ===")
    for sym in symbols:
        if fetch_and_save(sym):
            success_count += 1
        else:
            fail_count += 1
            failed_symbols.append(sym)

    print("\n=== Fetching Index Data ===")
    for idx in indexes:
        if fetch_and_save(idx, is_index=True):
            success_count += 1
        else:
            fail_count += 1
            failed_symbols.append(idx)

    print("\n=== Fetch Summary ===")
    print(f"✅ Success: {success_count}")
    print(f"❌ Fail: {fail_count}")
    if failed_symbols:
        print(f"Failed symbols: {failed_symbols}")


if __name__ == "__main__":
    main()
