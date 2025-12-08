import pandas as pd


# ✅ RETURNS DATAFRAMES ONLY
def get_top_movers_df(df: pd.DataFrame, limit=10):
    if df is None or df.empty:
        return pd.DataFrame(), pd.DataFrame()

    df = df.sort_values("change_pct", ascending=False)

    gainers = df.head(limit)
    losers = df.tail(limit)

    return gainers, losers
