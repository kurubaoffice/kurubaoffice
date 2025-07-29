import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import ta


def calculate_supertrend(symbol, period="9mo", interval="1d", window=7, multiplier=3, testing=False):
    try:
        df = yf.download(symbol, period=period, interval=interval)
        print(f"[INFO] Data downloaded for {symbol}: {df.shape[0]} rows")

        # ✅ Flatten MultiIndex if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0].lower() for col in df.columns]
        else:
            df.columns = [col.lower() if isinstance(col, str) else col for col in df.columns]

        # ✅ Check OHLC columns
        required_cols = ['high', 'low', 'close']
        if not all(col in df.columns for col in required_cols):
            raise KeyError(f"[ERROR] Required OHLC columns missing. Found: {df.columns}")

        # ✅ Calculate ATR
        atr = ta.volatility.AverageTrueRange(
            high=df['high'], low=df['low'], close=df['close'], window=window
        )
        atr_val = atr.average_true_range()

        # ✅ Supertrend Logic
        hl2 = (df['high'] + df['low']) / 2
        upperband = hl2 + (multiplier * atr_val)
        lowerband = hl2 - (multiplier * atr_val)

        direction = [True]  # First assumed bullish
        for i in range(1, len(df)):
            if df['close'].iloc[i] > upperband.iloc[i - 1]:
                direction.append(True)
            elif df['close'].iloc[i] < lowerband.iloc[i - 1]:
                direction.append(False)
            else:
                direction.append(direction[-1])

        df['supertrend_direction'] = direction
        df['supertrend_upper'] = upperband
        df['supertrend_lower'] = lowerband

        if testing:
            print(df[['close', 'supertrend_upper', 'supertrend_lower', 'supertrend_direction']].tail(10).round(2))
            df.tail(60).plot(
                y=['close', 'supertrend_upper', 'supertrend_lower'],
                figsize=(12, 6),
                title=f"Supertrend ({window}, {multiplier}) - {symbol}"
            )
            plt.grid(True)
            plt.show()
            # ✅ Extract Meaningful Info for Return
        last_row = df.iloc[-1]
        direction = "Bullish" if last_row['supertrend_direction'] else "Bearish"
        upper = last_row['supertrend_upper']
        lower = last_row['supertrend_lower']
        close = last_row['close']

        # Determine signal
        prev = df.iloc[-2]
        if prev['supertrend_direction'] != last_row['supertrend_direction']:
            signal = "Buy" if last_row['supertrend_direction'] else "Sell"
        else:
            signal = "Hold"

        # Trend strength (optional logic)
        band_distance = abs(upper - lower)
        strength = "Strong" if band_distance / close > 0.03 else "Neutral"

        result = {
            "supertrend_direction": direction,
            "current_signal": signal,
            "trend_strength": strength,
            "indicator": "Supertrend",
            "latest_close": round(close, 2),
            "upper_band": round(upper, 2),
            "lower_band": round(lower, 2),
        }
        return result  # ✅ Return this dictionary instead of df

    except Exception as e:
        print(f"[ERROR] Supertrend calculation failed: {e}")
        return pd.DataFrame()


if __name__ == "__main__":
    symbol = "HDFCBANK.NS"
    testing = True  # Toggle off when integrating into Tidder engine

    result = calculate_supertrend(symbol, window=7, multiplier=3, testing=testing)

    if not result or 'supertrend_direction' not in result:
        print(f"⚠️ Missing Supertrend result for {symbol}")
    else:
        print(f"[✅] Supertrend result for {symbol}:")
        for k, v in result.items():
            print(f"   {k}: {v}")
