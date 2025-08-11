# reporting/report_stock_summary.py

from reporting.format_report import format_stock_summary
from compute.apply_indicators import apply_indicators
from compute.indicators.interpretation import interpret_signals
from utils.data_loader import get_stock_historical
from reporting.report_single_stock import analyze_single_stock
def run_pipeline_for_symbol(symbol, chat_id=None):
    try:
        df = get_stock_historical(symbol)
        df = apply_indicators(df)
        signals = interpret_signals(df)
        #report = format_stock_summary(symbol, signals)
        report = analyze_single_stock(symbol)
        return True, report  # ✅ return report
    except Exception as e:
        print(f"[ERROR] Failed to analyze {symbol}: {e}")
        return False, None
