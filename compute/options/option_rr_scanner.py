# filename: compute/options/option_rr_scanner.py
# CLEAN REWRITE WITH STRICT MODE (OPTION A) + NSE FIRST + Expiry selection support

import math
import pandas as pd
import numpy as np
import datetime as dt
import yfinance as yf
import aiohttp
import asyncio
import re
import calendar
import httpx
# -------------------------------
# Constants / URLs
# -------------------------------
NSE_OC_URL = "https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"

# -------------------------------
# Helpers: Date parsing / expiry resolution
# -------------------------------
MONTH_SHORT_MAP = {
    "JAN":1,"FEB":2,"MAR":3,"APR":4,"MAY":5,"JUN":6,
    "JUL":7,"AUG":8,"SEP":9,"OCT":10,"NOV":11,"DEC":12
}

def _parse_date_formats(s: str):
    """
    Try multiple date formats and return a date object or None.
    Accepts: YYYY-MM-DD, DD-MMM-YYYY, DDMMYY, DDMMM, DD-MMM, DDMMMYYYY, DDMONYYYY etc.
    """
    s = s.strip().upper()
    # yyyy-mm-dd
    try:
        return dt.datetime.strptime(s, "%Y-%m-%d").date()
    except:
        pass
    # 25-DEC-2025 or 25-DEC
    for fmt in ("%d-%b-%Y", "%d-%b"):
        try:
            d = dt.datetime.strptime(s, fmt).date()
            if d.year == 1900:
                # no year provided -> assume this year or next if already passed
                d = d.replace(year=dt.date.today().year)
                if d < dt.date.today():
                    d = d.replace(year=d.year + 1)
            return d
        except:
            pass
    # 25DEC or 25DEC2025
    m = re.match(r"^(\d{1,2})([A-Z]{3})(\d{2,4})?$", s)
    if m:
        day = int(m.group(1))
        mon = m.group(2)
        year = m.group(3)
        mon_n = MONTH_SHORT_MAP.get(mon)
        if not mon_n:
            return None
        if not year:
            year_n = dt.date.today().year
            try_date = dt.date(year_n, mon_n, day)
            if try_date < dt.date.today():
                year_n += 1
            return dt.date(year_n, mon_n, day)
        else:
            y = int(year)
            if y < 100:
                y = 2000 + y
            return dt.date(y, mon_n, day)
    # Month only: DEC or DEC-2025
    m2 = re.match(r"^([A-Z]{3})(?:-?(\d{4}))?$", s)
    if m2:
        mon = m2.group(1)
        year = m2.group(2)
        mon_n = MONTH_SHORT_MAP.get(mon)
        if not mon_n:
            return None
        y = int(year) if year else dt.date.today().year
        # choose first of month as proxy
        return dt.date(y, mon_n, 1)
    return None

def _is_last_thursday_of_month(d: dt.date):
    # last thursday of the month
    last_day = calendar.monthrange(d.year, d.month)[1]
    last_date = dt.date(d.year, d.month, last_day)
    while last_date.weekday() != 3:  # Thursday
        last_date = last_date.replace(day=last_date.day - 1)
    return d == last_date

def days_to_expiry_nse(exp_str):
    try:
        return max(1, (dt.datetime.strptime(exp_str, "%d-%b-%Y").date() - dt.date.today()).days)
    except:
        return 7

# -------------------------------
# 1. Parse TG Message (enhanced)
# -------------------------------
def parse_tg_input(msg: str):
    """
    Returns: (ticker, dtype, expiry_raw)
    dtype -> "CE", "PE", "CEPE"
    expiry_raw -> string (maybe None) - raw user expiry token (e.g., DEC, 25DEC, 2025-12-25)
    """
    msg = msg.strip().upper()
    parts = [p for p in re.split(r'[\s\-]+', msg) if p]
    if not parts:
        return None, None, None
    ticker = parts[0]
    dtype = None
    expiry_raw = None

    # detect CE / PE / CEPE in remaining parts
    for p in parts[1:]:
        if p in ("CE", "PE", "CEPE"):
            dtype = p
        else:
            # treat first non-CE/PE token as expiry candidate
            if expiry_raw is None:
                expiry_raw = p

    if dtype is None:
        dtype = "CEPE"
    return ticker, dtype, expiry_raw

# -------------------------------
# 2. Underlying price from NSE
# -------------------------------


import httpx

