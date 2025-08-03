# compute/apply_indicators.py

from compute.indicators.rsi import calculate_rsi
from compute.indicators.macd import calculate_macd
from compute.indicators.supertrend import calculate_supertrend
from compute.indicators.ema import calculate_ema
# Add more as needed

def apply_indicators(df, config=None):
    """
    Applies a standard set of indicators to the given OHLCV dataframe.
    You can pass a config dict to control which indicators to apply and with what params.
    """
    df = calculate_rsi(df)
    df = calculate_macd(df)
    df = calculate_supertrend(df)
    df = calculate_ema(df, length=20)
    df = calculate_ema(df, length=50)
    df = calculate_ema(df, length=200)
    # Add more as required
    return df
