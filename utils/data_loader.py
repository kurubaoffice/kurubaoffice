import os
import yfinance as yf
import pandas as pd


def _clean_df(raw):
    # Defensive unpack if raw is a tuple
    if isinstance(raw, tuple):
        print("[WARN] yfinance returned a tuple, unpacking first element")
        raw = raw[0]

    if isinstance(raw, tuple):
        print("[ERROR] yfinance returned nested tuple — unsupported")
        raise ValueError("Nested tuple from yfinance, invalid response")

    if raw is None:
        raise ValueError("[ERROR] yfinance returned None")

    if not isinstance(raw, pd.DataFrame):
        raise TypeError(f"[ERROR] Expected DataFrame, got {type(raw)}")

    if raw.empty:
        raise ValueError("[ERROR] yfinance returned empty DataFrame")

    # Flatten MultiIndex columns if needed
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = [col[0] for col in raw.columns]

    raw.columns = [str(c).lower() for c in raw.columns]
    print(f"[DEBUG] Cleaned columns for dataframe: {raw.columns.tolist()}")

    raw.reset_index(inplace=True)
    if "date" in raw.columns:
        raw["Date"] = pd.to_datetime(raw["date"])
    return raw


def get_stock_historical(symbol, period="3mo", interval="1d"):
    print(f"[INFO] Fetching stock: {symbol}")

    local_path = os.path.join("data", "processed", "stocks", f"{symbol}.csv")
    if os.path.exists(local_path):
        print(f"[📁] Loading from local CSV: {local_path}")
        df = pd.read_csv(local_path)
        df['date'] = pd.to_datetime(df['date'])
        return df

    # Else fetch from yfinance
    yf_symbol = symbol if symbol.endswith(".NS") else f"{symbol}.NS"
    print(f"[🌐] Fetching from yfinance: {yf_symbol}")
    raw = yf.download(yf_symbol, period=period, interval=interval, auto_adjust=False, progress=False)
    return _clean_df(raw)


def get_index_historical(symbol="^NSEI", period="3mo", interval="1d"):
    local_path = os.path.join("data", "processed", "index", "NIFTY.csv")

    if os.path.exists(local_path):
        print(f"[📂] Reading local index data from {local_path}")
        try:
            df = pd.read_csv(local_path)
            df.columns = [c.lower() for c in df.columns]
            if "date" in df.columns:
                df["Date"] = pd.to_datetime(df["date"])
            return _clean_df(df)
        except Exception as e:
            print(f"[ERROR] Failed to read local index CSV: {e}")
            print(f"[INFO] Falling back to yfinance for index {symbol}")

    print(f"[🌐] Fetching index: {symbol}")
    raw = yf.download(symbol, period=period, interval=interval, auto_adjust=False, progress=False)
    return _clean_df(raw)


# --- New: List symbols filtered by listed_companies.csv ---

LISTED_COMPANIES_CSV = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw', 'listed_companies.csv')


def list_available_symbols(data_path):
    """
    Returns sorted list of symbols present in both listed_companies.csv
    and with existing CSV data files in data_path.
    """
    df_listed = pd.read_csv(LISTED_COMPANIES_CSV)
    symbols = df_listed['symbol'].tolist()

    available_symbols = [s for s in symbols if os.path.exists(os.path.join(data_path, f"{s}.csv"))]

    return sorted(available_symbols)


def load_stock_data(symbol, data_dir):
    filepath = os.path.join(data_dir, f"{symbol}.csv")

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"No data file found for {symbol}")

    df = pd.read_csv(filepath)

    # Find date column
    date_col = None
    for col in ["Date", "date"]:
        if col in df.columns:
            date_col = col
            break

    if not date_col:
        raise ValueError(f"No date column found for {symbol}")

    # Convert date
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col])
    df = df.sort_values(by=date_col)

    return df
