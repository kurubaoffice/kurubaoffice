import pandas as pd
import os

def list_available_symbols(data_path):
    return [f.replace(".csv", "") for f in os.listdir(data_path) if f.endswith(".csv")]

def load_stock_data(symbol, data_path):
    file_path = os.path.join(data_path, f"{symbol}.csv")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"CSV not found for {symbol}")
    return pd.read_csv(file_path, parse_dates=["Date"])
