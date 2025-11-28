# compute/bnf_engine.py
"""
BankNifty option helper: menu + analysis + suggestions
Enhanced and cleaned:
 - Trend detection (advanced)
 - Support/Resistance (classic OI walls)
 - PCR (ATM & Total)
 - Max Pain calculation
 - R:R estimates for picks
 - Suggestions + Trend Radar (emoji bar)
 - Robust / defensive handling for missing columns
"""

from typing import Tuple, Dict, List, Optional
import datetime as dt
import numpy as np
import pandas as pd

from fetcher.fetch_banknifty_option_chain import fetch_banknifty_option_chain
from compute.options.strike_selector import pick_best_ce_pe
# We keep these imports for compatibility though not all are used in every function:
from compute.options.rr_engine import list_available_expiries_for_symbol, scan_rr_for_expiry, format_for_telegram
from compute.options.expiry_menu import classify_expiries, combined_order


# -----------------------
# Utilities
# -----------------------

def safe_series(df, *cols):
    """
    Returns the first existing column as a numeric Series.
    If none exist, returns a zero-filled Series with same length.
    """
    for c in cols:
        if c in df.columns:
            return pd.to_numeric(df[c], errors='coerce').fillna(0)
    # fallback = return zero Series, NEVER int
    return pd.Series([0] * len(df))

def _to_date(expiry_str: str) -> dt.date:
    return dt.datetime.strptime(expiry_str, "%d-%b-%Y").date()


def pick_3w_2m(expiries: List[str]) -> List[str]:
    weekly, monthly = classify_expiries(expiries)
    selected = []

    # first up to 3 weekly
    for e in weekly[:3]:
        selected.append(e)

    # first up to 2 monthly
    for e in monthly[:2]:
        selected.append(e)

    # if not enough, fill from combined order
    combined = combined_order(weekly, monthly)
    idx = 0
    while len(selected) < 5 and idx < len(combined):
        if combined[idx] not in selected:
            selected.append(combined[idx])
        idx += 1

    return selected


# -----------------------
# Trend detection advanced
# -----------------------
def detect_bnf_trend_advanced(oc_df: pd.DataFrame, spot: float) -> Tuple[str, int]:
    """
    Advanced BankNifty trend detection.
    Returns: (trend_text, score 0..100)
    Defensive for missing data.
    """
    score = 50  # neutral baseline

    if oc_df is None or oc_df.empty or spot is None or (isinstance(spot, float) and np.isnan(spot)):
        return "⚪ No Data", 50

    # ensure numeric strike
    oc = oc_df.copy()
    oc['strike'] = pd.to_numeric(oc['strike'], errors='coerce')
    strikes = sorted([s for s in oc['strike'].unique() if not np.isnan(s)])
    if not strikes:
        return "⚪ No Strikes", 50

    atm = min(strikes, key=lambda s: abs(s - spot))

    # estimate spacing and nearby window
    spacing = int(np.median(np.diff(strikes))) if len(strikes) >= 2 else 100
    lo = atm - 3 * spacing
    hi = atm + 3 * spacing
    nearby = oc[(oc['strike'] >= lo) & (oc['strike'] <= hi)]

    # safe sums
    def safe_sum(df, col):
        if col in df.columns:
            return pd.to_numeric(df[col], errors='coerce').fillna(0).sum()
        return 0

    ce_oi = safe_sum(nearby, 'ce_oi')
    pe_oi = safe_sum(nearby, 'pe_oi')
    ce_chg = safe_sum(nearby, 'ce_change_oi')
    pe_chg = safe_sum(nearby, 'pe_change_oi')
    ce_vol = safe_sum(nearby, 'ce_volume')
    pe_vol = safe_sum(nearby, 'pe_volume')

    ce_iv = None
    pe_iv = None
    if 'ce_iv' in nearby.columns:
        ce_iv = pd.to_numeric(nearby['ce_iv'], errors='coerce').mean()
    if 'pe_iv' in nearby.columns:
        pe_iv = pd.to_numeric(nearby['pe_iv'], errors='coerce').mean()

    # Price trend (if prev_close provided)
    if 'prev_close' in oc.columns:
        try:
            prev = float(oc['prev_close'].iloc[0])
            if prev > 0:
                move = ((spot - prev) / prev) * 100
                if move > 0.35:
                    score += 8
                elif move < -0.35:
                    score -= 8
        except Exception:
            pass

    # ΔOI influence
    oi_diff = ce_chg - pe_chg
    if oi_diff > 0:
        score += 10
    elif oi_diff < 0:
        score -= 10

    # OI strength
    if ce_oi > pe_oi * 1.3:
        score += 6
    elif pe_oi > ce_oi * 1.3:
        score -= 6

    # Volume influence
    vol_diff = ce_vol - pe_vol
    if vol_diff > 0:
        score += 5
    elif vol_diff < 0:
        score -= 5

    # IV divergence hint
    if ce_iv is not None and pe_iv is not None:
        try:
            if ce_iv > pe_iv + 1:
                score -= 4
            elif pe_iv > ce_iv + 1:
                score += 4
        except Exception:
            pass

    score = int(max(0, min(100, score)))

    if score >= 70:
        return "🔺 Strong Uptrend", score
    elif score >= 55:
        return "🟢 Mild Uptrend", score
    elif score <= 30:
        return "🔻 Strong Downtrend", score
    elif score <= 45:
        return "🔴 Mild Downtrend", score
    else:
        return "⚪ Sideways / Choppy", score


