# fetcher/fetch_incremental_price.py

from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
from storage.db_writer import get_latest_date_for_symbol, insert_price_data


def fetch_incremental_price_data(symbol):
    symbol = symbol.upper()
    last_date = get_latest_date_for_symbol(symbol)

    if last_date:
        start_date = last_date + timedelta(days=1)
    else:
        start_date = datetime(2022, 1, 1)

    end_date = datetime.today()

    # 🛡️ Ensure end_date is valid and not on a weekend
    end_date = min(end_date, datetime.now())
    if end_date.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        end_date -= timedelta(days=end_date.weekday() - 4)  # Move to last Friday

    if start_date >= end_date:
        print(f"[SKIP] {symbol} is already up-to-date or date range invalid.")
        return

    try:
        df = yf.download(
            f"{symbol}.NS",
            start=start_date.strftime('%Y-%m-%d'),
            end=end_date.strftime('%Y-%m-%d'),
            progress=False
        )
    except Exception as e:
        print(f"[ERROR] Failed to download {symbol}: {e}")
        return

    if df.empty:
        print(f"[EMPTY] No new data for {symbol} from {start_date.date()} to {end_date.date()}")
        return

    df.reset_index(inplace=True)
    df['symbol'] = symbol
    df.rename(columns={
        'Date': 'date',
        'Open': 'open',
        'High': 'high',
        'Low': 'low',
        'Close': 'close',
        'Adj Close': 'adj_close',
        'Volume': 'volume'
    }, inplace=True)

    df = df[['date', 'symbol', 'open', 'high', 'low', 'close', 'adj_close', 'volume']]

    # Save raw CSV
    df.to_csv(f"data/raw/{symbol}_{start_date.date()}_to_{end_date.date()}.csv", index=False)

    # Save to DB
    insert_price_data(symbol, df)

    print(f"[DONE] {symbol} price data saved ({len(df)} rows).")
