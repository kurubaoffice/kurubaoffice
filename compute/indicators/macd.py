# compute/indicators/macd.py

from ta.trend import MACD
import pandas as pd

def calculate_macd(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds MACD, Signal Line, and MACD Histogram to the DataFrame.

    Parameters:
        df (pd.DataFrame): DataFrame with at least a 'close' column.

    Returns:
        pd.DataFrame: Modified DataFrame with MACD columns.
    """
    try:
        if 'close' not in df.columns:
            raise ValueError("Missing 'close' column for MACD")

        df = df.dropna(subset=['close'])  # clean up missing data

        macd = MACD(close=df['close'], window_slow=26, window_fast=12, window_sign=9)

        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['macd_histogram'] = macd.macd_diff()

        df['macd_signal_label'] = "No Signal"
        df.loc[df['macd'] > df['macd_signal'], 'macd_signal_label'] = "Bullish Crossover"
        df.loc[df['macd'] < df['macd_signal'], 'macd_signal_label'] = "Bearish Crossover"

        return df

    except Exception as e:
        print(f"[ERROR] MACD calculation failed: {e}")
        return df
