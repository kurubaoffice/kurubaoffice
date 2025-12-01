import pandas as pd
from pathlib import Path

FNO_FILE = Path("data/raw/fno_list.csv")

def get_fno_list():
    return pd.read_csv(FNO_FILE)

def get_fno_symbols():
    df = pd.read_csv(FNO_FILE)
    return df["symbol"].tolist()
