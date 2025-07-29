import os
import json
import pandas as pd
import yfinance as yf
from datetime import datetime

def calculate_cci(df, window=20):
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    moving_avg = typical_price.rolling(window=window).mean()
    mean_deviation = typical_price.rolling(window=window).apply(lambda x: (abs(x - x.mean())).mean())
    cci = (typical_price - moving_avg) / (0.015 * mean_deviation)
    df['cci'] = cci
    return df

def interpret_cci(latest_cci):
    signal = ""
    bullish = bearish = False

    if latest_cci > 100:
        signal = "Overbought – Possible trend reversal or strong uptrend"
        bearish = True
    elif latest_cci < -100:
        signal = "Oversold – Possible trend reversal or strong downtrend"
        bullish = True
    else:
        signal = "Neutral – No strong trend signal"

    return signal, bullish, bearish

def analyze_cci(symbol, window=20, plot=False):
    print(f"\n🔍 Fetching data for {symbol}...")

    df = yf.download(symbol, period="6mo", interval="1d", auto_adjust=False)[['High', 'Low', 'Close']]
    df = calculate_cci(df, window=window)
    latest_row = df.dropna().iloc[-1]
    # Handle single-value series deprecation warning
    cci_raw = latest_row['cci']
    latest_cci = float(cci_raw.iloc[0] if isinstance(cci_raw, pd.Series) else cci_raw)


    signal, bullish, bearish = interpret_cci(latest_cci)

    print(f"\n📊 CCI Summary for {symbol}:")
    print(f"🧮 Latest CCI: {latest_cci:.2f}")
    print(f"📢 Final Signal: **{signal}**")
    print(f"✅ Bullish: {bullish}, Bearish: {bearish}")

    # Save signal
    summary = {
        "symbol": symbol,
        "indicator": "CCI",
        "cci_value": round(latest_cci, 2),
        "signal": signal,
        "bullish": bullish,
        "bearish": bearish,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # Save JSON to global data folder
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # Tidder2.0/
    output_dir = os.path.join(BASE_DIR, 'data', 'processed', 'indicators')
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, f"{symbol.replace('.NS', '').lower()}_cci.json")

    with open(output_path, 'w') as f:
        json.dump(summary, f, indent=4)

    print(f"\n✅ CCI signal saved to {output_path}")

    # Optional plot (disabled by default)
    if plot:
        import matplotlib.pyplot as plt
        df[['cci']].plot(title=f"CCI - {symbol}")
        plt.axhline(100, color='r', linestyle='--')
        plt.axhline(-100, color='g', linestyle='--')
        plt.show()

if __name__ == "__main__":
    analyze_cci("RELIANCE.NS", plot=False)
