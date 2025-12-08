import requests
import pandas as pd
from requests.exceptions import RequestException

BASE_URL = "https://www.nseindia.com"
FNO_URL = BASE_URL + "/api/live-analysis-oi-spurts-underlyings"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Connection": "keep-alive"
}

session = requests.Session()
session.headers.update(HEADERS)


# ✅ REQUIRED: Initialize NSE Cookies
def init_nse():
    try:
        session.get(BASE_URL, timeout=5)
    except:
        pass


init_nse()


# ✅ ALWAYS RETURNS A DATAFRAME
def fetch_fno_snapshot() -> pd.DataFrame:
    try:
        r = session.get(FNO_URL, timeout=7)
        r.raise_for_status()
        data = r.json().get("data", [])
    except RequestException as e:
        print("FNO snapshot error:", e)
        return pd.DataFrame()

    rows = []
    for r in data:
        rows.append({
            "symbol": r.get("symbol"),
            "ltp": r.get("lastPrice"),
            "change_pct": r.get("pChange"),
            "oi": r.get("openInterest")
        })

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    df = df.dropna(subset=["symbol", "change_pct"])
    df["change_pct"] = pd.to_numeric(df["change_pct"], errors="coerce")
    df = df.dropna(subset=["change_pct"])

    return df
