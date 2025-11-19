# compute/bnf_engine.py
"""
BankNifty option helper: menu + analysis + suggestions
Depends on existing project utilities:
- fetch_banknifty_option_chain
- pick_best_ce_pe
- list_available_expiries_for_symbol / scan_rr_for_expiry / format_for_telegram
"""

from typing import Tuple, Dict, List, Optional
import datetime as dt
import numpy as np

from fetcher.fetch_banknifty_option_chain import fetch_banknifty_option_chain
from compute.options.strike_selector import pick_best_ce_pe
from compute.options.rr_engine import list_available_expiries_for_symbol, scan_rr_for_expiry, format_for_telegram
from compute.options.expiry_menu import classify_expiries, combined_order


def _to_date(expiry_str: str):
    return dt.datetime.strptime(expiry_str, "%d-%b-%Y").date()


def pick_3w_2m(expiries: List[str]) -> List[str]:
    weekly, monthly = classify_expiries(expiries)
    selected = []

    for e in weekly[:3]:
        selected.append(e)

    for e in monthly[:2]:
        selected.append(e)

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
def detect_bnf_trend_advanced(oc_df, spot: float) -> tuple:
    score = 50

    strikes = sorted(oc_df["strike"].unique())
    atm = min(strikes, key=lambda s: abs(s - spot))
    nearby = oc_df[(oc_df["strike"] >= atm - 300) & (oc_df["strike"] <= atm + 300)]

    ce_oi = nearby["ce_oi"].sum() if "ce_oi" in oc_df else 0
    pe_oi = nearby["pe_oi"].sum() if "pe_oi" in oc_df else 0

    ce_chg = nearby["ce_change_oi"].sum() if "ce_change_oi" in oc_df else 0
    pe_chg = nearby["pe_change_oi"].sum() if "pe_change_oi" in oc_df else 0

    ce_vol = nearby["ce_volume"].sum() if "ce_volume" in oc_df else 0
    pe_vol = nearby["pe_volume"].sum() if "pe_volume" in oc_df else 0

    ce_iv = nearby["ce_iv"].mean() if "ce_iv" in oc_df else None
    pe_iv = nearby["pe_iv"].mean() if "pe_iv" in oc_df else None

    # Price trend
    if "prev_close" in oc_df.columns:
        prev = float(oc_df["prev_close"].iloc[0])
        move = ((spot - prev) / prev) * 100
        if move > 0.35:
            score += 8
        elif move < -0.35:
            score -= 8

    # ΔOI
    oi_diff = ce_chg - pe_chg
    if oi_diff > 0:
        score += 10
    elif oi_diff < 0:
        score -= 10

    # OI weight
    if ce_oi > pe_oi * 1.3:
        score += 6
    elif pe_oi > ce_oi * 1.3:
        score -= 6

    # Volume
    vol_diff = ce_vol - pe_vol
    if vol_diff > 0:
        score += 5
    elif vol_diff < 0:
        score -= 5

    # IV trend
    if ce_iv and pe_iv:
        if ce_iv > pe_iv + 1:
            score -= 4
        elif pe_iv > ce_iv + 1:
            score += 4

    score = max(0, min(100, score))

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
        return round(expected_move / premium, 2)
    except Exception:
        return 0.0


# -----------------------
# Suggestions
# -----------------------
def suggestions_from_picks(picks: Dict, spot: float) -> List[str]:
    out = []
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
        except:
            pass

    if best_ce:
        rr_ce = compute_rr_for_strike(spot, best_ce["strike"], best_ce.get("ltp", best_ce.get("lastPrice", 0)))
        out.append(f"🔥 CE R:R ~ {rr_ce}")

    if best_pe:
        rr_pe = compute_rr_for_strike(spot, best_pe["strike"], best_pe.get("ltp", best_pe.get("lastPrice", 0)))
        out.append(f"🐻 PE R:R ~ {rr_pe}")

    return out


# -----------------------
# Menu builder
# -----------------------
async def get_bnf_expiry_menu_and_state() -> Tuple[str, dict]:
    oc_df = fetch_banknifty_option_chain()
    if oc_df is None or oc_df.empty:
        raise RuntimeError("No BankNifty OC data")

    expiries = sorted(oc_df["expiry"].unique(), key=lambda x: dt.datetime.strptime(x, "%d-%b-%Y"))
    selected = pick_3w_2m(expiries)

    try:
        spot = float(oc_df["spot"].iloc[0])
    except:
        spot = np.nan

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
    if oc_df is None or oc_df.empty:
        raise RuntimeError("No BankNifty OC data")

    oc = oc_df[oc_df["expiry"] == expiry].copy()
    if oc.empty:
        oc = oc_df.copy()

    try:
        spot = float(oc_df["spot"].iloc[0])
    except:
        spot = np.nan

    picks = pick_best_ce_pe(oc, spot)

    trend_text, trend_score = detect_bnf_trend_advanced(oc_df, spot)

    if picks.get("best_ce"):
        picks["best_ce"]["rr"] = compute_rr_for_strike(spot, picks["best_ce"]["strike"], picks["best_ce"].get("ltp", 0))

    if picks.get("best_pe"):
        picks["best_pe"]["rr"] = compute_rr_for_strike(spot, picks["best_pe"]["strike"], picks["best_pe"].get("ltp", 0))

    sugg = suggestions_from_picks(picks, spot)

    lines = []
    lines.append(f"📈 BankNifty Option Analysis")
    lines.append(f"Expiry: {expiry}")
    lines.append(f"Spot: {spot:.2f}\n")
    lines.append(f"📊 Trend: {trend_text} ({trend_score}%)\n")

    ce = picks.get("best_ce")
    if ce:
        lines.append("🔥 BEST CE")
        lines.append(f"Strike: {ce['strike']}  Premium: {ce.get('ltp', '—')}  OI: {ce.get('oi', '—')}  ΔOI: {ce.get('change_oi', '—')}")
        lines.append(f"RR: {ce.get('rr', '—')}\n")

    pe = picks.get("best_pe")
    if pe:
        lines.append("🐻 BEST PE")
        lines.append(f"Strike: {pe['strike']}  Premium: {pe.get('ltp', '—')}  OI: {pe.get('oi', '—')}  ΔOI: {pe.get('change_oi', '—')}")
        lines.append(f"RR: {pe.get('rr', '—')}\n")

    if sugg:
        lines.append("💡 Suggestions:")
        for s in sugg:
            lines.append(f"• {s}")

    return "\n".join(lines)
