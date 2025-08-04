import pandas as pd
import os

import os


import os

def get_nifty_constituents(path="data/processed/stocks"):
    base_path = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(base_path, "..", path)  # relative to helpers.py
    full_path = os.path.abspath(full_path)

    print(f"[DEBUG] Looking in: {full_path}")
    if not os.path.exists(full_path):
        print(f"[ERROR] Path does not exist: {full_path}")
        return []

    files = os.listdir(full_path)
    print(f"[DEBUG] Files found: {files}")

    return [f.replace(".csv", "") for f in files if f.endswith(".csv")]



def save_to_csv(df, symbol, path="data/processed/stocks"):
    os.makedirs(path, exist_ok=True)
    file_path = os.path.join(path, f"{symbol}.csv")
    df.to_csv(file_path, index=False)
    print(f"✅ Saved {symbol} → {file_path}")


from pathlib import Path

def get_project_root():
    return Path(__file__).resolve().parents[1]
