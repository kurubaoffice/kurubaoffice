import os
import pandas as pd
import yfinance as yf
from fetcher.fetch_index_data import get_index_constituents


# ==== Sample Indicator Functions ====
def compute_ema(df, window=20):
    return df['Close'].ewm(span=window, adjust=False).mean()


def compute_rsi(df, window=14):
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


# ==== ✅ Storage Function (Global Data Path) ====
def save_to_csv(df, symbol):
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    save_path = os.path.join(project_root, "data", "processed", "stocks")
    os.makedirs(save_path, exist_ok=True)

    file_path = os.path.join(save_path, f"{symbol}.csv")
    df.to_csv(file_path, index=False)
    print(f"✅ Saved {symbol} with indicators → {file_path}")


# ==== Main Function ====
def build_nifty50_indicator_dataset():
    index_name = "NIFTY 50"
    symbols = get_index_constituents(index_name)
    print(f"📋 Found {len(symbols)} NIFTY 50 stocks.")

    for symbol in symbols:
        try:
            ticker = symbol + ".NS"
            df = yf.download(ticker, period="6mo", interval="1d", progress=False, auto_adjust=False)
            if df.empty:
                print(f"⚠️  Skipping {symbol} (no data).")
                continue

            df.reset_index(inplace=True)
            df['EMA_20'] = compute_ema(df, 20)
            df['RSI_14'] = compute_rsi(df, 14)
            save_to_csv(df, symbol)
        except Exception as e:
            print(f"[ERROR] {symbol}: {e}")


# ==== Run It ====
if __name__ == "__main__":
    build_nifty50_indicator_dataset()
