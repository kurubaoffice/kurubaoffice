# compute/options/rr_engine.py
import math
import pandas as pd
import numpy as np
import datetime as dt
import yfinance as yf
import aiohttp
from typing import Tuple, Dict, List, Optional
from .rr_parser import parse_tg_input
from .expiry_menu import classify_expiries, combined_order
import re

NSE_OC_URL = "https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"

# -------------------------
# Utils
# -------------------------
def _normalize_iv(iv) -> float:
    try:
        iv = float(iv)
    except:
        return 0.0
    if iv > 5:
        iv = iv / 100.0
    return iv

def expected_move_from_iv(S: float, iv: float, days: int) -> float:
    return S * iv * math.sqrt(days / 252.0)

def days_to_expiry_nse(exp_str: str) -> int:
    try:
        return max(1, (dt.datetime.strptime(exp_str, "%d-%b-%Y").date() - dt.date.today()).days)
    except:
        return 7

# -------------------------
# fetch underlying price
# -------------------------
def fetch_underlying_price(ticker: str) -> Tuple[float, yf.Ticker]:
    yf_t = ticker if ticker.endswith('.NS') else f"{ticker}.NS"
    tk = yf.Ticker(yf_t)
    info = tk.history(period='1d', interval='1m')
    if info.empty:
        raise RuntimeError("No price data from yfinance")
    return float(info['Close'].iloc[-1]), tk

# -------------------------
# fetch NSE option chain
# -------------------------
async def fetch_option_chain_nse(symbol: str) -> Dict[str, Dict]:
    headers = {
        "user-agent": "Mozilla/5.0",
        "accept": "application/json",
        "accept-language": "en-US,en;q=0.9"
    }
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(NSE_OC_URL.format(symbol=symbol)) as resp:
            if resp.status != 200:
                raise RuntimeError(f"NSE OC fetch failed: status {resp.status}")
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

    # normalize names
    for df in (calls_df, puts_df):
        df.rename(columns={"last_price":"lastPrice", "iv":"impliedVolatility"}, inplace=True, errors='ignore')

    expiries = sorted(list({e.get("expiryDate") for e in records if e.get("expiryDate")}),
                      key=lambda d: dt.datetime.strptime(d, "%d-%b-%Y").date())

    result = {}
    for e in expiries:
        result[e] = {
            "calls": calls_df[calls_df['expiryDate'] == e] if not calls_df.empty else pd.DataFrame(),
            "puts": puts_df[puts_df['expiryDate'] == e] if not puts_df.empty else pd.DataFrame()
        }
    return result

# -------------------------
# fallback to yfinance option chain
# -------------------------
def fetch_option_chain_yf(tk) -> Dict[str, Dict]:
    res = {}
    for e in tk.options:
        oc = tk.option_chain(e)
        c = oc.calls.copy()
        p = oc.puts.copy()
        c['expiry'] = e
        p['expiry'] = e
        res[e] = {'calls': c, 'puts': p}
    return res

# -------------------------
# combined fetch (NSE first)
# -------------------------
async def fetch_chain_async(symbol: str) -> Tuple[float, Dict[str, Dict], str]:
    # try NSE
    try:
        chain_nse = await fetch_option_chain_nse(symbol)
        price, tk = fetch_underlying_price(symbol)
        return price, chain_nse, 'NSE'
    except Exception:
        # fallback to yfinance
        price, tk = fetch_underlying_price(symbol)
        chain_yf = fetch_option_chain_yf(tk)
        return price, chain_yf, 'YF'

# -------------------------
# RR scoring
# -------------------------
def compute_rr_strict(S: float, df: pd.DataFrame, right: str, days: int, k_target=1.0) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame([])

    df = df.copy()

    # map columns
    lp_col = 'lastPrice' if 'lastPrice' in df.columns else ('last_price' if 'last_price' in df.columns else None)
    iv_col = 'impliedVolatility' if 'impliedVolatility' in df.columns else ('iv' if 'iv' in df.columns else None)
    strike_col = 'strikePrice' if 'strikePrice' in df.columns else ('strike' if 'strike' in df.columns else None)
    oi_col = 'openInterest' if 'openInterest' in df.columns else 'openInterest'

    if lp_col and iv_col and strike_col:
        df = df[(df[lp_col] > 0) & (df[iv_col] > 0)]
    if df.empty:
        return pd.DataFrame([])

    rows = []
    for _, r in df.iterrows():
        try:
            K = float(r.get(strike_col, np.nan))
        except:
            continue
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

