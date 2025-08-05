import pandas as pd

def apply_indicators(df, config=None):
    from compute.indicators.rsi import calculate_rsi
    from compute.indicators.macd import calculate_macd
    from compute.indicators.supertrend import calculate_supertrend
    from compute.indicators.ema import calculate_ema
    from compute.indicators.atr import apply_atr
    from compute.indicators.bollinger import calculate_bollinger_bands
    from compute.indicators.adx import calculate_adx_from_df
    try:
        df = calculate_bollinger_bands(df)
        print("[DEBUG] BB df type:", type(df))
    except Exception as e:
        print(f"[ERROR] Bollinger Bands failed: {e}")
    try:
        df = calculate_rsi(df)
        print("[DEBUG] After RSI:", type(df))
    except Exception as e:
        print(f"[ERROR] RSI failed: {e}")

    try:
        df = calculate_macd(df)
        print("[DEBUG] After MACD:", type(df))
    except Exception as e:
        print(f"[ERROR] MACD failed: {e}")

    try:
        df = calculate_supertrend(df)
        print("[DEBUG] After Supertrend:", type(df))
        if not isinstance(df, pd.DataFrame):
            raise TypeError("Supertrend returned non-DataFrame")
        # ✅ Add signal column based on supertrend trend column
        if 'supertrend' in df.columns:
            df['supertrend_signal'] = df['supertrend'].apply(lambda x: True if x == 'Buy' else False if x == 'Sell' else None)
    except Exception as e:
        print(f"[ERROR] Supertrend failed: {e}")

    try:
        df = calculate_ema(df, length=20)
        df = calculate_ema(df, length=50)
        df = calculate_ema(df, length=200)
        print("[DEBUG] After EMA:", type(df))
    except Exception as e:
        print(f"[ERROR] EMA failed: {e}")

    try:
        df = apply_atr(df)
        print("[DEBUG] After ATR:", type(df))
    except Exception as e:
        print(f"[ERROR] ATR failed: {e}")

    try:
        df = calculate_bollinger_bands(df)
        print("[DEBUG] After BB:", type(df))
    except Exception as e:
        print(f"[ERROR] Bollinger Bands failed: {e}")

    try:
        df, _ = calculate_adx_from_df(df)
        print("[DEBUG] After ADX:", type(df))
    except Exception as e:
        print(f"[ERROR] ADX failed: {e}")

    return df