# -----------------------
# RR calculator
# -----------------------
def compute_rr_for_strike(spot: float, strike: float, premium: float) -> float:
    try:
        expected_move = abs(strike - spot)
        if premium is None or premium <= 0:
            return 0.0
        return round(expected_move / float(premium), 2)
    except Exception:
        return 0.0


# -----------------------
# Suggestions
# -----------------------
def suggestions_from_picks(picks: Dict, spot: float) -> List[str]:
    out: List[str] = []
    best_ce = picks.get("best_ce")
    best_pe = picks.get("best_pe")

    if best_ce and best_pe:
        try:
            ce_delta = int(best_ce.get("change_oi", 0))
            pe_delta = int(best_pe.get("change_oi", 0))
            if ce_delta > 0 and pe_delta <= 0:
                out.append("🔺 Bullish signals: CE accumulation + PE unwinding.")
            if pe_delta > 0 and ce_delta <= 0:
                out.append("🔻 Bearish signals: PE accumulation + CE unwinding.")
        except Exception:
            pass

    if best_ce:
        rr_ce = compute_rr_for_strike(spot, best_ce["strike"], best_ce.get("ltp", best_ce.get("lastPrice", 0)))
        out.append(f"🔥 CE R:R ~ {rr_ce}")

    if best_pe:
        rr_pe = compute_rr_for_strike(spot, best_pe["strike"], best_pe.get("ltp", best_pe.get("lastPrice", 0)))
        out.append(f"🐻 PE R:R ~ {rr_pe}")

    # liquidity hint
    try:
        if best_ce and best_pe and int(best_ce.get("oi", 0)) > int(best_pe.get("oi", 0)) * 2:
            out.append("⚠️ CE side much more liquid than PE — watch for CE-led moves.")
    except Exception:
        pass

    return out


# -----------------------
# Support & Resistance (Classic OI Walls)
# -----------------------
def compute_support_resistance(oc_df: pd.DataFrame) -> Tuple[Optional[int], Optional[int]]:
    """
    Classic OI walls:
      - Support = strike with highest PE OI
      - Resistance = strike with highest CE OI
    Returns (support_strike_or_None, resistance_strike_or_None)
    """
    if oc_df is None or oc_df.empty:
        return None, None

    df = oc_df.copy()
    # prefer aggregated columns if present
    if 'pe_oi' in df.columns:
        df['pe_oi_num'] = pd.to_numeric(df['pe_oi'], errors='coerce').fillna(0)
    else:
        df['pe_oi_num'] = safe_series(df, 'pe_oi', 'PE_openInterest', 'pe_openInterest')

    if 'ce_oi' in df.columns:
        df['ce_oi_num'] = pd.to_numeric(df['ce_oi'], errors='coerce').fillna(0)
    else:
        df['ce_oi_num'] = safe_series(df, 'ce_oi', 'CE_openInterest', 'ce_openInterest')

    # ensure strike numeric
    df['strike'] = pd.to_numeric(df['strike'], errors='coerce')

    try:
        support_row = df.loc[df['pe_oi_num'].idxmax()]
        resistance_row = df.loc[df['ce_oi_num'].idxmax()]
        support = int(support_row['strike'])
        resistance = int(resistance_row['strike'])
        return support, resistance
    except Exception:
        return None, None


