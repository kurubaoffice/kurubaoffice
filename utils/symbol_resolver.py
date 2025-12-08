import pandas as pd
from rapidfuzz import process, fuzz
import os
import glob

# -------------------------------
# Detect data directory
# -------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(ROOT, "Tidder2.0", "data", "raw")
os.makedirs(DATA_DIR, exist_ok=True)

# -------------------------------
# Auto-detect CSV
# -------------------------------
csv_files = glob.glob(os.path.join(DATA_DIR, "company_info.csv"))

if not csv_files:
    print("[symbol_resolver] No CSV file found in", DATA_DIR)
    full_symbols = {}
else:
    FULL_LIST_PATH = csv_files[0]
    print("[symbol_resolver] Using CSV:", FULL_LIST_PATH)

    try:
        df_full = pd.read_csv(FULL_LIST_PATH)
        # Normalize columns
        df_full.columns = [c.lower().replace(" ", "_") for c in df_full.columns]

        # Automatically detect columns
        name_col = [c for c in df_full.columns if "name" in c][0]
        symbol_col = [c for c in df_full.columns if "symbol" in c][0]

        full_symbols = {
            str(row[name_col]).upper(): str(row[symbol_col]).upper()
            for _, row in df_full.iterrows()
            if pd.notna(row[symbol_col])
        }

    except Exception as e:
        print("[symbol_resolver] Error loading full list:", e)
        full_symbols = {}

# For fuzzy search
company_names = list(full_symbols.keys())


# -------------------------------
# Core Resolver
# -------------------------------
def resolve_symbol(query: str):
    """
    Given any text (e.g., 'tcs', 'Reliance', 'infosys ltd', 'HDFC BANK'),
    returns the NSE symbol (e.g., 'TCS', 'RELIANCE', 'INFY', 'HDFCBANK').
    """
    if not query or not full_symbols:
        return None

    q = query.strip().upper()

    # 1️⃣ Direct exact symbol match
    if q in full_symbols.values():
        return q

    # 2️⃣ Direct company name match
    if q in full_symbols:
        return full_symbols[q]

    # 3️⃣ Starts-with match
    for name, sym in full_symbols.items():
        if name.startswith(q):
            return sym

    # 4️⃣ Fuzzy match using RapidFuzz
    if company_names:
        match = process.extractOne(q, company_names, scorer=fuzz.WRatio)
        if match and match[1] > 80:  # confidence threshold
            return full_symbols[match[0]]

    # No match
    return None
