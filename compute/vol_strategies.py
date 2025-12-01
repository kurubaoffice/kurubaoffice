import os
import pandas as pd
import datetime as dt

from fetcher.fetch_india_vix import fetch_india_vix


# ============================================================
# CONFIG
# ============================================================

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT)  # Tidder2.0/

VIX_HISTORY_PATH = os.path.join(DATA_DIR, "VIX_HISTORY.csv")
NIFTY_PATH = os.path.join(DATA_DIR, "data", "processed", "index", "NIFTY.csv")

os.makedirs(DATA_DIR, exist_ok=True)


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
    vix_series = update_vix_history(live_vix)
    vix_pct = compute_vix_percentile(vix_series) if len(vix_series) >= 20 else None

    # Load local NIFTY
    nifty = load_nifty()

    # ATR%
    atr_pct = compute_atr_pct(nifty)

    # Regime
    regime = detect_regime(live_vix, vix_pct)

    # Strategies
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