# -----------------------
# PCR calculations
# -----------------------
def compute_pcr(oc_df: pd.DataFrame, spot: float) -> Tuple[float, float]:
    """
    Returns: (atm_pcr, total_pcr)
    - total_pcr = total PE OI / total CE OI
    - atm_pcr = PE OI / CE OI at ATM strike (or close window)
    """
    if oc_df is None or oc_df.empty:
        return 0.0, 0.0

    df = oc_df.copy()
    df['strike'] = pd.to_numeric(df['strike'], errors='coerce')
    df = df.dropna(subset=['strike']).reset_index(drop=True)

    # find total OI
    total_pe = safe_series(df, 'pe_oi', 'PE_openInterest', 'put_openInterest').sum()

    total_ce = safe_series(df, 'ce_oi', 'CE_openInterest', 'call_openInterest').sum()

    total_pcr = float(total_pe / total_ce) if total_ce > 0 else (float('inf') if total_pe > 0 else 0.0)

    # ATM PCR
    strikes = sorted(df['strike'].unique())
    if not strikes:
        return 0.0, round(float(total_pcr), 2)
    atm = min(strikes, key=lambda s: abs(s - spot))
    atm_rows = df[df['strike'] == atm]
    if atm_rows.empty:
        spacing = int(np.median(np.diff(strikes))) if len(strikes) >= 2 else 100
        atm_rows = df[df['strike'].between(atm - spacing, atm + spacing)]

    atm_pe = safe_series(atm_rows, 'pe_oi', 'PE_openInterest').sum()
    atm_ce = safe_series(atm_rows, 'ce_oi', 'CE_openInterest').sum()

    #atm_ce = pd.to_numeric(atm_rows.get('ce_oi') or atm_rows.get('CE_openInterest') or 0, errors='coerce').fillna(0).sum()
    atm_pcr = float(atm_pe / atm_ce) if atm_ce > 0 else (float('inf') if atm_pe > 0 else 0.0)

    return round(float(atm_pcr), 2), round(float(total_pcr), 2)


# -----------------------
# Max Pain
# -----------------------
def compute_max_pain(oc_df: pd.DataFrame) -> Tuple[Optional[float], Dict[float, float]]:
    """
    Compute Max Pain by summing intrinsic payouts * OI across strikes.
    Returns: (max_pain_price, payouts_by_price_dict)
    """
    if oc_df is None or oc_df.empty:
        return None, {}

    df = oc_df.copy()
    df['strike'] = pd.to_numeric(df['strike'], errors='coerce')
    df = df.dropna(subset=['strike']).reset_index(drop=True)

    # normalized OI columns
    df['call_oi'] = safe_series(df, 'ce_oi', 'CE_openInterest')
    df['put_oi'] = safe_series(df, 'pe_oi', 'PE_openInterest')

    candidate_prices = sorted(df['strike'].unique())
    payouts: Dict[float, float] = {}
    for p in candidate_prices:
        calls = df[df['strike'] < p]
        calls_payout = ((p - calls['strike']) * calls['call_oi']).sum()
        puts = df[df['strike'] > p]
        puts_payout = ((puts['strike'] - p) * puts['put_oi']).sum()
        total = calls_payout + puts_payout
        payouts[p] = float(total)

    if not payouts:
        return None, {}

    max_pain_price = min(payouts.items(), key=lambda kv: kv[1])[0]
    return float(max_pain_price), payouts


# -----------------------
# Trend Radar (emoji bar)
# -----------------------
def trend_radar_bar(score: Optional[int]) -> str:
    if score is None:
        return "⬜⬜⬜⬜⬜"
    score = int(max(0, min(100, score)))
    full = score // 20
    rem = score % 20
    half = 1 if rem >= 10 and full < 5 else 0
    blocks = []
    for _ in range(full):
        blocks.append("🟩")
    if half:
        blocks.append("🟨")
    while len(blocks) < 5:
        blocks.append("⬜")
    return "".join(blocks)


# -----------------------
# Menu builder
# -----------------------
async def get_bnf_expiry_menu_and_state() -> Tuple[str, dict]:
    oc_df = fetch_banknifty_option_chain()
    if oc_df is None or oc_df.empty:
        raise RuntimeError("No BankNifty option chain data available")

    if 'expiry' not in oc_df.columns:
        raise RuntimeError("Option chain missing expiry column")

    expiries = sorted(list(oc_df['expiry'].unique()), key=lambda x: dt.datetime.strptime(x, "%d-%b-%Y"))
    selected = pick_3w_2m(expiries)

    try:
        spot = float(oc_df['spot'].iloc[0])
    except Exception:
        spot = float('nan')

    lines = ["📅 Available Expiries for BANKNIFTY", ""]
    idx = 1
    for e in selected:
        lines.append(f"{idx}️⃣ {e}")
        idx += 1
    lines.append(f"\nReply with a number (1–{idx-1}) to select expiry.")
    state = {"symbol": "BANKNIFTY", "expiries": selected, "underlying": spot}
    return "\n".join(lines), state


