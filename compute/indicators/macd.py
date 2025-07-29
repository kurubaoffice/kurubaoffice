import yfinance as yf
import pandas as pd
from ta.trend import MACD

def calculate_macd(symbol, period="6mo", interval="1d"):
    try:
        df = yf.download(symbol, period=period, interval=interval, auto_adjust=False)
        print(f"[INFO] Data downloaded for {symbol}: {df.shape[0]} rows")

        # Flatten MultiIndex columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        print(f"[DEBUG] Columns in DataFrame: {df.columns.tolist()}")

        # Check if 'Close' is present
        if 'Close' not in df.columns:
            raise KeyError(df.columns)

        df = df.dropna(subset=['Close'])
        close_series = df['Close']

        # Ensure 1D Series
        if isinstance(close_series, pd.DataFrame):
            close_series = close_series.squeeze()

        # MACD calculation
        macd = MACD(close=close_series, window_slow=26, window_fast=12, window_sign=9)
        df['MACD'] = macd.macd()
        df['Signal_Line'] = macd.macd_signal()
        df['MACD_Histogram'] = macd.macd_diff()

        # Interpret MACD signal
        df['MACD_Signal'] = "No Signal"
        df.loc[df['MACD'] > df['Signal_Line'], 'MACD_Signal'] = "Bullish Crossover"
        df.loc[df['MACD'] < df['Signal_Line'], 'MACD_Signal'] = "Bearish Crossover"

        print(df[['Close', 'MACD', 'Signal_Line', 'MACD_Signal']].tail(10).round(2))
        return df

    except Exception as e:
        print(f"[ERROR] MACD calculation failed: {e}")
        return pd.DataFrame()
import matplotlib.pyplot as plt

def plot_macd(df, symbol):
    if df.empty or 'MACD' not in df.columns:
        print("[WARN] No data to plot.")
        return

    plt.figure(figsize=(14, 7))
    plt.title(f"MACD Indicator for {symbol}")
    plt.plot(df.index, df['MACD'], label='MACD', color='blue', linewidth=1.5)
    plt.plot(df.index, df['Signal_Line'], label='Signal Line', color='orange', linewidth=1.5)
    plt.bar(df.index, df['MACD_Histogram'], label='Histogram', color='gray', alpha=0.4)

    # Mark Bullish and Bearish Crossovers
    bullish = df[df['MACD_Signal'] == 'Bullish Crossover']
    bearish = df[df['MACD_Signal'] == 'Bearish Crossover']

    plt.scatter(bullish.index, bullish['MACD'], label='Bullish', marker='^', color='green', s=80)
    plt.scatter(bearish.index, bearish['MACD'], label='Bearish', marker='v', color='red', s=80)

    plt.legend(loc='upper left')
    plt.grid(True)
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    symbol = "EPACK.NS"
    df = calculate_macd(symbol)
    plot_macd(df, symbol)

    if df.empty or not {'MACD', 'Signal_Line', 'MACD_Signal'}.issubset(df.columns):
        print(f"⚠️ Missing MACD data in DataFrame for {symbol}")
    else:
        print(f"[✅] MACD successfully calculated for {symbol}")
