# compute/options/rr_engine.py
import math
import pandas as pd
import numpy as np
import datetime as dt
import yfinance as yf
import aiohttp
from typing import Tuple, Dict, List, Optional, Any
from .rr_parser import parse_tg_input
from .expiry_menu import classify_expiries, combined_order
import re
import calendar

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

# Normal CDF using math.erf
def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

# Black-Scholes helper: returns d1, d2 plus greeks (call/put)
def _bs_d1d2(S: float, K: float, iv: float, T: float, r: float = 0.07) -> Tuple[float, float]:
    # iv is decimal (e.g., 0.2); T in years
    if iv <= 0 or T <= 0 or S <= 0 or K <= 0:
        return 0.0, 0.0
    try:
        d1 = (math.log(S / K) + (r + 0.5 * iv * iv) * T) / (iv * math.sqrt(T))
        d2 = d1 - iv * math.sqrt(T)
        return d1, d2
    except Exception:
        return 0.0, 0.0

def bs_greeks(right: str, S: float, K: float, iv: float, T: float, r: float = 0.07) -> Dict[str, float]:
    # returns approximate Delta, Gamma, Theta (per day), Vega (per 1 vol point)
    # Theta in currency per day, Vega per 1 vol (0.01)
    d1, d2 = _bs_d1d2(S, K, iv, T, r)
    N_d1 = _norm_cdf(d1)
    N_d2 = _norm_cdf(d2)
    pdf_d1 = (1.0 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * d1 * d1)
    # Delta
    if right == "CALL":
        delta = N_d1
    else:
        delta = N_d1 - 1.0
    # Gamma
    gamma = pdf_d1 / (S * iv * math.sqrt(T)) if iv > 0 and T > 0 and S > 0 else 0.0
    # Theta (approx per year -> convert to per day)
    try:
        term1 = - (S * pdf_d1 * iv) / (2 * math.sqrt(T))
        if right == "CALL":
            term2 = r * K * math.exp(-r * T) * N_d2
            theta = (term1 - term2) / 252.0
        else:
            term2 = r * K * math.exp(-r * T) * (1 - N_d2)
            theta = (term1 + term2) / 252.0
    except Exception:
        theta = 0.0
    # Vega (per 1 vol point -> 0.01)
    vega = S * pdf_d1 * math.sqrt(T) / 100.0 if iv > 0 and T > 0 else 0.0
    return {
        "delta": float(delta),
        "gamma": float(gamma),
        "theta": float(theta),
        "vega": float(vega)
    }

# -------------------------
# fetch underlying price
# -------------------------
def fetch_underlying_price(ticker: str) -> Tuple[float, Any]:
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
        df = df[(df[lp_col] > 0) & (df[iv_col] >= 0)]
    if df.empty:
        return pd.DataFrame([])

    rows = []
    T = max(1, days) / 252.0
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
            'openInterest': int(r.get(oi_col, 0)),
            'T_years': T
        })

    return pd.DataFrame(rows).sort_values('RR', ascending=False)