# -----------------------
# Full analysis
# -----------------------
async def analyze_bnf_for_expiry(expiry: str) -> str:
    oc_df = fetch_banknifty_option_chain()
    # --- DEFENSIVE STRING FIX ---
    if 'expiry' in oc_df.columns:
        oc_df['expiry'] = oc_df['expiry'].astype(str).fillna("")
    if 'type' in oc_df.columns:
        oc_df['type'] = oc_df['type'].astype(str).fillna("")
    if oc_df is None or oc_df.empty:
        raise RuntimeError("No BankNifty option chain available")

    # filter for expiry if present
    if 'expiry' in oc_df.columns:
        oc = oc_df[oc_df['expiry'] == expiry].copy()
        if oc.empty:
            # fallback to first expiry or whole df
            oc = oc_df.copy()
    else:
        oc = oc_df.copy()

    # ensure strike numeric
    oc['strike'] = pd.to_numeric(oc['strike'], errors='coerce')
    oc = oc.dropna(subset=['strike']).reset_index(drop=True)

    # spot extraction
    try:
        spot = float(oc_df['spot'].iloc[0])
    except Exception:
        spot = float('nan')

    # picks using your existing selector
    picks = pick_best_ce_pe(oc, spot)

    # trend detection returns (text, score)
    trend_text, trend_score = detect_bnf_trend_advanced(oc_df, spot)
    radar = trend_radar_bar(trend_score)

    # compute support/resistance
    support_strike, resistance_strike = compute_support_resistance(oc_df)
    sup_text = f"{support_strike}" if support_strike is not None else "—"
    res_text = f"{resistance_strike}" if resistance_strike is not None else "—"

    # PCR and MaxPain
    atm_pcr, total_pcr = compute_pcr(oc_df, spot)
    max_pain_price, payouts = compute_max_pain(oc_df)

    # compute R:R for picks
    if picks.get("best_ce"):
        picks["best_ce"]["rr"] = compute_rr_for_strike(
            spot,
            picks["best_ce"]["strike"],
            picks["best_ce"].get("ltp", picks["best_ce"].get("lastPrice", 0))
        )

    if picks.get("best_pe"):
        picks["best_pe"]["rr"] = compute_rr_for_strike(
            spot,
            picks["best_pe"]["strike"],
            picks["best_pe"].get("ltp", picks["best_pe"].get("lastPrice", 0))
        )

    # suggestions
    sugg = suggestions_from_picks(picks, spot)

    # Build final output (trend + meta above CE/PE)
    lines: List[str] = []
    lines.append("📈 BankNifty Option Analysis")
    lines.append(f"Expiry: {expiry}")
    lines.append(f"Spot: {spot:.2f}\n")
    lines.append(f"📊 Trend: {trend_text} ({trend_score}%) {radar}\n")
    lines.append(f"🛡 Support (PE OI wall): {sup_text}   🔰 Resistance (CE OI wall): {res_text}")
    lines.append(f"📊 PCR (ATM / Total): {atm_pcr} / {total_pcr}")
    if max_pain_price is not None:
        lines.append(f"🎯 Max Pain: {max_pain_price}")
    else:
        lines.append("🎯 Max Pain: —")
    lines.append("")

    # CE block
    ce = picks.get("best_ce")
    if ce:
        lines.append("🔥 BEST CE")
        lines.append(f"Strike: {ce['strike']}  Premium: {ce.get('ltp', ce.get('lastPrice', '—'))}  OI: {ce.get('oi', '—')}  ΔOI: {ce.get('change_oi', '—')}")
        lines.append(f"RR: {ce.get('rr', '—')}\n")

    # PE block
    pe = picks.get("best_pe")
    if pe:
        lines.append("🐻 BEST PE")
        lines.append(f"Strike: {pe['strike']}  Premium: {pe.get('ltp', pe.get('lastPrice', '—'))}  OI: {pe.get('oi', '—')}  ΔOI: {pe.get('change_oi', '—')}")
        lines.append(f"RR: {pe.get('rr', '—')}\n")

    # suggestions
    if sugg:
        lines.append("💡 Suggestions:")
        for s in sugg:
            lines.append(f"• {s}")

    return "\n".join(lines)
