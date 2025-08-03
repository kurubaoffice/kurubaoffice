# reporting/report_nifty_analysis.py

from compute.apply_indicators import apply_indicators
from compute.indicators.interpretation import interpret_signals
from utils.data_loader import get_index_historical, get_stock_historical
from utils.helpers import get_nifty_constituents
from reporting.format_report import format_nifty_full_report


def analyze_nifty(period="3mo", interval="1d"):
    # --- Step 1: Get index data ---
    index_df = get_index_historical("^NSEI", period=period, interval=interval)
    index_df = apply_indicators(index_df)
    index_signals = interpret_signals(index_df)

    # --- Step 2: Get constituent data ---
    constituents = get_nifty_constituents()  # Expects symbols as list
    stock_summaries = []

    for symbol in constituents:
        try:
            stock_df = get_stock_historical(symbol, period=period, interval=interval)
            stock_df = apply_indicators(stock_df)
            stock_signals = interpret_signals(stock_df)
            stock_summaries.append({
                "symbol": symbol,
                "signals": stock_signals
            })
        except Exception as e:
            print(f"[Error] {symbol}: {e}")

    # --- Step 3: Format unified report ---
    return format_nifty_full_report(index_signals, stock_summaries)
