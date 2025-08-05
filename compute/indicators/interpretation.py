def interpret_signals(df):
    latest = df.iloc[-1]
    signals = {}

    # --- Supertrend ---
    if "supertrend" in latest:
        if latest["supertrend"]:
            signals["Supertrend"] = "Buy"
        else:
            signals["Supertrend"] = "Sell"

    # --- RSI Interpretation ---
    if "rsi_14" in latest:
        rsi = latest["rsi_14"]
        if rsi > 70:
            signals["RSI"] = f"Overbought ({rsi:.1f})"
            signals["RSI_Signal"] = "Bearish"
        elif rsi < 30:
            signals["RSI"] = f"Oversold ({rsi:.1f})"
            signals["RSI_Signal"] = "Bullish"
        else:
            signals["RSI"] = f"Neutral ({rsi:.1f})"
            signals["RSI_Signal"] = "Neutral"

    # --- MACD Signal ---
    if "macd" in latest and "macd_signal" in latest:
        if latest["macd"] > latest["macd_signal"]:
            signals["MACD"] = "Bullish crossover"
            signals["MACD_Signal"] = "Bullish"
        else:
            signals["MACD"] = "Bearish crossover"
            signals["MACD_Signal"] = "Bearish"

    # --- Price vs EMA ---
    if "ema_20" in latest and "close" in latest:
        signals["EMA20"] = "Above" if latest["close"] > latest["ema_20"] else "Below"
        signals["EMA20_Signal"] = "Bullish" if latest["close"] > latest["ema_20"] else "Bearish"

    if "ema_50" in latest and "close" in latest:
        signals["EMA50"] = "Above" if latest["close"] > latest["ema_50"] else "Below"
        signals["EMA50_Signal"] = "Bullish" if latest["close"] > latest["ema_50"] else "Bearish"

    # --- ADX Strength (if available) ---
    if "adx" in latest:
        adx_val = latest["adx"]
        if adx_val >= 20:
            signals["ADX"] = f"Strong ({adx_val:.1f})"
            signals["ADX_Signal"] = "Bullish"
        else:
            signals["ADX"] = f"Weak ({adx_val:.1f})"
            signals["ADX_Signal"] = "Neutral"

    return signals
