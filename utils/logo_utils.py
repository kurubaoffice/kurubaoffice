
import os
import pandas as pd

# Compute absolute project root path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

COMPANY_FILE = os.path.join(BASE_DIR, "data", "raw", "company_info.csv")

print("📁 Loading company file from:", COMPANY_FILE)

df = pd.read_csv(COMPANY_FILE)
df.set_index("symbol", inplace=True)

def get_company_details(symbol):
    try:
        row = df.loc[symbol]
        return row["name"], row.get("logo_path")
    except:
        return symbol, None
