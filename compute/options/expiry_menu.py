import datetime as dt
import calendar
from typing import List, Tuple


def _is_last_thursday_of_month(d: dt.date) -> bool:
    """Return True if the date is the last Thursday of its month."""
    last_day = calendar.monthrange(d.year, d.month)[1]
    last_date = dt.date(d.year, d.month, last_day)
    while last_date.weekday() != 3:  # Thursday
        last_date = last_date.replace(day=last_date.day - 1)
    return d == last_date


def classify_expiries(expiries: List[str]) -> Tuple[List[str], List[str]]:
    """
    Classify a list of expiry dates into weekly and monthly expiries.

    Args:
        expiries: List of strings like '25-Nov-2025'

    Returns:
        Tuple of (weekly_list, monthly_list), both sorted chronologically.
    """
    weekly = []
    monthly = []

    for e in expiries:
        try:
            e_str = str(e).strip()
            if not e_str:
                continue
            d = dt.datetime.strptime(e_str, "%d-%b-%Y").date()
        except Exception:
            continue
        if _is_last_thursday_of_month(d):
            monthly.append(e_str)
        else:
            weekly.append(e_str)

    def _parse_date_safe(s):
        try:
            return dt.datetime.strptime(s, "%d-%b-%Y").date()
        except Exception:
            return dt.date.max

    weekly = sorted(weekly, key=_parse_date_safe)
    monthly = sorted(monthly, key=_parse_date_safe)
    return weekly, monthly


def format_grouped_expiry_menu(symbol: str, weekly: list, monthly: list) -> str:
    """
    Format expiry dates in a grouped, card-style menu for Telegram or CLI.

    Args:
        symbol: Stock or index symbol
        weekly: List of weekly expiry strings
        monthly: List of monthly expiry strings

    Returns:
        A formatted string for display.
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

    lines.append(f"\nReply with a number (1–{idx - 1}) to select expiry, or send a date (25-Dec-2025) / month (DEC).")
    return "\n".join(lines)


def combined_order(weekly: list, monthly: list) -> list:
    """Return a combined list of weekly + monthly expiries in order."""
    return weekly + monthly
