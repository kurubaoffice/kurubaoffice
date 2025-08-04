# compute/indicators/ema.py

def calculate_ema(df, column="close", length=20):
    """
    Calculate Exponential Moving Average (EMA).

    Parameters:
        df (pd.DataFrame): DataFrame containing the OHLCV data.
        column (str): Column to calculate EMA on (default is 'close').
        length (int): Lookback period for EMA.

    Returns:
        pd.DataFrame with new column: 'ema_{length}'
    """
    ema_col = f"ema_{length}"
    if column not in df.columns:
        raise KeyError(f"'{column}' column not found in DataFrame. Available columns: {df.columns.tolist()}")

    df[ema_col] = df[column].ewm(span=length, adjust=False).mean()
    return df
