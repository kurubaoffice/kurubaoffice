import yfinance as yf
import pandas as pd
import numpy as np
import json
import os

def calculate_cmf(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    df = df.copy()
    df = df[['High', 'Low', 'Close', 'Volume']].dropna()

    high = df['High'].astype(float)
    low = df['Low'].astype(float)
    close = df['Close'].astype(float)
    volume = df['Volume'].astype(float)

    mf_multiplier = ((close - low) - (high - close)) / (high - low)
    mf_multiplier.replace([np.inf, -np.inf], 0, inplace=True)
    mf_multiplier.fillna(0, inplace=True)

    mf_volume = mf_multiplier * volume
    cmf = mf_volume.rolling(window=period).sum() / volume.rolling(window=period).sum()

    df['cmf'] = cmf
    return df

def interpret_cmf(latest_cmf: float) -> dict:
    signal = "Neutral – No clear trend"
    bullish = bearish = neutral = False

    if latest_cmf > 0.25:
        signal = "Strong Bullish – High buying pressure"
        bullish = True
    elif latest_cmf > 0.05:
        signal = "Mild Bullish – Some buying pressure"
        bullish = True
    elif latest_cmf < -0.25:
        signal = "Strong Bearish – High selling pressure"
        bearish = True
    elif latest_cmf < -0.05:
        signal = "Mild Bearish – Some selling pressure"
        bearish = True
    else:
        neutral = True

    return {
        "cmf_value": round(latest_cmf, 3),
        "signal": signal,
        "bullish": bullish,
        "bearish": bearish,
        "neutral": neutral
    }

def analyze_cmf(symbol: str):
    print(f"\n🔍 Fetching data for {symbol}...")
    df = yf.download(symbol, period="6mo", interval="1d", progress=False, auto_adjust=False)
    df = calculate_cmf(df)
    latest_cmf = df['cmf'].dropna().iloc[-1]

    result = interpret_cmf(latest_cmf)

    print(f"\n📊 CMF Summary for {symbol}:")
    print(f"🧮 Latest CMF: {result['cmf_value']}")
    print(f"📢 Final Signal: **{result['signal']}**")
    print(f"✅ Bullish: {result['bullish']}, Bearish: {result['bearish']}, Neutral: {result['neutral']}")

    # Save result
    base_symbol = symbol.replace(".NS", "").lower()
    output_path = os.path.join("data", "processed", "indicators", f"{base_symbol}_cmf.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(result, f, indent=4)

    print(f"\n✅ CMF signal saved to {output_path}")

# Run for test
if __name__ == "__main__":
    analyze_cmf("RELIANCE.NS")