# -------------------------
# Max Pain calculation (from calls/puts DataFrames)
# -------------------------
def compute_max_pain_from_chain(calls_df: pd.DataFrame, puts_df: pd.DataFrame) -> Tuple[Optional[float], Dict[float, float]]:
    # Merge call/put OI per strike and compute total payout vs price candidates
    if (calls_df is None or calls_df.empty) and (puts_df is None or puts_df.empty):
        return None, {}
    # normalize strike and oi
    df_c = pd.DataFrame()
    df_p = pd.DataFrame()
    if calls_df is not None and not calls_df.empty:
        df_c = calls_df.rename(columns={'strikePrice':'strike', 'openInterest':'call_oi'}).copy()
        if 'call_oi' not in df_c.columns:
            df_c['call_oi'] = df_c.get('openInterest', 0)
    if puts_df is not None and not puts_df.empty:
        df_p = puts_df.rename(columns={'strikePrice':'strike', 'openInterest':'put_oi'}).copy()
        if 'put_oi' not in df_p.columns:
            df_p['put_oi'] = df_p.get('openInterest', 0)

    merged = pd.DataFrame({'strike': sorted(set(
        list(df_c['strike'].dropna().unique()) + list(df_p['strike'].dropna().unique())
    ))})
    merged = merged.merge(df_c[['strike', 'call_oi']].groupby('strike').sum().reset_index(), on='strike', how='left')
    merged = merged.merge(df_p[['strike', 'put_oi']].groupby('strike').sum().reset_index(), on='strike', how='left')
    merged['call_oi'] = pd.to_numeric(merged.get('call_oi', 0)).fillna(0)
    merged['put_oi'] = pd.to_numeric(merged.get('put_oi', 0)).fillna(0)

    payouts = {}
    strikes = sorted(merged['strike'].dropna().unique())
    if len(strikes) == 0:
        return None, {}
    for p in strikes:
        calls = merged[merged['strike'] < p]
        calls_payout = ((p - calls['strike']) * calls['call_oi']).sum()
        puts = merged[merged['strike'] > p]
        puts_payout = ((puts['strike'] - p) * puts['put_oi']).sum()
        total = float(calls_payout + puts_payout)
        payouts[float(p)] = total
    # max pain = price with minimum total payout
    max_pain_price = min(payouts.items(), key=lambda kv: kv[1])[0]
    return float(max_pain_price), payouts

# -------------------------
# Listing expiries API
# -------------------------
async def list_available_expiries_for_symbol(message_text: str) -> Tuple[str, List[str], List[str], List[str], float]:
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
            'candidates': hits,
            'raw_calls': chain[expiry].get('calls'),
            'raw_puts': chain[expiry].get('puts'),
        }
    return results

