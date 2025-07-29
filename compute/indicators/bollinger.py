import os
import json
import warnings
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from ta.volatility import BollingerBands

warnings.simplefilter(action='ignore', category=FutureWarning)


from ta.volatility import BollingerBands

def calculate_bollinger_bands(df, window=20, std_dev=2):
    close_series = df["Close"]
    if isinstance(close_series, pd.DataFrame):  # If it's accidentally 2D
        close_series = close_series.squeeze()
    else:
        close_series = pd.Series(close_series).squeeze()

    # Initialize indicator
    indicator_bb = BollingerBands(close=close_series, window=window, window_dev=std_dev)

    # Extract bands
    df['bb_upper'] = indicator_bb.bollinger_hband().squeeze()
    df['bb_middle'] = indicator_bb.bollinger_mavg().squeeze()
    df['bb_lower'] = indicator_bb.bollinger_lband().squeeze()

    return df




def interpret_bollinger(df):
    latest_row = df.iloc[-1]
    close = float(latest_row["Close"])
    upper = float(latest_row["bb_upper"])
    middle = float(latest_row["bb_middle"])
    lower = float(latest_row["bb_lower"])

    signal = "Neutral – Price is within bands"
    bullish = bearish = breakout = squeeze = False

    if close > upper:
        signal = "Bearish Reversal Possible – Price broke above upper band"
        breakout = True
        bearish = True
    elif close < lower:
        signal = "Bullish Reversal Possible – Price broke below lower band"
        breakout = True
        bullish = True
    elif close > middle:
        signal = "Mild Bullish – Price above midline"
        bullish = True
    elif close < middle:
        signal = "Mild Bearish – Price below midline"
        bearish = True

    # Optional squeeze detection (volatility compression)
    df['bb_width'] = df['bb_upper'] - df['bb_lower']
    recent_widths = df['bb_width'].tail(20)
    if recent_widths.std() < 0.5 * recent_widths.mean():  # Heuristic
        squeeze = True

    return {
        "latest_close": round(close, 2),
        "bb_upper": round(upper, 2),
        "bb_middle": round(middle, 2),
        "bb_lower": round(lower, 2),
        "signal": signal,
        "bullish": bullish,
        "bearish": bearish,
        "breakout_detected": breakout,
        "squeeze_detected": squeeze
    }


def plot_bollinger(df, symbol):
    plt.figure(figsize=(12, 6))
    plt.plot(df.index, df['Close'], label='Close Price', color='blue')
    plt.plot(df.index, df['bb_upper'], label='Upper Band', color='red', linestyle='--')
    plt.plot(df.index, df['bb_middle'], label='Middle Band (SMA)', color='black', linestyle='--')
    plt.plot(df.index, df['bb_lower'], label='Lower Band', color='green', linestyle='--')
    plt.title(f"Bollinger Bands for {symbol}")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()


def analyze_bollinger(symbol, window=20, std_dev=2, plot=False):
    print(f"\n🔍 Fetching data for {symbol}...")
    df = yf.download(symbol, period="6mo", interval="1d")[['Close']]
    df = calculate_bollinger_bands(df, window=window, std_dev=std_dev)
    result = interpret_bollinger(df)

    print(f"\n📊 Bollinger Bands Summary for {symbol}:")
    print(f"📉 Close: {result['latest_close']}")
    print(f"🔺 Upper Band: {result['bb_upper']}, 🔻 Lower Band: {result['bb_lower']}")
    print(f"📢 Final Signal: **{result['signal']}**")
    print(f"✅ Bullish: {result['bullish']}, Bearish: {result['bearish']}, Breakout: {result['breakout_detected']}, Squeeze: {result['squeeze_detected']}")

    # Save JSON to global data folder
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # Tidder2.0/
    output_dir = os.path.join(BASE_DIR, 'data', 'processed', 'indicators')
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, f"{symbol.replace('.NS', '').lower()}_bollinger.json")
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=4)

    print(f"\n✅ Bollinger Bands signal saved to {output_path}")

    if plot:
        plot_bollinger(df, symbol)


if __name__ == "__main__":
    analyze_bollinger("RELIANCE.NS", plot=False)
