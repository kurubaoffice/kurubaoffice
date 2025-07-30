import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def calculate_ichimoku(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates Ichimoku Cloud components and appends them to the DataFrame.
    """
    df['tenkan_sen'] = (df['High'].rolling(9).max() + df['Low'].rolling(9).min()) / 2
    df['kijun_sen'] = (df['High'].rolling(26).max() + df['Low'].rolling(26).min()) / 2
    df['senkou_span_a'] = ((df['tenkan_sen'] + df['kijun_sen']) / 2).shift(26)
    df['senkou_span_b'] = ((df['High'].rolling(52).max() + df['Low'].rolling(52).min()) / 2).shift(26)
    df['chikou_span'] = df['Close'].shift(-26)
    return df


def interpret_ichimoku(df: pd.DataFrame) -> dict:
    """
    Interprets Ichimoku Cloud signals from latest data.
    Returns a dictionary of signal interpretation.
    """
    signals = {}
    latest = df.iloc[-1:]

    try:
        a = float(
            latest['senkou_span_a'].item() if hasattr(latest['senkou_span_a'], 'item') else latest['senkou_span_a'])
        b = float(
            latest['senkou_span_b'].item() if hasattr(latest['senkou_span_b'], 'item') else latest['senkou_span_b'])
        price = float(latest['Close'].item() if hasattr(latest['Close'], 'item') else latest['Close'])

        if price > max(a, b):
            signals['cloud_position'] = 'Bullish'
        elif price < min(a, b):
            signals['cloud_position'] = 'Bearish'
        else:
            signals['cloud_position'] = 'Neutral'
    except Exception:
        signals['cloud_position'] = 'Insufficient Data'

    try:
        if pd.notna(latest['tenkan_sen'].iloc[0]) and pd.notna(latest['kijun_sen'].iloc[0]):
            if latest['tenkan_sen'].iloc[0] > latest['kijun_sen'].iloc[0]:
                signals['tk_cross'] = 'Bullish Crossover'
            elif latest['tenkan_sen'].iloc[0] < latest['kijun_sen'].iloc[0]:
                signals['tk_cross'] = 'Bearish Crossover'
            else:
                signals['tk_cross'] = 'No Crossover'
        else:
            signals['tk_cross'] = 'Insufficient Data'
    except Exception:
        signals['tk_cross'] = 'Insufficient Data'

    try:
        if len(df) >= 27:
            past_price = df.iloc[-27]['Close']
            if pd.notna(latest['chikou_span'].iloc[0]):
                if latest['chikou_span'].iloc[0] > past_price:
                    signals['chikou_confirmation'] = 'Bullish'
                elif latest['chikou_span'].iloc[0] < past_price:
                    signals['chikou_confirmation'] = 'Bearish'
                else:
                    signals['chikou_confirmation'] = 'Neutral'
            else:
                signals['chikou_confirmation'] = 'Insufficient Data'
        else:
            signals['chikou_confirmation'] = 'Insufficient Data'
    except Exception:
        signals['chikou_confirmation'] = 'Insufficient Data'

    # Final signal determination
    bullish = sum(1 for v in signals.values() if 'Bullish' in v)
    bearish = sum(1 for v in signals.values() if 'Bearish' in v)

    if bullish >= 2:
        signals['ichimoku_signal'] = 'Bullish'
    elif bearish >= 2:
        signals['ichimoku_signal'] = 'Bearish'
    else:
        signals['ichimoku_signal'] = 'Neutral'

    return signals


def plot_ichimoku(df: pd.DataFrame, symbol: str = None, save_path: str = None):
    """
    Plots Ichimoku Cloud chart.
    """
    plt.figure(figsize=(14, 7))
    plt.plot(df['Close'], label='Close', color='black', linewidth=1)
    plt.plot(df['tenkan_sen'], label='Tenkan-sen', color='red', linestyle='--')
    plt.plot(df['kijun_sen'], label='Kijun-sen', color='blue', linestyle='--')
    plt.plot(df['chikou_span'], label='Chikou Span', color='green', linestyle=':')
    plt.plot(df['senkou_span_a'], label='Senkou Span A', color='orange')
    plt.plot(df['senkou_span_b'], label='Senkou Span B', color='purple')

    # Cloud fill
    plt.fill_between(df.index, df['senkou_span_a'], df['senkou_span_b'],
                     where=(df['senkou_span_a'] >= df['senkou_span_b']),
                     color='lightgreen', alpha=0.3)

    plt.fill_between(df.index, df['senkou_span_a'], df['senkou_span_b'],
                     where=(df['senkou_span_a'] < df['senkou_span_b']),
                     color='lightcoral', alpha=0.3)

    plt.title(f'Ichimoku Cloud for {symbol}' if symbol else 'Ichimoku Cloud')
    plt.legend()
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path)
        plt.close()
    else:
        plt.show()


def summarize_ichimoku(signals: dict) -> str:
    """
    Converts technical signals into a human-readable explanation.
    """
    summary = []

    if signals.get("cloud_position") == "Bullish":
        summary.append("📈 Price is above the cloud → Strong uptrend.")
    elif signals.get("cloud_position") == "Bearish":
        summary.append("📉 Price is below the cloud → Downtrend.")
    else:
        summary.append("☁️ Price is inside the cloud → Neutral or range-bound.")

    if signals.get("tk_cross") == "Bullish Crossover":
        summary.append("🟢 Tenkan-sen crossed above Kijun-sen → Bullish signal.")
    elif signals.get("tk_cross") == "Bearish Crossover":
        summary.append("🔴 Tenkan-sen crossed below Kijun-sen → Bearish signal.")

    if signals.get("chikou_confirmation") == "Bullish":
        summary.append("✅ Chikou span confirms bullish momentum.")
    elif signals.get("chikou_confirmation") == "Bearish":
        summary.append("❌ Chikou span confirms bearish momentum.")

    summary.append(f"🔍 Final Ichimoku Signal: **{signals.get('ichimoku_signal', 'N/A')}**")

    return "\n".join(summary)


def get_ichimoku_summary(df: pd.DataFrame) -> tuple:
    """
    Full wrapper to calculate + interpret and return structured results.
    """
    df = calculate_ichimoku(df)
    signals = interpret_ichimoku(df)
    return df, signals


# Run standalone
if __name__ == "__main__":
    import yfinance as yf

    symbol = "RELIANCE.NS"
    df = yf.download(symbol, period="9mo", interval="1d", auto_adjust=False)[['Open', 'High', 'Low', 'Close', 'Volume']]
    df, signals = get_ichimoku_summary(df)

    if 'error' in signals:
        print(f"❌ Error in Ichimoku calculation: {signals['error']}")
    else:
        print(f"\n📊 Ichimoku Technical Summary for {symbol}:\n")
        print(summarize_ichimoku(signals))

    plot_ichimoku(df, symbol=symbol)
