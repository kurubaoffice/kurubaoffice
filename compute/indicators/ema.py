# compute/indicators/ema.py

def calculate_ema(df, length=20, column='close'):
    """
    Adds an EMA column to the dataframe.
    Args:
        df (pd.DataFrame): OHLCV dataframe with at least `column` (usually 'close').
        length (int): Period for EMA.
        column (str): Which column to apply EMA on.
    Returns:
        pd.DataFrame with new column: 'ema_<length>'
    """
    ema_col = f"ema_{length}"
    df[ema_col] = df[column].ewm(span=length, adjust=False).mean()
    return df
