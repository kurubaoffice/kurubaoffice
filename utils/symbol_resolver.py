import pandas as pd
from rapidfuzz import process, fuzz
import os

# -------------------------------
# Load NSE full company list
# -------------------------------
FULL_LIST_PATH = "data/raw/company_info.csv"  # you have this already

if os.path.exists(FULL_LIST_PATH):
    try:
        df_full = pd.read_csv(FULL_LIST_PATH)
        df_full.columns = [c.lower() for c in df_full.columns]

        # Expect columns: company_name, symbol
        full_symbols = {
            str(row["company_name"]).upper(): str(row["symbol"]).upper()
            for _, row in df_full.iterrows()
            if pd.notna(row["symbol"])
        }
    except Exception as e:
        print("[symbol_resolver] Error loading full list:", e)
        full_symbols = {}
else:
    print("[symbol_resolver] Full NSE list not found at", FULL_LIST_PATH)
    full_symbols = {}

# For fuzzy search
company_names = list(full_symbols.keys())


# -----------------------------------------------------------
# Core Resolver
# -----------------------------------------------------------
def resolve_symbol(query: str):
    """
    Given any text (e.g., 'tcs', 'Reliance', 'infosys ltd', 'HDFC BANK'),
    returns the NSE symbol (e.g., 'TCS', 'RELIANCE', 'INFY', 'HDFCBANK').
    """

    if not query:
        return None

    q = query.strip().upper()

    # 1️⃣ Direct exact symbol match
    if q in full_symbols.values():
        return q

    # 2️⃣ Direct company name match
    if q in full_symbols:
        return full_symbols[q]

    # 3️⃣ Starts-with match (TATA, HDFC etc.)
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
