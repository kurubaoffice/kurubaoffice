import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import ta
import os

def send_alert(symbol, signal, direction):
    # Placeholder alert logic — replace with Telegram/Slack/etc. if needed
    alert_msg = f"[🚨 ALERT] {symbol} | Supertrend Signal: {signal} | Direction: {direction}"
    print(alert_msg)

def calculate_supertrend(symbol, period="9mo", interval="1d", window=7, multiplier=3, testing=False, save_result=True):
    try:
        df = yf.download(symbol, period=period, interval=interval, auto_adjust=False)
        df.index = pd.to_datetime(df.index)  # ✅ Fix for deprecated BDay warning
        print(f"[INFO] Data downloaded for {symbol}: {df.shape[0]} rows")

        # ✅ Clean columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0].lower() for col in df.columns]
        else:
            df.columns = [col.lower() if isinstance(col, str) else col for col in df.columns]

        required_cols = ['high', 'low', 'close']
        if not all(col in df.columns for col in required_cols):
            raise KeyError(f"[ERROR] Required OHLC columns missing. Found: {df.columns}")

        # ✅ ATR
        atr = ta.volatility.AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=window)
        atr_val = atr.average_true_range()

        # ✅ Bands & direction
        hl2 = (df['high'] + df['low']) / 2
        upperband = hl2 + (multiplier * atr_val)
        lowerband = hl2 - (multiplier * atr_val)

        direction = [True]
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

        # ✅ Show results
        if testing:
            print(df[['close', 'supertrend_upper', 'supertrend_lower', 'supertrend_direction']].tail(10).round(2))
            df.tail(60).plot(
                y=['close', 'supertrend_upper', 'supertrend_lower'],
                figsize=(12, 6),
                title=f"Supertrend ({window}, {multiplier}) - {symbol}"
            )
            plt.grid(True)
            plt.show()

        # ✅ Last row result
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]

        direction_str = "Bullish" if last_row['supertrend_direction'] else "Bearish"
        upper = last_row['supertrend_upper']
        lower = last_row['supertrend_lower']
        close = last_row['close']

        # Signal
        if prev_row['supertrend_direction'] != last_row['supertrend_direction']:
            signal = "Buy" if last_row['supertrend_direction'] else "Sell"
        else:
            signal = "Hold"

        # Strength
        band_distance = abs(upper - lower)
        strength = "Strong" if band_distance / close > 0.03 else "Neutral"

        result = {
            "symbol": symbol,
            "indicator": "Supertrend",
            "supertrend_direction": direction_str,
            "current_signal": signal,
            "trend_strength": strength,
            "latest_close": round(close, 2),
            "upper_band": round(upper, 2),
            "lower_band": round(lower, 2),
        }

        print(f"[✅] Supertrend result for {symbol}:")
        for k, v in result.items():
            print(f"   {k}: {v}")

        # ✅ Save result
        if save_result:
            output_path = "data/processed/technical_indicators.csv"
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            df_out = pd.DataFrame([result])
            header = not os.path.exists(output_path)
            df_out.to_csv(output_path, mode='a', index=False, header=header)
            print(f"[💾] Result saved to {output_path}")

        # ✅ Send alert if Buy/Sell
        if signal in ['Buy', 'Sell']:
            send_alert(symbol, signal, direction_str)

        return result

    except Exception as e:
        print(f"[ERROR] Supertrend calculation failed: {e}")
        return {}

# Entry
if __name__ == "__main__":
    symbol = "HDFCBANK.NS"
    testing = True
    result = calculate_supertrend(symbol, testing=testing)

    if not result:
        print(f"⚠️ Supertrend calculation incomplete for {symbol}")
