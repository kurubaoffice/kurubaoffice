import os
import pandas as pd
import datetime as dt

from fetcher.fetch_india_vix import fetch_india_vix


# ============================================================
# CONFIG
# ============================================================

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Tidder2.0/

DATA_DIR = os.path.join(ROOT, "data", "processed", "index")

os.makedirs(DATA_DIR, exist_ok=True)

VIX_HISTORY_PATH = os.path.join(DATA_DIR, "VIX_HISTORY.csv")
NIFTY_PATH = os.path.join(DATA_DIR, "NIFTY.csv")




# ============================================================
# 1. VIX HISTORY
# ============================================================

def update_vix_history(live_vix):
    """Maintains a rolling 250-day VIX history."""

    today = dt.datetime.now().strftime("%Y-%m-%d")

    # Create file if missing
    if not os.path.exists(VIX_HISTORY_PATH):
        df = pd.DataFrame([{"Date": today, "VIX": live_vix}])
        df.to_csv(VIX_HISTORY_PATH, index=False)
        return df["VIX"]

    df = pd.read_csv(VIX_HISTORY_PATH)

    # Append today's value if not present
    if df["Date"].iloc[-1] != today:
        df.loc[len(df)] = [today, live_vix]

    df = df.tail(250)
    df.to_csv(VIX_HISTORY_PATH, index=False)

    return df["VIX"]

import yfinance as yf

def backfill_vix_history_if_needed(min_rows=200):
    """Auto-fill VIX history if file is empty or too short"""

    if os.path.exists(VIX_HISTORY_PATH):
        df = pd.read_csv(VIX_HISTORY_PATH)
        if len(df) >= min_rows:
            return df["VIX"]

    print("⚠️ Backfilling India VIX history from Yahoo Finance...")

    vix = yf.download("^INDIAVIX", period="2y", interval="1d")

    if vix.empty:
        print("❌ Failed to fetch VIX history")
        return None

    vix = vix.reset_index()
    vix = vix[["Date", "Close"]]
    vix.columns = ["Date", "VIX"]
    vix["Date"] = vix["Date"].dt.strftime("%Y-%m-%d")

    vix.to_csv(VIX_HISTORY_PATH, index=False)

    print("✅ VIX history backfilled:", len(vix), "rows")
    return vix["VIX"]

# ============================================================
# 2. LOAD NIFTY
# ============================================================

def load_nifty():
    """Load NIFTY OHLC from your local fetcher output."""

    if not os.path.exists(NIFTY_PATH):
        raise FileNotFoundError(f"NIFTY CSV NOT FOUND → {NIFTY_PATH}")

    df = pd.read_csv(NIFTY_PATH)

    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date")

    df.rename(columns={
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
    }, inplace=True)

    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["close"])

    return df


# ============================================================
# 3. VIX PERCENTILE
# ============================================================

def compute_vix_percentile(vix_series):
    ranks = vix_series.rank(pct=True)
    return float(ranks.iloc[-1] * 100)


# ============================================================
# 4. VOLATILITY REGIME
# ============================================================

def detect_regime(vix, percentile):
    if percentile is None:  # insufficient history
        if vix <= 12:
            return "low"
        if 12 < vix <= 18:
            return "neutral"
        return "high"

    # With percentile logic
    if vix <= 12 or percentile <= 10:
        return "low"
    if 12 < vix <= 18:
        return "neutral"
    return "high"

# ============================================================
# 4.1 CRASH PROBABILITY ENGINE
# ============================================================

def compute_crash_probability(vix, percentile, atr_pct, regime):
    """
    Returns crash probability as a percentage (0–100)
    """

    score = 0

    # 1️⃣ VIX Percentile Contribution (50%)
    if percentile is not None:
        score += percentile * 0.5
    else:
        # fallback if percentile missing
        score += min((vix / 40) * 50, 50)

    # 2️⃣ ATR % Contribution (30%)
    atr_score = min((atr_pct / 2.0) * 30, 30)  # 2% ATR = full 30 points
    score += atr_score

    # 3️⃣ Regime Contribution (20%)
    regime_weight = {
        "low": 5,
        "neutral": 12,
        "high": 20
    }.get(regime, 5)

    score += regime_weight

    return round(min(score, 100), 1)

# ============================================================
# 5. ATR %
# ============================================================

def compute_atr_pct(nifty_df, period=14):
    df = nifty_df.copy()

    df["H-L"] = df["high"] - df["low"]
    atr = df["H-L"].rolling(period).mean().iloc[-1]
    close = df["close"].iloc[-1]

    return (atr / close) * 100


# ============================================================
# 6. STRATEGY ENGINE
# ============================================================

