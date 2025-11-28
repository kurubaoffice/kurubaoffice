import requests
import pandas as pd
import json
import os
from datetime import datetime


def merge_ce_pe(df: pd.DataFrame) -> pd.DataFrame:
    """Merge CE and PE rows into one row per strike with cleaned types."""
    # Ensure merge keys are correct type
    df["expiry"] = df["expiry"].astype(str)
    df["type"] = df["type"].astype(str)
    df["strike"] = pd.to_numeric(df["strike"], errors="coerce").fillna(0).astype(int)
    df["spot"] = pd.to_numeric(df["spot"], errors="coerce").fillna(0.0)

    ce = df[df["type"] == "CE"].copy()
    pe = df[df["type"] == "PE"].copy()

    ce = ce.rename(columns={
        "oi": "ce_oi",
        "change_oi": "ce_change_oi",
        "volume": "ce_volume",
        "iv": "ce_iv",
        "lastPrice": "ce_lastPrice",
        "bid": "ce_bid",
        "ask": "ce_ask",
    })

    pe = pe.rename(columns={
        "oi": "pe_oi",
        "change_oi": "pe_change_oi",
        "volume": "pe_volume",
        "iv": "pe_iv",
        "lastPrice": "pe_lastPrice",
        "bid": "pe_bid",
        "ask": "pe_ask",
    })

    # Merge on clean keys
    merged = ce.merge(pe, on=["strike", "expiry", "spot"], how="outer").fillna(0)

    return merged


def fetch_banknifty_option_chain(save_daily=False) -> pd.DataFrame:
    """Fetch BankNifty option chain and return a merged CE+PE DataFrame."""
    url = "https://www.nseindia.com/api/option-chain-indices?symbol=BANKNIFTY"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "*/*",
        "Referer": "https://www.nseindia.com/option-chain",
    }

    session = requests.Session()
    session.get("https://www.nseindia.com", headers=headers, timeout=10)
    response = session.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    data = response.json()

    # Save snapshots
    os.makedirs("data/raw/option_chain", exist_ok=True)
    with open("data/raw/option_chain/latest_banknifty_oc.json", "w") as f:
        json.dump(data, f, indent=2)
    if save_daily:
        date_str = datetime.now().strftime("%Y-%m-%d")
        with open(f"data/raw/option_chain/{date_str}.json", "w") as f:
            json.dump(data, f, indent=2)

    records = []
    base = data.get("records", {})
    spot = base.get("underlyingValue", 0)

    for item in base.get("data", []):
        strike = item.get("strikePrice", 0)
        ce = item.get("CE")
        pe = item.get("PE")

        if ce:
            records.append({
                "expiry": str(ce.get("expiryDate", "")),
                "type": "CE",
                "strike": strike,
                "oi": ce.get("openInterest", 0),
                "change_oi": ce.get("changeinOpenInterest", 0),
                "volume": ce.get("totalTradedVolume", 0),
                "iv": ce.get("impliedVolatility", 0.0),
                "lastPrice": ce.get("lastPrice", 0.0),
                "bid": ce.get("bidPrice", 0.0),
                "ask": ce.get("askPrice", 0.0),
                "spot": spot,
            })

        if pe:
            records.append({
                "expiry": str(pe.get("expiryDate", "")),
                "type": "PE",
                "strike": strike,
                "oi": pe.get("openInterest", 0),
                "change_oi": pe.get("changeinOpenInterest", 0),
                "volume": pe.get("totalTradedVolume", 0),
                "iv": pe.get("impliedVolatility", 0.0),
                "lastPrice": pe.get("lastPrice", 0.0),
                "bid": pe.get("bidPrice", 0.0),
                "ask": pe.get("askPrice", 0.0),
                "spot": spot,
            })

    df_raw = pd.DataFrame(records)

    # --- FORCE CLEAN TYPES ---
    for col in df_raw.columns:
        if col in ["expiry", "type"]:
            df_raw[col] = df_raw[col].astype(str).fillna("")
        else:
            df_raw[col] = pd.to_numeric(df_raw[col], errors="coerce").fillna(0)

    # Clean strike and spot again
    df_raw["strike"] = df_raw["strike"].astype(int)
    df_raw["spot"] = df_raw["spot"].astype(float)

    # Merge CE+PE safely
    df = merge_ce_pe(df_raw)
    return df


if __name__ == "__main__":
    df = fetch_banknifty_option_chain()
    print(df.head())
    print("Rows:", len(df))