def fetch_underlying_price(ticker):
    """
    Fully NSE-based underlying fetcher.
    Works for BANKNIFTY / NIFTY / stocks.
    """
    index_map = {
        "BANKNIFTY": "NIFTY BANK",
        "NIFTY": "NIFTY 50",
        "FINNIFTY": "NIFTY FIN SERVICE",
    }

    # INDEX CASE
    if ticker.upper() in index_map:
        url = "https://www.nseindia.com/api/allIndices"
        headers = {"User-Agent": "Mozilla/5.0"}

        with httpx.Client(headers=headers, timeout=10) as client:
            client.get("https://www.nseindia.com")
            r = client.get(url)
            data = r.json()

        for item in data["data"]:
            if item["index"] == index_map[ticker.upper()]:
                return float(item["last"]), None

        raise RuntimeError("Index price not found on NSE")

    # STOCK CASE
    url = f"https://www.nseindia.com/api/quote-equity?symbol={ticker}"
    headers = {"User-Agent": "Mozilla/5.0"}

    with httpx.Client(headers=headers, timeout=10) as client:
        client.get("https://www.nseindia.com")
        r = client.get(url)
        data = r.json()

    return float(data["priceInfo"]["lastPrice"]), None


# -------------------------------
# 3. NSE Option Chain (Primary)
# -------------------------------
async def fetch_option_chain_nse(symbol):
    headers = {
        "user-agent": "Mozilla/5.0",
        "accept": "application/json",
        "accept-language": "en-US,en;q=0.9"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(NSE_OC_URL.format(symbol=symbol)) as resp:
            if resp.status != 200:
                raise RuntimeError("NSE OC fetch failed")
            data = await resp.json()

    records = data.get("records", {}).get("data", [])
    calls, puts = [], []

    for e in records:
        if e.get("CE"):
            calls.append(e["CE"])
        if e.get("PE"):
            puts.append(e["PE"])

    calls_df = pd.DataFrame(calls) if calls else pd.DataFrame()
    puts_df = pd.DataFrame(puts) if puts else pd.DataFrame()

    # Normalize field names
    for df in (calls_df, puts_df):
        df.rename(columns={
            "last_price": "lastPrice",
            "iv": "impliedVolatility"
        }, inplace=True, errors='ignore')

    expiries = sorted(list({e.get("expiryDate") for e in records if e.get("expiryDate")}),
                      key=lambda d: dt.datetime.strptime(d, "%d-%b-%Y").date())

    expiry_map = {}
    for e in expiries:
        expiry_map[e] = {
            'calls': calls_df[calls_df['expiryDate'] == e] if not calls_df.empty else pd.DataFrame(),
            'puts': puts_df[puts_df['expiryDate'] == e] if not puts_df.empty else pd.DataFrame()
        }
    return expiry_map

# -------------------------------
# 4. YF Option Chain (Fallback)
# -------------------------------
def fetch_option_chain_yf(tk):
    res = {}
    for e in tk.options:
        oc = tk.option_chain(e)
        c = oc.calls.copy()
        p = oc.puts.copy()
        c['expiry'] = e
        p['expiry'] = e
        res[e] = {'calls': c, 'puts': p}
    return res

# -------------------------------
# 5. Calculations
# -------------------------------
def expected_move_from_iv(S, iv_decimal, days):
    return S * iv_decimal * math.sqrt(days / 252)

def _normalize_iv(iv):
    if iv is None:
        return 0.0
    try:
        iv = float(iv)
        if iv > 5:
            iv = iv / 100.0
        return iv
    except:
        return 0.0

# -------------------------------
# 6. STRICT RR SCORING (MODE A)
# -------------------------------
def compute_rr_strict(S, df, right, days, k_target=1.0):
    if df is None or df.empty:
        return pd.DataFrame([])

    df = df.copy()

    # Normalise name differences
    if 'strikePrice' in df.columns:
        df.rename(columns={'strikePrice':'strike', 'lastPrice':'lastPrice', 'impliedVolatility':'impliedVolatility'}, inplace=True, errors='ignore')

    # Strict filter: keep only real tradable strikes
    lp_col = 'lastPrice' if 'lastPrice' in df.columns else 'last_price' if 'last_price' in df.columns else None
    iv_col = 'impliedVolatility' if 'impliedVolatility' in df.columns else 'iv' if 'iv' in df.columns else None
    oi_col = 'openInterest' if 'openInterest' in df.columns else 'openInterest'

    if lp_col and iv_col and oi_col:
        df = df[(df[lp_col] > 0) & (df[iv_col] > 0) & (df[oi_col] >= 0)]
    else:
        # fallback - try to continue
        pass

    if df.empty:
        return pd.DataFrame([])

    rows = []
    for _, r in df.iterrows():
        K = float(r.get('strike', np.nan))
        premium = float(r.get(lp_col, 0.0))
        iv = _normalize_iv(r.get(iv_col, 0.0))
        EM = expected_move_from_iv(S, iv, days)
        if right == 'CALL':
            target = S + k_target * EM
            payoff = max(0, target - K)
        else:
            target = S - k_target * EM
            payoff = max(0, K - target)

        rr = payoff / premium if premium > 0 else 0.0

        rows.append({
            'strike': K,
            'premium': premium,
            'iv': iv,
            'EM': EM,
            'target_price': target,
            'payoff': payoff,
            'RR': rr,
            'openInterest': int(r.get(oi_col, 0))
        })

    return pd.DataFrame(rows).sort_values('RR', ascending=False)

# -------------------------------
# 7. NSE-first async fetch
# -------------------------------
async def fetch_chain_async(symbol):
    """
    NSE-first ALWAYS.
    yfinance fallback ONLY for STOCKS — NEVER for INDEX (BANKNIFTY / NIFTY / FINNIFTY).
    """
    try:
        # NSE option chain
        chain_nse = await fetch_option_chain_nse(symbol)
        price, _ = fetch_underlying_price(symbol)
        return price, chain_nse, 'NSE'
    except Exception as e:
        # If symbol is an index → NEVER fallback to yfinance
        if symbol.upper() in ("BANKNIFTY", "NIFTY", "FINNIFTY"):
            raise RuntimeError(f"NSE OC failed and fallback disabled for index: {e}")




# -------------------------------
# 8. Expiry utilities / listing
# -------------------------------
def classify_expiries(expiries):
    """
    Input: list of expiry strings like '25-Dec-2025'
    Output: (weekly_list, monthly_list) both sorted (strings)
    """
    weekly = []
    monthly = []
    for e in expiries:
        try:
            d = dt.datetime.strptime(e, "%d-%b-%Y").date()
        except:
            continue
        if _is_last_thursday_of_month(d):
            monthly.append(e)
        else:
            weekly.append(e)
    weekly = sorted(weekly, key=lambda x: dt.datetime.strptime(x, "%d-%b-%Y").date())
    monthly = sorted(monthly, key=lambda x: dt.datetime.strptime(x, "%d-%b-%Y").date())
    return weekly, monthly

def format_grouped_expiry_menu(symbol, weekly, monthly):
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

async def list_available_expiries_for_symbol(message_text):
    """
    Returns: (symbol, expiries_list_sorted, weekly_list, monthly_list, underlying_price)
    expiries_list_sorted = weekly + monthly (same order as menu)
    """
    ticker, dtype, expiry_raw = parse_tg_input(message_text)
    if not ticker:
        raise RuntimeError("Could not parse ticker")

    price, chain, source = await fetch_chain_async(ticker)
    expiries = sorted(chain.keys(), key=lambda d: dt.datetime.strptime(d, "%d-%b-%Y").date())
    weekly, monthly = classify_expiries(expiries)
    combined = weekly + monthly
    return ticker, combined, weekly, monthly, price

def resolve_expiry_from_raw(expiry_raw, expiries_list):
    """
    Return matching expiry string from expiries_list given expiry_raw.
    expiry_raw may be None -> return None
    """
    if not expiry_raw:
        return None
    # exact match
    if expiry_raw in expiries_list:
        return expiry_raw
    # try parse into date and match
    d = _parse_date_formats(expiry_raw)
    if d:
        for e in expiries_list:
            try:
                ed = dt.datetime.strptime(e, "%d-%b-%Y").date()
                if ed == d:
                    return e
            except:
                continue
        # if d is first-of-month sentinel (mon-only), find last thursday of that month in list
        if d.day == 1:
            for e in expiries_list:
                ed = dt.datetime.strptime(e, "%d-%b-%Y").date()
                if ed.month == d.month and ed.year == d.year:
                    # prefer monthly expiry if it's last thursday
                    if _is_last_thursday_of_month(ed):
                        return e
            # else return first expiry in that month
            for e in expiries_list:
                ed = dt.datetime.strptime(e, "%d-%b-%Y").date()
                if ed.month == d.month and ed.year == d.year:
                    return e
    # try substring month match e.g., 'DEC'
    ur = expiry_raw.upper()
    for e in expiries_list:
        if ur in e.upper():
            return e
    return None

# -------------------------------
# 9. Async RR Scanner (enhanced)
# -------------------------------
async def scan_rr_async(message_text, desired_rr=2.0, k_target=1.0, expiry_override=None):
    """
    message_text: user text like "TCS-CE" or "TCS-CEPE" or "TCS-PE-DEC"
    expiry_override: explicit expiry string in NSE format '25-Dec-2025' OR None
    """
    ticker, dtype, expiry_raw = parse_tg_input(message_text)

    # build rights list
    if dtype == "CE":
        rights = ["CALL"]
    elif dtype == "PE":
        rights = ["PUT"]
    else:
        rights = ["CALL", "PUT"]

    price, chain, source = await fetch_chain_async(ticker)
    expiries = sorted(chain.keys(), key=lambda d: dt.datetime.strptime(d, "%d-%b-%Y").date())

    # Determine selected expiry
    chosen_expiry = None
    if expiry_override:
        chosen_expiry = expiry_override if expiry_override in expiries else None

    if not chosen_expiry and expiry_raw:
        chosen_expiry = resolve_expiry_from_raw(expiry_raw, expiries)

    if not chosen_expiry:
        # default to nearest (first one)
        if expiries:
            chosen_expiry = expiries[0]
        else:
            raise RuntimeError("No expiries available")

    days = days_to_expiry_nse(chosen_expiry)

    results = {}
    for r in rights:
        df = chain[chosen_expiry]['calls' if r == 'CALL' else 'puts']
        scored = compute_rr_strict(price, df, r, days, k_target)
        hits = scored[scored['RR'] >= desired_rr].head(20)
        results[r] = {
            'expiry': chosen_expiry,
            'days': days,
            'underlying': price,
            'candidates': hits
        }
    return results

# -------------------------------
# 10. Format for Telegram
# -------------------------------
def format_for_telegram(results, desired_rr):
    lines = []
    for right, payload in results.items():
        lines.append(f"*{right}* expiry {payload['expiry']} (Days Remaining {payload['days']}) — Underlying {payload['underlying']:.2f}\n")
        df = payload['candidates']
        if df is None or df.empty:
            lines.append(f"_No strikes found with RR ≥ {desired_rr}_\n")
            continue
        for _, r in df.iterrows():
            lines.append(
                f"Strike {int(r['strike'])} | Premium {r['premium']:.2f} | IV {(r['iv']*100):.1f}% | OI {r['openInterest']} | EM {r['EM']:.2f} | Target {r['target_price']:.2f} | RR {r['RR']:.2f} \n"
            )
        lines.append("\n")
    return "\n".join(lines)

# -------------------------------
# 11. Public wrapper for telegram integration
# -------------------------------
async def get_expiry_menu_and_state(message_text):
    """
    Returns: menu_text, state where state = {"symbol":..., "expiries": [...], "weekly": [...], "monthly": [...], "underlying": ...}
    """
    symbol, combined, weekly, monthly, underlying = await list_available_expiries_for_symbol(message_text)
    menu = format_grouped_expiry_menu(symbol, weekly, monthly)
    state = {
        "symbol": symbol,
        "expiries": combined,
        "weekly": weekly,
        "monthly": monthly,
        "underlying": underlying,
    }
    return menu, state

async def process_option_rr_telegram(message_text, expiry_selection=None, desired_rr=2.0):
    """
    expiry_selection: either None (auto), an index (int), or an expiry string like '25-Dec-2025'
    If index is provided, it selects from the expiries available for the message_text.
    """
    ticker, dtype, expiry_raw = parse_tg_input(message_text)

    # If expiry_selection is integer index, resolve to expiry string
    expiry_str = None
    if isinstance(expiry_selection, int):
        # fetch expiries
        _, combined, _, _, _ = await list_available_expiries_for_symbol(message_text)
        if 0 <= expiry_selection < len(combined):
            expiry_str = combined[expiry_selection]
        else:
            raise RuntimeError("Invalid expiry index")
    elif isinstance(expiry_selection, str):
        expiry_str = expiry_selection

    results = await scan_rr_async(message_text, desired_rr=desired_rr, k_target=1.0, expiry_override=expiry_str)
    return format_for_telegram(results, desired_rr)
