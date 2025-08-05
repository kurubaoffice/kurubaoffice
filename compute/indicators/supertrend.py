import pandas as pd
import ta


def calculate_supertrend(
    df: pd.DataFrame,
    window: int = 7,
    multiplier: float = 3.0,
    verbose: bool = False
) -> pd.DataFrame:
    """
    Calculate Supertrend indicator using ATR.

    Args:
        df (pd.DataFrame): DataFrame with 'high', 'low', 'close'.
        window (int): ATR window length.
        multiplier (float): Multiplier for ATR bands.
        verbose (bool): If True, prints debug info.

    Returns:
        pd.DataFrame: Original DataFrame with new columns:
                      ['supertrend', 'supertrend_upper', 'supertrend_lower']
    """
    try:
        # ✅ Validate input columns
        required_cols = ['high', 'low', 'close']
        if not all(col in df.columns for col in required_cols):
            raise ValueError(f"Missing required OHLC columns: {df.columns.tolist()}")

        # ✅ Compute ATR
        atr = ta.volatility.AverageTrueRange(
            high=df['high'], low=df['low'], close=df['close'], window=window
        ).average_true_range()

        hl2 = (df['high'] + df['low']) / 2
        upperband = hl2 + (multiplier * atr)
        lowerband = hl2 - (multiplier * atr)

        # Initialize direction series
        direction = [True]  # First value is bullish by default

        for i in range(1, len(df)):
            if df['close'].iloc[i] > upperband.iloc[i - 1]:
                direction.append(True)
            elif df['close'].iloc[i] < lowerband.iloc[i - 1]:
                direction.append(False)
            else:
                direction.append(direction[-1])  # Carry forward

        # ✅ Add to DataFrame
        df['supertrend'] = direction
        df['supertrend_upper'] = upperband
        df['supertrend_lower'] = lowerband

        if verbose:
            print(f"[INFO] Supertrend calculated for {len(df)} rows.")
            print(df[['close', 'supertrend', 'supertrend_upper', 'supertrend_lower']].tail())

        return df

    except Exception as e:
        print(f"[ERROR] Supertrend calculation failed: {e}")
        return df  # Gracefully return original DataFrame
