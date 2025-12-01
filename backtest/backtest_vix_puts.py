# backtest_vix_puts.py
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import timedelta

# NOTE: replace tickers/data with reliable intraday or daily option data if available
VIX_TICKER = '^VIX'  # replace with India VIX source
NIFTY_TICKER = '^NSEI'

vix = yf.download(VIX_TICKER, period='3y', interval='1d', progress=False)
nifty = yf.download(NIFTY_TICKER, period='3y', interval='1d', progress=False)

# simple event: when VIX close <= 12, enter a 21-day ATM put equivalent
vix['signal'] = (vix['Close'] <= 12).astype(int)

trades = []
for date, row in vix.iterrows():
    if row['signal'] == 1:
        entry_date = date
        exit_date = entry_date + pd.Timedelta(days=21)
        if exit_date not in nifty.index:
            # find next available trading day
            exit_date = nifty.index[nifty.index.get_loc(exit_date, method='bfill')]
        try:
            entry_price = nifty.loc[entry_date]['Close']
            exit_price = nifty.loc[exit_date]['Close']
        except Exception:
            continue
        ret = (exit_price - entry_price) / entry_price
        trades.append({'entry': entry_date, 'exit': exit_date, 'entry_price': entry_price, 'exit_price': exit_price, 'ret': ret})

trades_df = pd.DataFrame(trades)
print(trades_df.describe())
print('Total trades:', len(trades_df))
print('Avg return per trade (underlying move):', trades_df['ret'].mean())