# compute/volatility/vol_strategies.py
"""
VIX-based Volatility Regime + Options Strategy Module (LIVE VERSION)
Uses:
- fetch_india_vix() for real-time VIX
- Local NIFTY CSV for ATR calculation
- Optional lightweight rolling VIX history file (auto-managed)

NO yfinance, NO external APIs except NSE.

This module ALWAYS works live.
"""

import os
import pandas as pd
import datetime as dt

from fetcher.fetch_india_vix import fetch_india_vix

# --------------------------------
# FIXED: Always anchor to project root
# --------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#DATA_DIR = os.path.join(ROOT, "data", "processed", "index")
DATA_DIR = os.path.dirname(os.path.dirname(__file__))   # Tidder2.0/

VIX_HISTORY_PATH = os.path.join(DATA_DIR, "VIX_HISTORY.csv")
NIFTY_PATH = os.path.join(DATA_DIR, "NIFTY.csv")

# Ensure directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# ------------------------------
# 1. Load or create VIX history
# ------------------------------
def update_vix_history(live_vix):
    """
    Maintains a rolling 250-day VIX history file.
    Auto-creates if missing.
    """

    # If no file → create one with only today's value
    if not os.path.exists(VIX_HISTORY_PATH):
        df = pd.DataFrame([{
            "Date": dt.datetime.now().strftime("%Y-%m-%d"),
            "VIX": live_vix
        }])
        df.to_csv(VIX_HISTORY_PATH, index=False)
        return df["VIX"]

    # Append today's VIX
    df = pd.read_csv(VIX_HISTORY_PATH)
    today = dt.datetime.now().strftime("%Y-%m-%d")

    if df["Date"].iloc[-1] != today:
        df.loc[len(df)] = [today, live_vix]

    # Keep last 250 rows
    df = df.tail(250)
    df.to_csv(VIX_HISTORY_PATH, index=False)

    return df["VIX"]



# ------------------------------
# 2. Load NIFTY data
# ------------------------------
def load_nifty():
    path = os.path.join(ROOT, "data", "processed", "index", "NIFTY.csv")

    if not os.path.exists(path):
        print("FILE NOT FOUND:", path)
        return False

    df = pd.read_csv(path)

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])
    df = df.sort_values("Date")

    df.rename(columns={
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
    }, inplace=True)

    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["open", "close"])

    return df






# ------------------------------
# 3. VIX percentile metric
# ------------------------------
def compute_vix_percentile(vix_series):
    ranks = vix_series.rank(pct=True)
    return float(ranks.iloc[-1] * 100)



# ------------------------------
# 4. Regime detection
# ------------------------------
def detect_regime(vix, percentile):
    if percentile is None:
        # Fallback absolute VIX rule when no history exists
        if vix <= 12:
            return "low"
        if 12 < vix <= 18:
            return "neutral"
        return "high"

    # Full logic when percentile known
    if vix <= 12 or percentile <= 10:
        return "low"
    if 12 < vix <= 18:
        return "neutral"
    return "high"



# ------------------------------
# 5. ATR%
# ------------------------------
def compute_atr_pct(nifty_df, period=14):
    df = nifty_df.copy()
    df["H-L"] = df["high"] - df["low"]
    atr = df["H-L"].rolling(period).mean().iloc[-1]
    close = df["close"].iloc[-1]
    return (atr / close) * 100




# ------------------------------
# 6. Strategy Suggestor
# ------------------------------
def suggest_strategy(regime):

    if regime == "low":
        return [
            {"strategy": "buy_puts", "timing": "now",
             "notes": "Best time to buy puts. Crash probability high."},

            {"strategy": "buy_straddle", "timing": "now",
             "notes": "IV is cheap → perfect for straddles."},

            {"strategy": "put_calendar", "timing": "now",
             "notes": "Sell near-month / buy next-month ATM put."},
        ]

    if regime == "neutral":
        return [
            {"strategy": "light_long_vol", "timing": "monitor",
             "notes": "Build small hedges. Wait for breakout."}
        ]

    # high regime
    return [
        {"strategy": "sell_premium", "timing": "now",
         "notes": "High IV → iron condor, short strangle (hedged)."}
    ]



# ------------------------------
# 7. MASTER FUNCTION
# ------------------------------
def analyze_vix_and_nifty():
    # 1) Live VIX
    live_vix = fetch_india_vix()["vix"]

    # 2) Update / create VIX history
    vix_series = update_vix_history(live_vix)

    # If history < 20 points, percentile not meaningful
    vix_pct = compute_vix_percentile(vix_series) if len(vix_series) >= 20 else None

    # 3) Load NIFTY
    nifty = load_nifty()

    # 4) ATR%
    atr_pct = compute_atr_pct(nifty)

    # 5) Regime
    regime = detect_regime(live_vix, vix_pct)

    # 6) Strategies
    strategies = suggest_strategy(regime)

    return {
        "timestamp": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "vix": {
            "value": live_vix,
            "percentile": vix_pct
        },
        "regime": regime,
        "nifty_close": float(nifty["close"].iloc[-1]),
        "nifty_atr_pct": float(atr_pct),
        "suggestions": strategies
    }
def format_vol_report_telegram(data):
    """
    Formats the Volatility Strategy Report for Telegram output.
    """
    date = data.get("timestamp", "N/A")

    vix_val = data["vix"].get("value", "N/A")
    vix_pctile = data["vix"].get("percentile", "N/A")
    regime = data.get("regime", "N/A")

    nifty_close = data.get("nifty_close", "N/A")
    atr_pct = data.get("nifty_atr_pct", "N/A")

    suggestions = data.get("suggestions", [])

    # Build strategy suggestions list
    strat_text = ""
    for s in suggestions:
        strat_text += f"• *{s['strategy'].replace('_', ' ').title()}* — {s['timing']}\n"
        strat_text += f"    _{s['notes']}_\n"

    return f"""
<b>📊 VOLATILITY STRATEGY REPORT</b>

<b>🗓 Date:</b> {date}

<b>🧨 INDIA VIX:</b> {vix_val}
<b>Percentile:</b> {vix_pctile}
<b>Market Regime:</b> <b>{regime.upper()}</b>

<b>📌 NIFTY:</b> {nifty_close}
<b>ATR %:</b> {atr_pct:.2f}%

<b>🎯 Suggested Strategies</b>
{strat_text}
""".strip()


if __name__ == "__main__":
    print(analyze_vix_and_nifty())
