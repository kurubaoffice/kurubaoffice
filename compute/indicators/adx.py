import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from ta.trend import ADXIndicator


def calculate_adx(symbol, period="9mo", interval="1d", window=14, testing=False):
    try:
        df = yf.download(symbol, period=period, interval=interval, auto_adjust=False)

        # Flatten if MultiIndex
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Remove column name if present
        df.columns.name = None

        # Lowercase for consistency
        df.columns = [col.lower() for col in df.columns]
        print(f"[INFO] Data downloaded for {symbol}: {df.shape[0]} rows")


        required_cols = ['high', 'low', 'close']
        if not all(col in df.columns for col in required_cols):
            raise KeyError(f"[ERROR] Required OHLC columns missing. Found: {df.columns}")

        adx = ADXIndicator(high=df['high'], low=df['low'], close=df['close'], window=window)
        df['adx'] = adx.adx()
        df['+di'] = adx.adx_pos()
        df['-di'] = adx.adx_neg()

        if testing:
            print(df[['close', 'adx', '+di', '-di']].tail(10).round(2))
            df.tail(60).plot(
                y=['adx', '+di', '-di'],
                figsize=(12, 6),
                title=f"ADX ({window}) - {symbol}"
            )
            plt.grid(True)
            plt.show()

        # ✅ Meaningful Summary
        last_row = df.iloc[-1]
        adx_value = last_row['adx']
        plus_di = last_row['+di']
        minus_di = last_row['-di']

        strength = (
            "Strong" if adx_value > 25
            else "Weak" if adx_value < 20
            else "Moderate"
        )
        direction = (
            "Bullish" if plus_di > minus_di
            else "Bearish" if minus_di > plus_di
            else "Sideways"
        )

        signal = "Buy" if direction == "Bullish" and strength == "Strong" else (
                 "Sell" if direction == "Bearish" and strength == "Strong" else "Hold")

        result = {
            "indicator": "ADX",
            "adx_value": round(adx_value, 2),
            "+DI": round(plus_di, 2),
            "-DI": round(minus_di, 2),
            "trend_strength": strength,
            "trend_direction": direction,
            "current_signal": signal
        }

        return df, result

    except Exception as e:
        print(f"[ERROR] ADX calculation failed: {e}")
        return pd.DataFrame(), {}


if __name__ == "__main__":
    symbol = "RELIANCE.NS"
    testing = True  # Set False when used in engine

    df, summary = calculate_adx(symbol, window=14, testing=testing)

    if df.empty or 'adx' not in df.columns:
        print(f"⚠️ Missing ADX data in DataFrame for {symbol}")
    else:
        print(f"[✅] ADX result for {symbol}:")
        for k, v in summary.items():
            print(f"   {k}: {v}")
