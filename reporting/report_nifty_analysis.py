from compute.apply_indicators import apply_indicators
from compute.indicators.interpretation import interpret_signals
from compute.indicators.confidence_score import compute_confidence_score

from utils.data_loader import get_index_historical, get_stock_historical
from utils.helpers import get_nifty_constituents
from reporting.format_report import format_nifty_full_report
from compute.apply_indicators import apply_indicators

print("🔁 analyze_nifty() was called!")

def analyze_nifty(period="3mo", interval="1d", for_telegram=False):
    # --- Step 1: Get index data ---
    index_df = get_index_historical("^NSEI", period=period, interval=interval)
    index_df = apply_indicators(index_df)
    index_signals = interpret_signals(index_df)
    index_signals["__raw__"] = index_df.iloc[-1].to_dict()
    print("[DEBUG] Columns in index_df:", index_df.columns.tolist())
    print("[DEBUG] Tail of index_df:\n", index_df[['high', 'low', 'close']].tail(5))
    print("[DEBUG] Total rows in index_df:", len(index_df))
    print("[DEBUG] Tail of index_df with ADX columns:")
    print(index_df[['close', 'adx', '+di', '-di']].tail(5).round(2))


    if not isinstance(index_signals, dict):
        print(f"[DEBUG] Invalid index_signals: {index_signals} ({type(index_signals)})")

    # --- Step 2: Get constituent data ---
    constituents = get_nifty_constituents()
    stock_summaries = []

    for symbol in constituents:
        try:
            stock_df = get_stock_historical(symbol, period=period, interval=interval)
            stock_df = apply_indicators(stock_df)
            stock_signals = interpret_signals(stock_df)
            confidence = compute_confidence_score(stock_signals)
            print(f"🔢 Confidence for {symbol}: {confidence}%")
            stock_summaries.append({
                "symbol": symbol,
                "signals": stock_signals,
                "confidence": confidence
            })

        except Exception as e:
            print(f"[Error] {symbol}: {e}")

    # --- Step 3: Format unified report ---
    return format_nifty_full_report(index_signals, stock_summaries,  df_index=index_df, for_telegram=for_telegram)
