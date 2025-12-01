# compute/indicators/nlp_insights.py

import numpy as np

def compute_hold_or_sell(df):
    """HOLD / SELL suggestion using supertrend + RSI + MACD."""
    if df is None or len(df) < 5:
        return "Insufficient data to decide."

    last = df.iloc[-1]
    trend = last.get("supertrend_signal", 0)
    rsi = last.get("rsi", 50)
    macd = last.get("macd", 0)

    score = 0
    score += trend * 2
    score += 1 if macd > 0 else -1
    score += 1 if rsi < 70 else -1

    if score >= 2:
        return "Trend is positive. HOLD with bullish bias."
    elif score <= -2:
        return "Trend looks weak. Consider SELL or booking profits."
    else:
        return "Sideways trend. HOLD with caution."


def compute_future_outlook(df):
    """Project future high/low using ATR."""
    if df is None or len(df) < 5:
        return "Outlook unclear due to limited data."

    last = df.iloc[-1]
    trend = last.get("supertrend_signal", 0)
    atr = last.get("atr", 0)
    close = last["close"]

    high_proj = round(close + (1.5 * atr), 2)
    low_proj = round(close - (1.5 * atr), 2)

    outlook = "Bullish" if trend == 1 else "Bearish" if trend == -1 else "Neutral"

    return (
        f"Outlook: **{outlook}**\n"
        f"Projected High: ₹{high_proj}\n"
        f"Projected Low: ₹{low_proj}"
    )


def compute_stoploss(df):
    """Suggest SL using ATR."""
    if df is None or len(df) < 5:
        return "No SL suggestion possible."

    last = df.iloc[-1]
    atr = last.get("atr", 0)
    close = last["close"]

    sl = round(close - (1.2 * atr), 2)
    return f"Suggested Stoploss: ₹{sl}"


def compute_target(df):
    """Suggest target using ATR."""
    if df is None or len(df) < 5:
        return "No target suggestion possible."

    last = df.iloc[-1]
    atr = last.get("atr", 0)
    close = last["close"]

    target = round(close + (1.8 * atr), 2)
    return f"Suggested Target: ₹{target}"


def compute_basic(query):
    """Basic rule-based sentiment on user question."""
    q = query.lower()

    if any(x in q for x in ["good", "up", "buy", "bull"]):
        return "Positive tone detected."
    if any(x in q for x in ["down", "bad", "sell", "bear"]):
        return "Negative tone detected."
    return "Neutral tone detected."
