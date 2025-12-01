# compute/options/fno_snapshot.py

import requests
import pandas as pd

NSE_FNO_URL = "https://www.nseindia.com/api/live-analysis-oi-spurts-underlyings"
NSE_CHAIN_URL = "https://www.nseindia.com/api/option-chain-equities"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*",
    "Connection": "keep-alive"
}

session = requests.Session()
session.headers.update(HEADERS)


# -----------------------------------------------------------------------------------
# 1️⃣ Fetch Top FnO Underlying Snapshot (Gainers / Losers)
# -----------------------------------------------------------------------------------
def fetch_fno_snapshot():
    try:
        r = session.get(NSE_FNO_URL, timeout=5)
        data = r.json()["data"]
    except Exception as e:
        print("Snapshot error:", e)
        return pd.DataFrame()

    rows = []
    for row in data:
        try:
            rows.append({
                "symbol": row.get("symbol"),
                "ltp": row.get("lastPrice"),
                "change_pct": row.get("pChange"),
                "oi": row.get("openInterest")
            })
        except:
            pass

    df = pd.DataFrame(rows)
    return df.dropna()


def get_top_movers(df):
    df_sorted = df.sort_values("change_pct", ascending=False)
    return df_sorted.head(10), df_sorted.tail(10)


# -----------------------------------------------------------------------------------
# 2️⃣ Fetch FnO Option Chain for CE/PE selection
# -----------------------------------------------------------------------------------
def fetch_option_chain(symbol):
    url = f"{NSE_CHAIN_URL}?symbol={symbol}"

    try:
        r = session.get(url, timeout=5)
        data = r.json()
    except:
        return None

    rows = []

    for entry in data["records"]["data"]:
        strike = entry.get("strikePrice")
        expiry = entry.get("expiryDate")

        ce = entry.get("CE")
        pe = entry.get("PE")

        # CE DATA
        if ce:
            rows.append({
                "symbol": symbol,
                "optionType": "CE",
                "strike": strike,
                "expiry": expiry,
                "premium": ce.get("lastPrice"),
                "change_pct": ce.get("pChange"),
                "oi": ce.get("openInterest"),
                "volume": ce.get("totalTradedVolume")
            })

        # PE DATA
        if pe:
            rows.append({
                "symbol": symbol,
                "optionType": "PE",
                "strike": strike,
                "expiry": expiry,
                "premium": pe.get("lastPrice"),
                "change_pct": pe.get("pChange"),
                "oi": pe.get("openInterest"),
                "volume": pe.get("totalTradedVolume")
            })

    df = pd.DataFrame(rows)
    return df.dropna()
