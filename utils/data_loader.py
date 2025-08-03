import yfinance as yf
import pandas as pd

def get_stock_historical(symbol, period="3mo", interval="1d"):
    df = yf.download(symbol, period=period, interval=interval)
    df.reset_index(inplace=True)
    df.columns = [c.lower() for c in df.columns]
    return df

def get_index_historical(symbol="^NSEI", period="3mo", interval="1d"):
    df = yf.download(symbol, period=period, interval=interval)
    df.reset_index(inplace=True)
    df.columns = [c.lower() for c in df.columns]
    return df
