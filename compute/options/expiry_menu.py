# compute/options/expiry_menu.py
import datetime as dt
import calendar
from typing import List, Tuple

def _is_last_thursday_of_month(d: dt.date) -> bool:
    last = calendar.monthrange(d.year, d.month)[1]
    last_date = dt.date(d.year, d.month, last)
    while last_date.weekday() != 3:  # Thursday
        last_date = last_date.replace(day=last_date.day - 1)
    return d == last_date

def classify_expiries(expiries: List[str]) -> Tuple[List[str], List[str]]:
    """
    expiries: list of strings like '25-Nov-2025'
    Returns weekly_list, monthly_list (strings) in chronological order
    """
    weekly = []
    monthly = []
    for e in expiries:
        try:
            d = dt.datetime.strptime(e, "%d-%b-%Y").date()
        except Exception:
            continue
        if _is_last_thursday_of_month(d):
            monthly.append(e)
        else:
            weekly.append(e)

    weekly = sorted(weekly, key=lambda x: dt.datetime.strptime(x, "%d-%b-%Y").date())
    monthly = sorted(monthly, key=lambda x: dt.datetime.strptime(x, "%d-%b-%Y").date())
    return weekly, monthly

def format_grouped_expiry_menu(symbol: str, weekly: list, monthly: list) -> str:
    """
    1B style (grouped card-style)
    """
    lines = [f"📅 Available Expiries for {symbol}\n"]
    idx = 1
    if weekly:
        lines.append("🗓 Weekly Expiries")
        for e in weekly:
            lines.append(f"{idx}️⃣ {e}")
            idx += 1
    if monthly:
        lines.append("\n📆 Monthly & Far-Month Expiries")
        for e in monthly:
            lines.append(f"{idx}️⃣ {e}")
            idx += 1
    lines.append(f"\nReply with a number (1–{idx-1}) to select expiry, or send a date (25-Dec-2025) / month (DEC).")
    return "\n".join(lines)

def combined_order(weekly: list, monthly: list) -> list:
    return weekly + monthly
