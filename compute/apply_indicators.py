import pandas as pd


def apply_indicators(df, config=None):
    from compute.indicators.rsi import calculate_rsi
    from compute.indicators.macd import calculate_macd
    from compute.indicators.supertrend import calculate_supertrend
    from compute.indicators.ema import calculate_ema

    try:
        df = calculate_rsi(df)
    except Exception as e:
        print(f"[ERROR] RSI failed: {e}")

    try:
        df = calculate_macd(df)
    except Exception as e:
        print(f"[ERROR] MACD failed: {e}")

    try:
        df = calculate_supertrend(df)
        if not isinstance(df, pd.DataFrame):
            raise TypeError("Supertrend returned non-DataFrame")
    except Exception as e:
        print(f"[ERROR] Supertrend failed: {e}")

    try:
        df = calculate_ema(df, length=20)
        df = calculate_ema(df, length=50)
        df = calculate_ema(df, length=200)
    except Exception as e:
        print(f"[ERROR] EMA failed: {e}")

    return df
