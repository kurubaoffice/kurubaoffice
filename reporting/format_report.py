import os
import pandas as pd
import pathlib

from compute.indicators.interpretation import interpret_signals
from utils.helpers import get_nifty_constituents

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


# ✅ MODIFIED: added for_telegram flag
def format_nifty_full_report(index_signals, stock_summaries, for_telegram=False):
    lines = ["📈 *NIFTY 50 Summary*"]

    # --- Index-level signals ---
    lines.append("\n📊 *Index Overview*")
    show_keys = ["MACD", "EMA", "Supertrend", "RSI"]  # You can customize this list

    for key in show_keys:
        if key in index_signals:
            lines.append(f"- `{key}`: *{index_signals[key]}*")

    # 🧠 Optional confidence value
    conf = index_signals.get("confidence", None)
    if conf is not None:
        lines.append(f"- 🧠 *Confidence*: `{conf:.1f}%`")

    # --- Stock-level summaries (non-Telegram only) ---
    if not for_telegram:
        lines.append("\n📈 *Top Stock Signals*")
        if isinstance(stock_summaries, list):
            for stock in stock_summaries:
                sym = stock["symbol"]
                sigs = stock["signals"]
                summary = ", ".join(f"{k}: {v}" for k, v in sigs.items())
                lines.append(f"- `{sym}`: {summary}")

        # --- Top Confidence Rankings ---
        top_conf = sorted(
            [s for s in stock_summaries if "confidence" in s],
            key=lambda x: x["confidence"],
            reverse=True
        )[:10]

        if top_conf:
            lines.append("\n🔢 *Top Confidence Stocks*")
            for s in top_conf:
                lines.append(f"- `{s['symbol']}`: {s['confidence']:.1f}%")

    # --- Signals to Watch with Confidence ---
    if isinstance(stock_summaries, list):
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
            for s in bullish[:10]:
                conf = s.get("confidence", None)
                conf_str = f" – {conf:.1f}%" if conf is not None else ""
                lines.append(f"  - `{s['symbol']}`{conf_str}")

        if bearish:
            lines.append("\n🐻 *Bearish Stocks:*")
            for s in bearish[:10]:
                conf = s.get("confidence", None)
                conf_str = f" – {conf:.1f}%" if conf is not None else ""
                lines.append(f"  - `{s['symbol']}`{conf_str}")

    print(f"[DEBUG] Returning report of type: {type(lines)}")
    print(f"[DEBUG] Sample return value: {lines[:2]}")

    return "\n".join(lines)

