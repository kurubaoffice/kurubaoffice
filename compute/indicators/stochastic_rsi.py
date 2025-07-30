import os
import json
import yfinance as yf
import numpy as np
import pandas as pd

def compute_stochastic_rsi(df, rsi_period=14, stoch_period=14, smooth_k=3, smooth_d=3):
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=rsi_period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=rsi_period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    min_rsi = rsi.rolling(window=stoch_period).min()
    max_rsi = rsi.rolling(window=stoch_period).max()

    stoch_rsi = (rsi - min_rsi) / (max_rsi - min_rsi)
    stoch_k = stoch_rsi.rolling(window=smooth_k).mean()
    stoch_d = stoch_k.rolling(window=smooth_d).mean()

    df['stoch_rsi'] = stoch_rsi
    df['stoch_k'] = stoch_k
    df['stoch_d'] = stoch_d

    return df.dropna()

def interpret_stochastic_rsi(latest_row):
    k = float(latest_row['stoch_k'].iloc[0])
    d = float(latest_row['stoch_d'].iloc[0])

    if k > 0.8 and d > 0.8:
        condition = "Overbought"
    elif k < 0.2 and d < 0.2:
        condition = "Oversold"
    else:
        condition = "Neutral zone"

    if k > d:
        crossover = "Bullish crossover "
        bullish = True
        bearish = False
    elif k < d:
        crossover = "Bearish crossover "
        bullish = False
        bearish = True
    else:
        crossover = "No clear crossover"
        bullish = False
        bearish = False

    signal_summary = {
        "stoch_rsi_k": round(k, 3),
        "stoch_rsi_d": round(d, 3),
        "condition": condition,
        "crossover": crossover,
        "final_signal": f"{condition} with {crossover}",
        "is_bullish": bullish if condition == "Oversold" else False,
        "is_bearish": bearish if condition == "Overbought" else False
    }
    return signal_summary

def save_signal_json(symbol, signal_data):
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    output_dir = os.path.join(DATA_DIR, 'processed', 'indicators')
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, f"{symbol.replace('.NS', '').lower()}_stochrsi.json")
    with open(output_path, 'w') as f:
        json.dump(signal_data, f, indent=4)

    print(f"\n✅ Stochastic RSI signal saved to {output_path}")

def main(symbol="RELIANCE.NS"):
    print(f"\n🔍 Fetching data for {symbol}...")
    df = yf.download(symbol, period="9mo", interval="1d", auto_adjust=False)[['Close']]
    df = compute_stochastic_rsi(df)
    latest = df.iloc[[-1]]
    summary = interpret_stochastic_rsi(latest.iloc[0])

    print(f"\n📊 Stochastic RSI Summary for {symbol}:")
    print(f"📈 Condition: {summary['condition']}")
    print(f"🔄 Crossover: {summary['crossover']}")
    print(f"📢 Final Signal: **{summary['final_signal']}**")
    print(f"✅ Bullish: {summary['is_bullish']}, Bearish: {summary['is_bearish']}")

    save_signal_json(symbol, summary)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        main()
