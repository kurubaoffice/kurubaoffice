# bot_ui/formatters.py

def format_simple_list(data, title="📊 List"):
    """
    Works with:
    ✅ list of dicts
    ✅ empty lists
    ✅ safe fallback
    """

    if not data:
        return f"{title}\n\n⚠️ No data available."

    msg = f"{title}\n\n"
    for i, row in enumerate(data, 1):
        symbol = row.get("symbol", "N/A")
        ltp = row.get("ltp", "-")
        chg = row.get("change_pct", "-")

        msg += f"{i}. {symbol} | {ltp} | {chg}%\n"

    return msg
def format_volatility_report(vix, change, regime, strategies):
    text = f"""
📊 *Volatility Analysis*

🧨 *INDIA VIX:* `{vix}`
📈 *Change:* `{change}`

🧭 *Market Regime:* *{regime}*

🎯 *Strategy Mapping:*
"""
    for s in strategies:
        text += f"\n{s}"

    return text
