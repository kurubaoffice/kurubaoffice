def format_fno_table_df(df, title):
    if df is None or df.empty:
        return f"{title}\n\n⚠️ No data available right now."

    msg = f"{title}\n\n"

    for i, (_, row) in enumerate(df.iterrows(), start=1):
        symbol = row["symbol"]
        ltp = row["ltp"]
        change = row["change_pct"]
        oi = row["oi"]

        emoji = "🟢" if change > 0 else "🔴"

        msg += (
            f"{i}. {symbol}\n"
            f"   LTP: {ltp}\n"
            f"   Change: {emoji} {change:.2f}%\n"
            f"   OI: {oi}\n\n"
        )

    return msg
