import pandas as pd
import os

def get_nifty_constituents(path="data/processed/stocks"):
    files = os.listdir(path)
    symbols = [f.replace(".csv", "") for f in files if f.endswith(".csv")]
    return sorted(symbols)

def save_to_csv(df, symbol, path="data/processed/stocks"):
    os.makedirs(path, exist_ok=True)
    file_path = os.path.join(path, f"{symbol}.csv")
    df.to_csv(file_path, index=False)
    print(f"✅ Saved {symbol} → {file_path}")
