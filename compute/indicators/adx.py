import pandas as pd
import matplotlib.pyplot as plt
from ta.trend import ADXIndicator

def calculate_adx_from_df(df, window=14, symbol=None, testing=False):
    """
    Calculate ADX and return enriched DataFrame + summary dict.

    Args:
        df (pd.DataFrame): Must contain 'high', 'low', 'close' (lowercase).
        window (int): Window for ADX calculation.
        symbol (str): Optional, for display in testing plots.
        testing (bool): If True, prints and plots ADX details.

    Returns:
        df (pd.DataFrame): With ['adx', '+di', '-di'] columns.
        dict: Summary including trend strength, direction, and signal.
    """
    try:
        # --- Check for required columns ---
        required_cols = ['high', 'low', 'close']
        if not all(col in df.columns for col in required_cols):
            raise KeyError(f"[ERROR] Required OHLC columns missing. Found: {df.columns}")

        # --- Calculate ADX and directional indicators ---
        adx = ADXIndicator(high=df['high'], low=df['low'], close=df['close'], window=window)
        df['adx'] = adx.adx()
        df['+di'] = adx.adx_pos()
        df['-di'] = adx.adx_neg()

        # --- Optional Debug Logging ---
        if testing:
            print("[DEBUG] Last 10 rows of ADX data:")
            print(df[['close', 'adx', '+di', '-di']].tail(10).round(2))
            df.tail(60).plot(
                y=['adx', '+di', '-di'],
                figsize=(12, 6),
                title=f"ADX ({window}) - {symbol or 'Symbol'}"
            )
            plt.grid(True)
            plt.show()

        # --- Get Last Valid Row (avoid NaN from .iloc[-1]) ---
        latest_valid = df.dropna(subset=['adx', '+di', '-di'])
        if latest_valid.empty:
            raise ValueError("[ERROR] No valid ADX data to interpret.")

        latest = latest_valid.iloc[-1]
        adx_val = latest['adx']
        plus_di = latest['+di']
        minus_di = latest['-di']

        # --- Compute Interpretation ---
        strength = (
            "Strong" if adx_val > 25 else
            "Weak" if adx_val < 20 else
            "Moderate"
        )
        direction = (
            "Bullish" if plus_di > minus_di else
            "Bearish" if minus_di > plus_di else
            "Sideways"
        )
        signal = (
            "Buy" if strength == "Strong" and direction == "Bullish" else
            "Sell" if strength == "Strong" and direction == "Bearish" else
            "Hold"
        )

        summary = {
            "indicator": "ADX",
            "adx_value": round(adx_val, 2),
            "+DI": round(plus_di, 2),
            "-DI": round(minus_di, 2),
            "trend_strength": strength,
            "trend_direction": direction,
            "current_signal": signal
        }

        return df, summary

    except Exception as e:
        print(f"[ERROR] ADX calculation failed: {e}")
        return df, {
            "indicator": "ADX",
            "adx_value": None,
            "+DI": None,
            "-DI": None,
            "trend_strength": "N/A",
            "trend_direction": "N/A",
            "current_signal": "N/A"
        }
