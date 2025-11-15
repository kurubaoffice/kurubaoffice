import pandas as pd
from fetcher.fetch_banknifty_option_chain import fetch_banknifty_option_chain
from compute.options.option_chain_utils import *

from fetcher.fetch_banknifty_option_chain import fetch_banknifty_option_chain


def test_option_chain_fetch():
    df =fetch_banknifty_option_chain()

    # Basic sanity checks
    assert df is not None
    assert len(df) > 0
    assert "oi" in df.columns
    assert "strike" in df.columns

df = fetch_banknifty_option_chain()

expiry = get_current_weekly_expiry(df)
print("Expiry:", expiry)

atm = get_atm_strike(df)
print("ATM Strike:", atm)

df2 = filter_df_for_selected_expiry(df, expiry)
print("Rows for expiry:", len(df2))

df3 = filter_strike_range(df2, atm)
print("Rows in ±5 strikes:", len(df3))
