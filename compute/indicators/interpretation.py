# compute/indicators/interpretation.py

def interpret_signals(df):
    latest = df.iloc[-1]

    signals = {}

    # --- Trend direction (based on Supertrend) ---
    if "supertrend" in latest:
        signals["Trend"] = "Bullish" if latest["supertrend"] else "Bearish"

    # --- RSI Interpretation ---
    if "rsi_14" in latest:
        rsi = latest["rsi_14"]
        if rsi > 70:
            signals["RSI"] = f"Overbought ({rsi:.1f})"
        elif rsi < 30:
            signals["RSI"] = f"Oversold ({rsi:.1f})"
        else:
            signals["RSI"] = f"Neutral ({rsi:.1f})"

    # --- MACD Signal ---
    if "macd" in latest and "macd_signal" in latest:
        if latest["macd"] > latest["macd_signal"]:
            signals["MACD"] = "Bullish crossover"
        else:
            signals["MACD"] = "Bearish crossover"

    # --- Price vs EMA20/EMA50 ---
    if "ema_20" in latest and "close" in latest:
        signals["Price vs EMA20"] = "Above" if latest["close"] > latest["ema_20"] else "Below"

    if "ema_50" in latest and "close" in latest:
        signals["Price vs EMA50"] = "Above" if latest["close"] > latest["ema_50"] else "Below"

    return signals
