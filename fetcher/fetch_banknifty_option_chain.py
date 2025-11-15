import requests
import pandas as pd
import json
import os
from datetime import datetime


def fetch_banknifty_option_chain(save_daily=False):
    """Fetch BankNifty option chain from NSE and return DataFrame."""

    url = "https://www.nseindia.com/api/option-chain-indices?symbol=BANKNIFTY"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/option-chain",
        "Connection": "keep-alive",
    }

    session = requests.Session()

    # Initial cookie request
    session.get("https://www.nseindia.com", headers=headers, timeout=10)

    # Actual data request
    response = session.get(url, headers=headers, timeout=10)
    response.raise_for_status()

    data = response.json()

    # Save latest snapshot
    os.makedirs("data/raw/option_chain", exist_ok=True)
    with open("data/raw/option_chain/latest_banknifty_oc.json", "w") as f:
        json.dump(data, f, indent=2)

    # Daily snapshot
    if save_daily:
        date_str = datetime.now().strftime("%Y-%m-%d")
        with open(f"data/raw/option_chain/{date_str}.json", "w") as f:
            json.dump(data, f, indent=2)

    # Parse into rows
    records = []
    base = data.get("records", {})
    spot = base.get("underlyingValue")

    for item in base.get("data", []):
        strike = item.get("strikePrice")
        ce = item.get("CE")
        pe = item.get("PE")

        # CE
        if ce:
            records.append({
                "expiry": ce.get("expiryDate"),
                "type": "CE",
                "strike": strike,
                "oi": ce.get("openInterest", 0),
                "change_oi": ce.get("changeinOpenInterest", 0),
                "volume": ce.get("totalTradedVolume", 0),
                "iv": ce.get("impliedVolatility", 0.0),
                "lastPrice": ce.get("lastPrice", 0.0),
                "bid": ce.get("bidPrice", 0.0),   # FIXED
                "ask": ce.get("askPrice", 0.0),
                "spot": spot,
            })

        # PE
        if pe:
            records.append({
                "expiry": pe.get("expiryDate"),
                "type": "PE",
                "strike": strike,
                "oi": pe.get("openInterest", 0),
                "change_oi": pe.get("changeinOpenInterest", 0),
                "volume": pe.get("totalTradedVolume", 0),
                "iv": pe.get("impliedVolatility", 0.0),
                "lastPrice": pe.get("lastPrice", 0.0),
                "bid": pe.get("bidPrice", 0.0),  # FIXED
                "ask": pe.get("askPrice", 0.0),
                "spot": spot,
            })

    df = pd.DataFrame(records)

    # Final safety cleanup
    numeric_cols = ["oi", "change_oi", "volume", "iv", "strike", "bid", "ask", "lastPrice", "spot"]
    for c in numeric_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    return df


if __name__ == "__main__":
    df = fetch_banknifty_option_chain()
    print(df.head())
    print("Rows:", len(df))
