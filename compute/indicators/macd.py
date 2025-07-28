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

if __name__ == "__main__":
    symbol = "HDFCBANK.NS"
    df = calculate_macd(symbol)

    if df.empty or not {'MACD', 'Signal_Line', 'MACD_Signal'}.issubset(df.columns):
        print(f"⚠️ Missing MACD data in DataFrame for {symbol}")
    else:
        print(f"[✅] MACD successfully calculated for {symbol}")
