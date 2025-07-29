# compute/indicators/vwap.py

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

def fetch_price_data(symbol, period="30d", interval="1d"):
    print(f"🔍 Fetching data for {symbol}...")
    df = yf.download(symbol, period=period, interval=interval, progress=False, auto_adjust=False)
    df = df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
    return df

def calculate_vwap(df: pd.DataFrame) -> pd.DataFrame:
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    df['vwap'] = (typical_price * df['Volume']).cumsum() / df['Volume'].cumsum()
    return df

def analyze_vwap(symbol: str):
    df = fetch_price_data(symbol)
    if df.empty:
        return {"error": "No data available"}

    df = calculate_vwap(df)
    latest = df.tail(1)

    close_price = latest['Close'].values[0].item()
    vwap_price = latest['vwap'].values[0].item()

    result = {
        "symbol": symbol,
        "vwap": round(vwap_price, 2),
        "current_price": round(close_price, 2),
    }

    if close_price > vwap_price:
        result.update({
            "signal": "Bullish – Price above VWAP",
            "bullish": True,
            "bearish": False,
            "neutral": False
        })
    elif close_price < vwap_price:
        result.update({
            "signal": "Bearish – Price below VWAP",
            "bullish": False,
            "bearish": True,
            "neutral": False
        })
    else:
        result.update({
            "signal": "Neutral – Price equals VWAP",
            "bullish": False,
            "bearish": False,
            "neutral": True
        })

    return result

# Test the module
if __name__ == "__main__":
    output = analyze_vwap("RELIANCE.NS")
    print("\n📊 VWAP Analysis:")
    print(output)
