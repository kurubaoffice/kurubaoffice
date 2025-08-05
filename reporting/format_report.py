import os
import pandas as pd
import pathlib

#from compute.indicators.interpretation import interpret_signals
#from utils.helpers import get_nifty_constituents

# Base paths
BASE_DIR = pathlib.Path(__file__).resolve().parents[1]

CSV_PATH = BASE_DIR / "data" / "raw" / "listed_companies.csv"
STOCK_DATA_DIR = BASE_DIR / "data" / "processed" / "stocks"

print("🧩 format_nifty_full_report() was called!")


def format_stock_summary(symbol, signals):
    lines = [f"📊 *Stock Report: {symbol}*"]
    for k, v in signals.items():
        lines.append(f"- {k}: {v}")
    return "\n".join(lines)


def file_exists_case_insensitive(folder: pathlib.Path, target_file: str) -> pathlib.Path | None:
    """Check if file exists in folder (case-insensitive). Return actual file path if exists."""
    for f in folder.iterdir():
        if f.name.lower() == target_file.lower():
            return f
    return None


def format_nifty_full_report(index_signals, stock_summaries, df_index=None, for_telegram=False):
    lines = ["📈 *NIFTY 50 Summary*"]


    # --- Index-level signals ---
    lines.append("\n📊 *Index Overview*")
    if df_index is not None and not df_index.empty and "close" in df_index.columns:
        latest_close = df_index.iloc[-1]["close"]
        lines.append(f"• CMP: `{latest_close:.2f}`")



    tech_row = index_signals.get("__raw__")  # Must be set during signal generation

    if tech_row:
        # Extract and format detailed indicators
        rsi_val = round(float(tech_row.get('RSI', 0.0)), 2)
        macd_val = round(float(tech_row.get('macd', 0.0)), 2)
        macd_signal_val = round(float(tech_row.get('macd_signal', 0.0)), 2)
        adx_val = round(float(tech_row.get('adx', 0.0)), 2)
        bb_upper = round(float(tech_row.get('bb_upper', 0.0)), 2)
        bb_lower = round(float(tech_row.get('bb_lower', 0.0)), 2)
        atr_val = round(float(tech_row.get('atr_14', 0.0)), 2)

        supertrend_val = tech_row.get('supertrend', None)
        if pd.isna(supertrend_val):
            supertrend_str = '⚪ N/A'
        else:
            supertrend_str = '🟢 Buy' if supertrend_val else '🔴 Sell'

        lines += [
            f"• RSI (14): {rsi_val}",
            f"• MACD: {macd_val}",
            f"• MACD Signal: {macd_signal_val}",
            f"• Supertrend: {supertrend_str}",
            f"• ADX Strength: {adx_val}",
            f"• BB Upper Band: {bb_upper}",
            f"• BB Lower Band: {bb_lower}",
            f"• ATR (Volatility): {atr_val}",
        ]
    else:
        lines.append("_⚠️ No index-level data available._")

    # --- Index Confidence ---
    conf = index_signals.get("confidence", None)
    if conf is not None:
        lines.append(f"\n✅ *NIFTY50 Confidence*: `{conf:.1f}%`")

    # -------------------------------
    # ✅ Always show Top Confidence Stocks (even in Telegram)
    # -------------------------------
    top_conf = sorted(
        [s for s in stock_summaries if "confidence" in s],
        key=lambda x: x["confidence"],
        reverse=True
    )[:10]

    if top_conf:
        lines.append("\n🔢 *Top Confidence Stocks*")
        for s in top_conf:
            lines.append(f"- `{s['symbol']}`: {s['confidence']:.1f}%")

    # -------------------------------
    # 🧪 Optional: Show Signals to Watch (based on trend)
    # Comment this block to hide it
    # -------------------------------
    bullish = [
        s for s in stock_summaries
        if s["signals"].get("Trend") == "Bullish"
    ]
    bearish = [
        s for s in stock_summaries
        if s["signals"].get("Trend") == "Bearish"
    ]

    if bullish or bearish:
        lines.append("\n💡 *Signals to Watch*")

    if bullish:
        lines.append("🐂 *Bullish Stocks:*")
        for s in bullish[:2]:
            conf = s.get("confidence", None)
            conf_str = f" – {conf:.1f}%" if conf is not None else ""
            lines.append(f"  - `{s['symbol']}`{conf_str}")

    if bearish:
        lines.append("\n🐻 *Bearish Stocks:*")
        for s in bearish[:2]:
            conf = s.get("confidence", None)
            conf_str = f" – {conf:.1f}%" if conf is not None else ""
            lines.append(f"  - `{s['symbol']}`{conf_str}")

    # -------------------------------
    # 🚫 OPTIONAL BLOCK: Full Stock-Level Summary (for CLI, not Telegram)
    # Uncomment this if needed
    # -------------------------------
    """
    if not for_telegram:
        lines.append("\n📈 *Top Stock Signals*")
        if isinstance(stock_summaries, list):
            for stock in stock_summaries:
                sym = stock["symbol"]
                sigs = stock["signals"]
                summary = ", ".join(f"{k}: {v}" for k, v in sigs.items())
                lines.append(f"- `{sym}`: {summary}")
    """

    print(f"[DEBUG] Returning report of type: {type(lines)}")
    print(f"[DEBUG] Sample return value: {lines[:2]}")

    return "\n".join(lines)


