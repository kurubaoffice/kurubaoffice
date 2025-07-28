import pandas as pd


def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    Calculate Relative Strength Index (RSI) and add it to the DataFrame.

    Parameters:
        df (pd.DataFrame): DataFrame with at least a 'Close' column.
        period (int): RSI calculation period. Default is 14.

    Returns:
        pd.DataFrame: Original DataFrame with added 'RSI' and 'RSI_Signal' columns.
    """
    if 'Close' not in df.columns:
        raise ValueError("DataFrame must contain 'Close' column for RSI")

    delta = df['Close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()

    avg_loss = avg_loss.replace(0, 1e-10)
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))

    def rsi_signal(rsi):
        if rsi >= 70:
            return "Overbought: Strong potential for reversal downward"
        elif rsi <= 30:
            return "Oversold: Strong potential for reversal upward"
        elif 50 < rsi < 70:
            return "Bullish: RSI trending upward but not yet overbought"
        elif 30 < rsi <= 50:
            return "Bearish: RSI trending downward but not yet oversold"
        return "Neutral: When RSI is exactly 50 (rare), considered balanced"

    df['RSI_Signal'] = df['RSI'].apply(lambda x: rsi_signal(x) if pd.notnull(x) else None)

    return df

def summarize_rsi_trend(df: pd.DataFrame, symbol: str):
    last_3 = df.tail(3)
    if len(last_3) < 3:
        print("Not enough data to summarize RSI trend.")
        return

    rsi_start = last_3['RSI'].iloc[0]
    rsi_end = last_3['RSI'].iloc[-1]
    price_start = float(last_3["Close"].iloc[0])
    price_end = float(last_3["Close"].iloc[-1])

    rsi_trend = "Rising" if rsi_end > rsi_start else "Falling" if rsi_end < rsi_start else "Flat"
    price_change = price_end - price_start
    price_pct = ((price_end - price_start) / price_start) * 100

    if rsi_end <= 30:
        zone = "Oversold"
    elif rsi_end >= 70:
        zone = "Overbought"
    elif rsi_end > rsi_start:
        zone = "Improving"
    else:
        zone = "Weakening"

    momentum = "Bearish with potential for reversal" if rsi_end <= 30 else (
        "Strong momentum" if rsi_end >= 70 else
        "Neutral to Bullish" if rsi_end > rsi_start else
        "Bearish trend continuation"
    )

    print(f"\n📊 Last 3-Day RSI Summary for {symbol}")
    print(f"- RSI Trend: {rsi_trend} ({rsi_start:.2f} → {rsi_end:.2f})")
    print(f"- RSI Zone: {zone}")
    print(f"- Price Trend: ₹{price_start:.2f} → ₹{price_end:.2f} ({'↑' if price_pct > 0 else '↓'} {abs(price_pct):.2f}%)")
    print(f"- Momentum Signal: {momentum}")



# 🔍 Local testing block (for standalone test runs)
if __name__ == "__main__":
    run_test = False  # 🔁 Toggle this to True to test RSI manually

    if run_test:
        import yfinance as yf
        import matplotlib.pyplot as plt

        symbol = "INFY.NS"
        df = yf.download(symbol, period="3mo", interval="1d")

        df = calculate_rsi(df)

        print(df[['Close', 'RSI', 'RSI_Signal']].tail(10).round(2))
        summarize_rsi_trend(df, symbol)

        # Optional: Plot RSI
        plt.figure(figsize=(12, 4))
        plt.plot(df['RSI'], label='RSI')
        plt.axhline(70, color='r', linestyle='--', label='Overbought')
        plt.axhline(30, color='g', linestyle='--', label='Oversold')
        plt.title(f"{symbol} - RSI")
        plt.legend()
        plt.grid()
        plt.tight_layout()
        plt.show()
