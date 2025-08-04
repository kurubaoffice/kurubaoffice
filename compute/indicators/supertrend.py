import pandas as pd  # ✅ Required for DataFrame/Series operations
import ta


def calculate_supertrend(df, window=7, multiplier=3):
    try:
        # ✅ Validate required columns
        for col in ['high', 'low', 'close']:
            if col not in df.columns:
                raise ValueError(f"Missing column: {col}")

        # ✅ ATR Calculation
        atr = ta.volatility.AverageTrueRange(
            high=df['high'], low=df['low'], close=df['close'], window=window
        ).average_true_range()

        hl2 = (df['high'] + df['low']) / 2
        upperband = hl2 + (multiplier * atr)
        lowerband = hl2 - (multiplier * atr)

        direction = [True]  # Bullish = True, Bearish = False

        for i in range(1, len(df)):
            if df['close'].iloc[i] > upperband.iloc[i - 1]:
                direction.append(True)
            elif df['close'].iloc[i] < lowerband.iloc[i - 1]:
                direction.append(False)
            else:
                direction.append(direction[-1])  # Same as previous

        df['supertrend'] = direction
        df['supertrend_upper'] = upperband
        df['supertrend_lower'] = lowerband

        return df

    except Exception as e:
        print(f"[ERROR] Supertrend calculation failed: {e}")
        return df  # Fail gracefully — return original df