def suggest_strategy(regime):

    if regime == "low":
        return [
            ("Buy Puts", "now", "Best time to buy puts. Crash probability high."),
            ("Buy Straddle", "now", "IV is cheap → perfect for straddles."),
            ("Put Calendar", "now", "Sell near-month / buy next-month ATM put."),
        ]

    if regime == "neutral":
        return [
            ("Light Long Vol", "monitor", "Build small hedges. Wait for breakout.")
        ]

    # high
    return [
        ("Sell Premium", "now", "High IV → iron condor, short strangle (hedged).")
    ]


# ============================================================
# 7. MASTER ENGINE
# ============================================================

def analyze_vix_and_nifty():
    """Main analysis → returns a dict to feed into Telegram formatter."""

    # LIVE VIX
    live_vix = fetch_india_vix()["vix"]

    # Update VIX history
    # Ensure history exists (auto backfill if missing)
    vix_series = backfill_vix_history_if_needed()

    # Update today's data
    vix_series = update_vix_history(live_vix)

    # Compute real percentile
    vix_pct = compute_vix_percentile(vix_series)

    # Load local NIFTY
    nifty = load_nifty()

    # ATR%
    atr_pct = compute_atr_pct(nifty)

    # Regime
    regime = detect_regime(live_vix, vix_pct)

    # ✅ Crash Probability
    crash_prob = compute_crash_probability(
        vix=live_vix,
        percentile=vix_pct,
        atr_pct=atr_pct,
        regime=regime
    )

    # Strategies
    strategies = suggest_strategy(regime)


    return {
        "timestamp": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "vix": {
            "value": live_vix,
            "percentile": vix_pct
        },
        "regime": regime,
        "crash_probability": crash_prob,
        "nifty_close": float(nifty["close"].iloc[-1]),
        "nifty_atr_pct": float(atr_pct),
        "strategies": strategies
    }


# ============================================================
# 8. TELEGRAM FORMATTER
# ============================================================

def format_vol_report_telegram(data):
    """Returns a clean, compact, Telegram-optimized HTML message."""

    ts = data["timestamp"]
    v = data["vix"]["value"]
    pct = data["vix"]["percentile"]
    close = data["nifty_close"]
    atr = data["nifty_atr_pct"]
    regime = data["regime"].upper()
    crash = data["crash_probability"]

    regime_emoji = {
        "LOW": "🟢",
        "NEUTRAL": "🟡",
        "HIGH": "🔴"
    }.get(regime, "")

    pct_txt = f"{pct:.1f}%" if pct is not None else "—"

    msg = (
f"<b>📊 VOLATILITY STRATEGY REPORT</b>\n\n"

f"<b>🗓 Date:</b> {ts}\n\n"

f"<b>🧨 INDIA VIX:</b> {v:.2f}\n"
f"<b>Percentile:</b> {pct_txt}\n"
f"<b>Market Regime:</b> <b>{regime} {regime_emoji}</b>\n\n"
f"<b>💥 Crash Probability:</b> <b>{crash}%</b>\n\n"

f"<b>📌 NIFTY:</b> {close:,.2f}\n"
f"<b>ATR %:</b> {atr:.2f}%\n\n"



f"<b>🎯 Recommended Strategies</b>\n"
    )

    # Strategies block
    for name, timing, note in data["strategies"]:
        msg += (
            f"• <b>{name}</b> — <i>{timing}</i>\n"
            f"  ⤷ <i>{note}</i>\n"
        )

    return msg.strip()

def format_vol_report_cli(data):
    """Plain-text version for terminal (no HTML tags)."""

    ts = data["timestamp"]
    v = data["vix"]["value"]
    pct = data["vix"]["percentile"]
    close = data["nifty_close"]
    atr = data["nifty_atr_pct"]
    regime = data["regime"].upper()
    crash = data["crash_probability"]

    regime_emoji = {
        "LOW": "🟢",
        "NEUTRAL": "🟡",
        "HIGH": "🔴"
    }.get(regime, "")

    pct_txt = f"{pct:.1f}%" if pct is not None else "—"

    msg = (
f"📊 VOLATILITY STRATEGY REPORT\n\n"
f"🗓 Date: {ts}\n\n"
f"🧨 INDIA VIX: {v:.2f}\n"
f"Percentile: {pct_txt}\n"
f"Market Regime: {regime} {regime_emoji}\n\n"
f"💥 Crash Probability: {crash}%\n\n"

f"📌 NIFTY: {close:,.2f}\n"
f"ATR %: {atr:.2f}%\n\n"
f"🎯 Recommended Strategies\n"
    )

    for name, timing, note in data["strategies"]:
        msg += (
            f"• {name} — {timing}\n"
            f"  ⤷ {note}\n"
        )

    return msg.strip()


# ============================================================
# 9. TEST HOOK
# ============================================================

if __name__ == "__main__":
    #print(format_vol_report_telegram(analyze_vix_and_nifty()))
    # CLI preview
    print(format_vol_report_cli(analyze_vix_and_nifty()))

