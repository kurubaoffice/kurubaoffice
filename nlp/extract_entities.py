import os
import pandas as pd
from rapidfuzz import process, fuzz
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMPANY_CSV = os.path.join(BASE_DIR, "data", "raw", "company_info.csv")

df = pd.read_csv(COMPANY_CSV)

company_names = df['name'].str.lower().tolist()
symbols = df['symbol'].tolist()


def extract_stock_entity(text: str):
    text_low = text.lower().strip()

    # --- 1) Tokenize & make 1-2 word windows ---
    tokens = re.findall(r"[a-zA-Z]+", text_low)
    candidates = []

    # Single words
    for t in tokens:
        candidates.append(t)

    # Two-word combinations → "reliance industries"
    for i in range(len(tokens) - 1):
        candidates.append(tokens[i] + " " + tokens[i+1])

    # --- 2) Try matching candidates ---
    for cand in candidates:
        # Symbol check
        if cand.upper() in symbols:
            return cand.upper(), 100

        # Fuzzy match
        best = process.extractOne(cand, company_names, scorer=fuzz.ratio)
        if best and best[1] >= 80:
            idx = company_names.index(best[0])
            return symbols[idx], best[1]

    return None, 0
