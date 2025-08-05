# reporting/report_single_stock.py

from compute.apply_indicators import apply_indicators
from compute.indicators.interpretation import interpret_signals
from compute.indicators.confidence_score import compute_confidence_score
from utils.data_loader import get_stock_historical
import pandas as pd


def format_single_stock_report(symbol, df, signals, confidence):
    last_row = df.iloc[-1]

    # Technical logic for trend indicators
    close_price = last_row.get("close", 0)
    ema20_val = last_row.get("ema_20", 0)
    ema50_val = last_row.get("ema_50", 0)
    adx_val = round(last_row.get("adx", 0), 2)
    adx_strength = "Bullish" if adx_val >= 20 else "Weak"

    lines = [
        f"📌 *Stock:* `{symbol}`",
        f"💰 *CMP:* ₹{round(close_price, 2)}",
        f"✅ *Confidence:* `{confidence:.1f}%`",

        f"\n📊 *Technical Indicators:*",
        f"- RSI (14): {round(last_row.get('RSI', 0), 2)}",
        f"- MACD: {round(last_row.get('macd', 0), 2)} / Signal: {round(last_row.get('macd_signal', 0), 2)}",
        f"- Supertrend: {'🟢 Buy' if last_row.get('supertrend') else '🔴 Sell'}",
        f"- EMA 20: {'📈 Above' if close_price > ema20_val else '📉 Below'}",
        f"- EMA 50: {'📈 Above' if close_price > ema50_val else '📉 Below'}",
        f"- ADX: {adx_val} – *{adx_strength}*",
        f"- Bollinger Bands: {round(last_row.get('bb_lower', 0), 2)} – {round(last_row.get('bb_upper', 0), 2)}",
        f"- ATR (Volatility): {round(last_row.get('atr_14', 0), 2)}",

        f"\n🧠 *Signal Summary:*"
    ]

    for k, v in signals.items():
        lines.append(f"- {k}: {v}")

    return "\n".join(lines)

def analyze_single_stock(symbol, period="9mo", interval="1d"):
    df = get_stock_historical(symbol, period=period, interval=interval)
    df = apply_indicators(df)
    signals = interpret_signals(df)
    confidence = compute_confidence_score(signals)
    return format_single_stock_report(symbol, df, signals, confidence)