# -------------------------
# Formatting for Telegram - ENHANCED with 6 features
# -------------------------
def format_for_telegram(results: Dict, desired_rr: float) -> str:
    """
    Enhancements added:
     - Best strike summary at top
     - POP % (probability of profit) using BS d2
     - Breakeven price
     - R/R in ₹ terms (max reward and max risk)
     - Simple Greeks (Delta, Gamma, Theta, Vega)
     - Max Pain per expiry (computed from raw call/put OC)
    """
    lines = []
    # Determine best strike overall (highest RR) across rights
    best_overall = None
    best_rr = -1.0
    for right, payload in results.items():
        df = payload.get('candidates')
        if df is None or df.empty:
            continue
        for _, r in df.iterrows():
            if r['RR'] > best_rr:
                best_rr = float(r['RR'])
                best_overall = {
                    "right": right,
                    "strike": float(r['strike']),
                    "RR": float(r['RR']),
                    "premium": float(r['premium']),
                    "iv": float(r['iv']),
                    "EM": float(r['EM']),
                    "target": float(r['target_price'])
                }

    # Add best-strike summary if present
    if best_overall:
        lines.append("🎯 Best Strike Summary")
        lines.append(f"• Best {best_overall['right']}: Strike {int(best_overall['strike'])} (RR {best_overall['RR']:.2f})")
        lines.append(f"  Premium {best_overall['premium']:.2f} | IV {(best_overall['iv']*100):.1f}% | EM {best_overall['EM']:.2f} | Target {best_overall['target']:.2f}\n")

    # Add max pain per expiry if raw data provided (first payload)
    # try to compute per-right (they share same expiry)
    any_payload = next(iter(results.values()))
    raw_calls = any_payload.get('raw_calls')
    raw_puts = any_payload.get('raw_puts')
    try:
        mp_price, _ = compute_max_pain_from_chain(raw_calls, raw_puts)
        if mp_price is not None:
            lines.append(f"🧭 Max Pain (approx): {mp_price}\n")
    except Exception:
        pass

    # Now list candidate strikes with enhanced info
    for right, payload in results.items():
        lines.append(f"*{right}* expiry {payload['expiry']} (Days Remaining {payload['days']}) — Underlying {payload['underlying']:.2f}\n")
        df = payload['candidates']
        if df is None or df.empty:
            lines.append(f"_No strikes found with RR ≥ {desired_rr}_\n")
            continue

        for _, r in df.iterrows():
            S = float(payload['underlying'])
            K = float(r['strike'])
            premium = float(r['premium'])
            iv = float(r['iv'])
            days = int(payload['days'])
            T = float(r.get('T_years', max(1, days)/252.0))
            # Breakeven
            if right == "CALL":
                breakeven = K + premium
            else:
                breakeven = K - premium
            # Reward/risk in ₹
            max_reward = float(r.get('payoff', 0.0))  # payoff estimate per contract (not considering lot size)
            max_risk = premium
            # POP: probability option ends ITM (use N(d2) from BS)
            d1, d2 = _bs_d1d2(S, K, iv, T)
            if right == "CALL":
                pop = _norm_cdf(d2)  # prob S_T > K
            else:
                pop = 1.0 - _norm_cdf(d2)  # prob S_T < K
            # Greeks
            greeks = bs_greeks("CALL" if right == "CALL" else "PUT", S, K, iv, T)
            # Format lines
            iv_pct = iv * 100.0
            lines.append(
                f"Strike {int(K)} " )
            lines.append(f"• Premium: {premium:.2f}")
            lines.append(f"• openInterest: {int(r.get('openInterest',0))}")
            lines.append(f"• Target Price: {r.get('target_price'):.2f}")
            lines.append("")
            lines.append(f"• Breakeven: {breakeven:.2f}")
            lines.append(f"• Probability of Profit: {(pop*100):.1f}%  — probability of finishing ITM")
            #lines.append(f"• Reward: ₹{max_reward:.2f}  | Risk: ₹{max_risk:.2f}  | Reward/Risk: { (max_reward/max_risk) if max_risk>0 else float('inf') :.2f}")
            #lines.append(f"• Greeks: Δ {greeks['delta']:.2f} | Γ {greeks['gamma']:.4f} | Θ {greeks['theta']:.3f}/day | Vega {greeks['vega']:.2f}")
            #lines.append(f"• Note: EM {r.get('EM'):.2f} implies target {r.get('target_price'):.2f} (used for RR calc).")
            lines.append("")  # empty line between strikes

            # ---------------- EXIT PLAN (3 METHODS) ----------------

            # Determine risk level from IV
            iv_pct = r['iv'] * 100

            if iv_pct < 12:
                risk_tag = "Low Risk (IV < 12%)"
            elif iv_pct < 20:
                risk_tag = "Moderate Risk (12–20%)"
            elif iv_pct < 30:
                risk_tag = "High Risk (20–30%)"
            else:
                risk_tag = "Very High Risk (IV > 30%)"

            # 1) Premium-based Stop Loss based on IV%
            iv_pct = r['iv'] * 100
            if iv_pct <= 15:
                sl_pct = 0.25
            elif iv_pct <= 25:
                sl_pct = 0.30
            elif iv_pct <= 35:
                sl_pct = 0.40
            else:
                sl_pct = 0.50

            sl_premium = r['premium'] * (1 - sl_pct)

            # 2) Price-action exit using breakeven & EM
            breakeven = r['strike'] + r['premium'] if right == "CALL" else r['strike'] - r['premium']
            pa_exit = breakeven - (0.4 * r['EM']) if right == "CALL" else breakeven + (0.4 * r['EM'])

            # 3) OI Trend Exit Condition (Fail-safe)
            if right == "CALL":
                oi_exit_msg = "Exit if CE OI drops >20% or PE OI rises >20%"
            else:
                oi_exit_msg = "Exit if PE OI drops >20% or CE OI rises >20%"

            # Final Output Block
            lines.append("***** Exit Plan *****")
            lines.append(f"• {risk_tag}")
            lines.append(f"• SL Premium: `{sl_premium:.2f}`")
            #lines.append(f"• Price-Action Exit (Underlying): `{pa_exit:.2f}`")
            #lines.append(f"• OI Trend Exit: {oi_exit_msg}")
            lines.append("")

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
