import pandas as pd


def get_current_weekly_expiry(df: pd.DataFrame) -> str:
    """
    Pick the nearest upcoming expiry.
    Works for BankNifty weekly-expiries.
    """
    expiries = sorted(df["expiry"].unique(), key=lambda x: pd.to_datetime(x, dayfirst=True))
    return expiries[0]   # earliest expiry


def get_atm_strike(df: pd.DataFrame) -> int:
    """
    ATM = closest strike to the spot price.
    """
    spot = df["spot"].iloc[0]
    df["dist"] = abs(df["strike"] - spot)
    atm = df.loc[df["dist"].idxmin()]["strike"]
    df.drop(columns=["dist"], inplace=True, errors="ignore")
    return int(atm)


def filter_df_for_selected_expiry(df: pd.DataFrame, expiry: str) -> pd.DataFrame:
    """Filter rows for selected expiry only."""
    return df[df["expiry"] == expiry].reset_index(drop=True)


def filter_strike_range(df: pd.DataFrame, atm: int, window: int = 5) -> pd.DataFrame:
    """
    Keep strikes ± window around ATM.
    Example: ATM=45000, window=5 → 44750–45250
    """
    min_strike = atm - window * 100
    max_strike = atm + window * 100
    return df[(df["strike"] >= min_strike) & (df["strike"] <= max_strike)].reset_index(drop=True)
