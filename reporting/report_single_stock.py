import pandas as pd
from compute.apply_indicators import apply_indicators
from compute.indicators.interpretation import interpret_signals
from compute.indicators.confidence_score import compute_confidence_score
from utils.data_loader import get_stock_historical
import re


def escape_md(text):
    """
    Escape special characters for Telegram MarkdownV2 formatting.
    """
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', str(text))


def trend_icon(condition):
    return '🟢' if condition else '🔴'


def format_single_stock_report(symbol, df, signals, confidence):
    last_row = df.iloc[-1]
    prev_row = df.iloc[-2] if len(df) >= 2 else last_row

    # Price details
    close_price = last_row.get("close", 0)
    prev_close = prev_row.get("close", 0)
    change = close_price - prev_close
    change_pct = (change / prev_close) * 100 if prev_close else 0

    # Trend indicators
    ema20_val = last_row.get("ema_20", 0)
    ema50_val = last_row.get("ema_50", 0)
    adx_val = round(last_row.get("adx", 0), 2)
    adx_strength = "Bullish" if adx_val >= 20 else "Weak"

    # EliteWave values
    ew_trend = last_row.get("elitewave_trend", "N/A")
    ew_wave = last_row.get("elitewave_current_wave", "N/A")
    ew_conf = last_row.get("elitewave_confidence", 0.0)

    # EliteWave interpretation (added)
    ew_final_dir = last_row.get("elitewave_final_direction", "N/A")
    ew_strength = last_row.get("elitewave_strength", "N/A")
    ew_explanation = last_row.get("elitewave_explanation", "N/A")

    # Signals
    bullish = [k for k, v in signals.items() if v == "Bullish"]
    bearish = [k for k, v in signals.items() if v == "Bearish"]

    lines = [
        f"📌 *Stock:* `{escape_md(symbol)}`",
        f"💰 *CMP:* ₹{round(close_price, 2)}",
        f"📉 *Daily Change:* {round(change, 2)} ({round(change_pct, 2)}%)",
        f"✅ *Confidence:* `{confidence:.1f}%`",

        "\n🧭 *Trend & Price Action:*",
        f"- EMA 20: {trend_icon(close_price > ema20_val)} {'Above' if close_price > ema20_val else 'Below'}",
        f"- EMA 50: {trend_icon(close_price > ema50_val)} {'Above' if close_price > ema50_val else 'Below'}",
        f"- Supertrend: {trend_icon(last_row.get('supertrend'))} {'Buy' if last_row.get('supertrend') else 'Sell'}",
        f"- ADX: {adx_val} – *{adx_strength}*",

        "\n📊 *Momentum Indicators:*",
        f"- RSI (14): {round(last_row.get('RSI', 0), 2)}",
        f"- MACD: {round(last_row.get('macd', 0), 2)} / Signal: {round(last_row.get('macd_signal', 0), 2)}",

        "\n📏 *Volatility & Range:*",
        f"- Bollinger Bands: {round(last_row.get('bb_lower', 0), 2)} – {round(last_row.get('bb_upper', 0), 2)}",
        f"- ATR (14): {round(last_row.get('atr_14', 0), 2)}",

         "\n🌀 *EliteWave Outcome:*",
        f"- Trend: {escape_md(ew_trend)}",
        f"- Current Wave: {escape_md(ew_wave)}",
        f"- Confidence: {ew_conf:.1f}%",

        "\n🌀 *EliteWave Interpretation:*",
        f"- Final Direction: {escape_md(ew_final_dir)}",
        f"- Strength: {escape_md(ew_strength)}",
        f"- Explanation: {escape_md(ew_explanation)}",

        "\n🧠 *Signal Summary:*",
        f"📈 *Bullish:* {', '.join(bullish) if bullish else 'None'}",
        f"📉 *Bearish:* {', '.join(bearish) if bearish else 'None'}"
    ]

    return "\n".join(lines)



def analyze_single_stock(symbol, period="9mo", interval="1d", return_json=False):
    df = get_stock_historical(symbol, period=period, interval=interval)
    df = apply_indicators(df)

    # No need to compute RSI divergences anymore
    signals = interpret_signals(df)
    confidence = compute_confidence_score(signals)
    formatted = format_single_stock_report(symbol, df, signals, confidence)

    if return_json:
        return {
            "symbol": symbol,
            "cmp": df.iloc[-1]["close"],
            "confidence": confidence,
            "signals": signals,
            "formatted": formatted
        }

    return formatted

