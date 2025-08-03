# reporting/format_report.py

def format_nifty_full_report(index_signals, stock_summaries):
    lines = ["📈 *NIFTY 50 Summary*\n"]

    # --- Stock Level Section ---
    lines.append("\n📈 *Top Stock Signals*")

    stock_symbols = get_nifty_constituents()

    for symbol in stock_symbols:
        try:
            print(f"🔍 Processing stock: {symbol}")  # Debug line
            stock_path = os.path.join("data", "processed", "stocks", f"{symbol}.csv")
            if not os.path.exists(stock_path):
                print(f"⚠️ Missing file for {symbol}")
                continue

            df = pd.read_csv(stock_path)
            if df.empty:
                print(f"⚠️ Empty data for {symbol}")
                continue

            interpreted = interpret_signals(df)
            summary = f"{symbol}: {interpreted.get('summary', '⚠️ No summary')}"
            lines.append(f"- {summary}")

        except Exception as e:
            print(f"[ERROR] Failed to process {symbol}: {e}")

    # --- Top Stocks Summary ---
    lines.append("\n📉 *Constituent Highlights*")
    for stock in stock_summaries[:10]:  # limit to top 10 for Telegram brevity
        sym = stock["symbol"]
        sigs = stock["signals"]
        summary = ", ".join(f"{k}: {v}" for k, v in sigs.items())
        lines.append(f"- {sym}: {summary}")

    # --- Categorize by trend ---
    bullish = [s["symbol"] for s in stock_summaries if s["signals"].get("Trend") == "Bullish"]
    bearish = [s["symbol"] for s in stock_summaries if s["signals"].get("Trend") == "Bearish"]

    lines.append("\n💡 *Signals to Watch*")
    if bullish:
        lines.append(f"- *Bullish*: {', '.join(bullish[:5])}")
    if bearish:
        lines.append(f"- *Bearish*: {', '.join(bearish[:5])}")

    return "\n".join(lines)