# -------------------------
# Listing expiries API
# -------------------------
async def list_available_expiries_for_symbol(message_text: str) -> Tuple[str, List[str], List[str], List[str], float]:
    """
    Return symbol, combined_expiries (weekly+monthly), weekly, monthly, underlying price
    """
    ticker, dtype, expiry_raw = parse_tg_input(message_text)
    if not ticker:
        raise RuntimeError("Could not parse ticker")

    price, chain, source = await fetch_chain_async(ticker)
    expiries = sorted(chain.keys(), key=lambda d: dt.datetime.strptime(d, "%d-%b-%Y").date())
    weekly, monthly = classify_expiries(expiries)
    combined = combined_order(weekly, monthly)
    return ticker, combined, weekly, monthly, price

# -------------------------
# scan API (single expiry)
# -------------------------
async def scan_rr_for_expiry(message_text: str, expiry: str, desired_rr: float = 2.0, k_target: float = 1.0) -> Dict:
    ticker, dtype, expiry_raw = parse_tg_input(message_text)
    if dtype == "CE":
        rights = ["CALL"]
    elif dtype == "PE":
        rights = ["PUT"]
    else:
        rights = ["CALL", "PUT"]

    price, chain, source = await fetch_chain_async(ticker)

    if expiry not in chain:
        # try to match substrings (e.g., user passed "DEC" or "25DEC")
        matched = None
        ur = expiry.upper()
        for e in chain.keys():
            if ur in e.upper():
                matched = e
                break
        if matched:
            expiry = matched
        else:
            # fallback to nearest
            expiry = sorted(chain.keys(), key=lambda d: dt.datetime.strptime(d, "%d-%b-%Y").date())[0]

    days = days_to_expiry_nse(expiry)
    results = {}
    for r in rights:
        df = chain[expiry]['calls' if r == 'CALL' else 'puts']
        scored = compute_rr_strict(price, df, r, days, k_target)
        hits = scored[scored['RR'] >= desired_rr].head(20)
        results[r] = {
            'expiry': expiry,
            'days': days,
            'underlying': price,
            'candidates': hits
        }
    return results

# -------------------------
# Formatting
# -------------------------
def format_for_telegram(results: Dict, desired_rr: float) -> str:
    lines = []
    for right, payload in results.items():
        lines.append(f"*{right}* expiry {payload['expiry']} (Days Remaining {payload['days']}) — Underlying {payload['underlying']:.2f}\n")
        df = payload['candidates']
        if df is None or df.empty:
            lines.append(f"_No strikes found with RR ≥ {desired_rr}_\n")
            continue
        for _, r in df.iterrows():
            iv_pct = (r['iv'] * 100) if r.get('iv') is not None else 0.0
            lines.append(f"Strike {int(r['strike'])} | Premium {r['premium']:.2f} | IV {iv_pct:.1f}% | OI {r['openInterest']} | EM {r['EM']:.2f} | Target {r['target_price']:.2f} | RR {r['RR']:.2f} \n")
        lines.append("\n")
    return "\n".join(lines)

# -------------------------
# Public wrapper used by bot
# -------------------------
async def get_expiry_menu_and_state(message_text: str):
    symbol, combined, weekly, monthly, underlying = await list_available_expiries_for_symbol(message_text)
    # return menu text and state dict
    from .expiry_menu import format_grouped_expiry_menu
    menu = format_grouped_expiry_menu(symbol, weekly, monthly)
    state = {
        "symbol": symbol,
        "expiries": combined,
        "weekly": weekly,
        "monthly": monthly,
        "underlying": underlying
    }
    return menu, state

async def process_option_rr_telegram(message_text: str, expiry_selection: Optional[int] = None, expiry_str: Optional[str] = None, desired_rr: float = 2.0):
    """
    expiry_selection: zero-based index referring to combined expiries returned by list_available_expiries_for_symbol()
    expiry_str: explicit expiry string to resolve (e.g., '25-Dec-2025' or 'DEC' or '25DEC')
    """
    if expiry_selection is not None:
        # resolve to expiry string
        _, combined, _, _, _ = await list_available_expiries_for_symbol(message_text)
        if expiry_selection < 0 or expiry_selection >= len(combined):
            raise RuntimeError("Invalid expiry index")
        chosen = combined[expiry_selection]
    elif expiry_str:
        chosen = expiry_str
    else:
        # fallback: choose nearest
        _, combined, _, _, _ = await list_available_expiries_for_symbol(message_text)
        chosen = combined[0]

    results = await scan_rr_for_expiry(message_text, chosen, desired_rr=desired_rr)
    return format_for_telegram(results, desired_rr)
