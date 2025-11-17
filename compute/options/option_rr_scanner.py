# filename: compute/options/option_rr_scanner.py
# CLEAN REWRITE WITH STRICT MODE (OPTION A) + NSE FIRST

import math
import pandas as pd
import numpy as np
import datetime as dt
import yfinance as yf
import aiohttp
import asyncio

# -------------------------------
# 1. Parse TG Message
# -------------------------------
def parse_tg_input(msg: str):
    parts = msg.strip().upper().split('-')
    ticker = parts[0]
    rights = []
    if len(parts) > 1:
        suf = parts[1]
        if 'CE' in suf:
            rights.append('CALL')
        if 'PE' in suf:
            rights.append('PUT')
    if not rights:
        rights = ['CALL', 'PUT']
    return ticker, rights

# -------------------------------
# 2. Underlying price from YF
# -------------------------------
def fetch_underlying_price(ticker):
    yf_t = ticker if ticker.endswith('.NS') else f"{ticker}.NS"
    tk = yf.Ticker(yf_t)
    info = tk.history(period='1d', interval='1m')
    if info.empty:
        raise RuntimeError("No price data from yfinance")
    return float(info['Close'].iloc[-1]), tk

# -------------------------------
# 3. NSE Option Chain (Primary)
# -------------------------------
NSE_OC_URL = "https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"

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

    calls_df = pd.DataFrame(calls)
    puts_df = pd.DataFrame(puts)

    # Normalize field names
    for df in (calls_df, puts_df):
        df.rename(columns={
            "last_price": "lastPrice",
            "iv": "impliedVolatility"
        }, inplace=True, errors='ignore')

    expiries = sorted(list({e.get("expiryDate") for e in records if e.get("expiryDate")}))

    expiry_map = {}
    for e in expiries:
        expiry_map[e] = {
            'calls': calls_df[calls_df['expiryDate'] == e],
            'puts': puts_df[puts_df['expiryDate'] == e]
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
def days_to_expiry_nse(exp_str):
    try:
        return max(1, (dt.datetime.strptime(exp_str, "%d-%b-%Y").date() - dt.date.today()).days)
    except:
        return 7

def expected_move_from_iv(S, iv_decimal, days):
    return S * iv_decimal * math.sqrt(days / 252)

# -------------------------------
# 6. STRICT RR SCORING (MODE A)
# -------------------------------
def compute_rr_strict(S, df, right, days, k_target=1.0):
    if df.empty:
        return pd.DataFrame([])

    df = df.copy()

    # Strict filter: keep only real tradable strikes
    df = df[(df['lastPrice'] > 0) & (df['impliedVolatility'] > 0) & (df['openInterest'] > 0)]
    if df.empty:
        return pd.DataFrame([])

    rows = []
    for _, r in df.iterrows():
        K = float(r['strikePrice'] if 'strikePrice' in r else r['strike'])
        premium = float(r['lastPrice'])
        iv = float(r['impliedVolatility'])
        if iv > 5:
            iv = iv / 100

        EM = expected_move_from_iv(S, iv, days)

        if right == 'CALL':
            target = S + k_target * EM
            payoff = max(0, target - K)
        else:
            target = S - k_target * EM
            payoff = max(0, K - target)

        rr = payoff / premium if premium > 0 else 0

        rows.append({
            'strike': K,
            'premium': premium,
            'iv': iv,
            'EM': EM,
            'target_price': target,
            'payoff': payoff,
            'RR': rr,
            'openInterest': r['openInterest']
        })

    return pd.DataFrame(rows).sort_values('RR', ascending=False)

# -------------------------------
# 7. NSE-first async fetch
# -------------------------------
async def fetch_chain_async(symbol):
    # Try NSE first
    try:
        chain_nse = await fetch_option_chain_nse(symbol)
        price, _ = fetch_underlying_price(symbol)
        return price, chain_nse, 'NSE'
    except:
        pass

    # Fallback to yfinance
    price, tk = fetch_underlying_price(symbol)
    chain_yf = fetch_option_chain_yf(tk)
    return price, chain_yf, 'YF'

# -------------------------------
# 8. Async RR Scanner
# -------------------------------
async def scan_rr_async(message_text, desired_rr=2.0, k_target=1.0, expiry_index=0):
    ticker, rights = parse_tg_input(message_text)
    price, chain, source = await fetch_chain_async(ticker)

    if source == 'NSE':
        expiries = sorted(chain.keys(), key=lambda d: dt.datetime.strptime(d, '%d-%b-%Y').date())
        exp = expiries[min(expiry_index, len(expiries)-1)]
        days = days_to_expiry_nse(exp)
    else:
        expiries = sorted(chain.keys())
        exp = expiries[min(expiry_index, len(expiries)-1)]
        days = 7

    results = {}
    for r in rights:
        df = chain[exp]['calls' if r == 'CALL' else 'puts']
        scored = compute_rr_strict(price, df, r, days, k_target)
        hits = scored[scored['RR'] >= desired_rr].head(10)

        results[r] = {
            'expiry': exp,
            'days': days,
            'underlying': price,
            'candidates': hits
        }
    return results

# -------------------------------
# 9. Format for Telegram
# -------------------------------
def format_for_telegram(results, desired_rr):
    lines = []

    for right, payload in results.items():
        lines.append(f"*{right}* expiry {payload['expiry']} (Days Remaining {payload['days']}) — Underlying {payload['underlying']:.2f}\n")
        df = payload['candidates']

        if df.empty:
            lines.append(f"_No strikes found with RR ≥ {desired_rr}_")
            continue

        for _, r in df.iterrows():
            lines.append(
                f"Strike {int(r['strike'])} | Premium {r['premium']:.2f} | IV {(r['iv']*100):.1f}% | OI {r['openInterest']} | EM {r['EM']:.2f} | Target {r['target_price']:.2f} | RR {r['RR']:.2f} \n"
            )
        lines.append("\n")

    return "\n".join(lines)

# -------------------------------
# 10. Telegram Wrapper
# -------------------------------
async def process_option_rr_telegram(message_text):
    results = await scan_rr_async(message_text)
    return format_for_telegram(results, 5.0)
