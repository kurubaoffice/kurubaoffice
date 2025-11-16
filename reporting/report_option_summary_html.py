# reporting/report_option_summary_html.py
from typing import Dict, Optional
import pandas as pd
import numpy as np
import re

# ---------- Helpers ----------
def _fmt(v, precision=2):
    if v is None:
        return "—"
    try:
        if isinstance(v, float):
            return f"{v:.{precision}f}"
        return str(int(v)) if float(v).is_integer() else str(v)
    except Exception:
        return str(v)

def _grade_score(score: float) -> str:
    if score is None or np.isnan(score):
        return "N/A"
    if score > 0.85:
        return "A 🔥"
    if score > 0.75:
        return "B 👍"
    if score > 0.60:
        return "C 🙂"
    return "D ⚠️"

def _force_df(x):
    """Return a DataFrame no matter what the input is."""
    if x is None:
        return pd.DataFrame()
    if isinstance(x, pd.DataFrame):
        return x.copy()
    if isinstance(x, pd.Series):
        return pd.DataFrame([x.to_dict()])
    if isinstance(x, dict):
        return pd.DataFrame([x])
    if isinstance(x, list):
        try:
            return pd.DataFrame(x)
        except Exception:
            return pd.DataFrame([{"bad_input": str(x)}])
    return pd.DataFrame([{"value": str(x)}])

def _get_opt_type_from_row(r: pd.Series) -> str:
    return (
        (r.get('optionType') if isinstance(r, dict) else None)
        or r.get('type') or r.get('option_type') or r.get('optionType_x') or '??'
    )

# ---------- Max Pain ----------
def max_pain(df, expiry=None):
    if df is None or df.empty:
        return {"max_pain_strike": None, "loss_map": {}}
    oc = df.copy()
    for c in ["strike", "oi", "type", "optionType"]:
        if c not in oc.columns:
            oc[c] = None
    spot = float(oc['spot'].iloc[0])
    oc['opt'] = oc['optionType'].fillna(oc.get('type')).fillna("NA")
    loss_map = {}
    for strike in sorted(oc['strike'].dropna().unique()):
        calls = oc[(oc['strike'] == strike) & (oc['opt'] == "CE")]
        puts  = oc[(oc['strike'] == strike) & (oc['opt'] == "PE")]
        call_loss = ((spot - strike).clip(lower=0)) * calls['oi'].sum()
        put_loss  = ((strike - spot).clip(lower=0)) * puts['oi'].sum()
        total_loss = float(call_loss + put_loss)
        loss_map[int(strike)] = total_loss
    if not loss_map:
        return {"max_pain_strike": None, "loss_map": {}}
    best_strike = min(loss_map, key=lambda s: loss_map[s])
    return {"max_pain_strike": int(best_strike), "loss_map": loss_map}

# ---------- Build Option Alert HTML ----------
def build_option_alert_html(
    picks: Dict,
    oc_df: pd.DataFrame,
    spot: float,
    bias_text: Optional[str] = None,
    previous_df: Optional[pd.DataFrame] = None,
    trend_text: Optional[str] = None,
    top_neighbors: int = 1
) -> str:

    # Defensive: ensure oc_df is DataFrame
    if not isinstance(oc_df, pd.DataFrame):
        try:
            oc_df = pd.DataFrame(oc_df)
        except Exception:
            return "⚠️ Error: Failed to parse option chain."

    # Picks into DataFrames
    ce_df = _force_df(picks.get("CE"))
    pe_df = _force_df(picks.get("PE"))
    picks = {"CE": ce_df, "PE": pe_df}

    # Ensure numeric columns
    for c in ['oi', 'change_oi', 'volume', 'iv', 'bid', 'ask', 'strike']:
        if c not in oc_df.columns:
            oc_df[c] = 0.0

    # Pick first rows
    r_ce = ce_df.iloc[0] if not ce_df.empty else None
    r_pe = pe_df.iloc[0] if not pe_df.empty else None

    # ATM strike
    try:
        atm = int(min(oc_df['strike'].unique(), key=lambda s: abs(s - spot)))
    except Exception:
        atm = None

    # Max pain
    try:
        mp = max_pain(oc_df)
        mp_strike = mp.get('max_pain_strike')
    except Exception:
        mp_strike = None

    # Build HTML
    lines = []
    lines.append("<b>📈 BankNifty Option Alert</b>")
    lines.append(f"Spot: <b>{_fmt(spot,2)}</b>")

    if bias_text:
        lines.append(f"<i>Bias:</i> {bias_text}")

    if trend_text:
        trend_summary = trend_text.strip().splitlines()[0]
        lines.append(f"<i>Trend:</i> {trend_summary}")

    lines.append("")

    # CE block
    lines.append("<b>🔥 BEST CE</b>")
    if r_ce is None:
        lines.append("No CE pick.")
    else:
        opt_type = _get_opt_type_from_row(r_ce)
        score = float(r_ce.get('score', 0.0))
        lines.append(f"Strike: <code>{int(r_ce['strike'])}</code> ({opt_type})")
        lines.append(f"Score: <b>{score:.3f}</b> ({_grade_score(score)})")
        lines.append(f"OI: <code>{_fmt(r_ce['oi'],0)}</code>  ΔOI: <code>{_fmt(r_ce.get('change_oi',0),0)}</code>  Vol: <code>{_fmt(r_ce['volume'],0)}</code>")
        ivv = float(r_ce.get('iv', 0.0))
        lines.append(f"IV: <code>{_fmt(ivv,2)}</code>")
        lines.append(f"Bid/Ask: <code>{_fmt(r_ce['bid'],2)} / {_fmt(r_ce['ask'],2)}</code>")

    lines.append("")

    # PE block
    lines.append("<b>🐻 BEST PE</b>")
    if r_pe is None:
        lines.append("No PE pick.")
    else:
        opt_type = _get_opt_type_from_row(r_pe)
        score = float(r_pe.get('score', 0.0))
        lines.append(f"Strike: <code>{int(r_pe['strike'])}</code> ({opt_type})")
        lines.append(f"Score: <b>{score:.3f}</b> ({_grade_score(score)})")
        lines.append(f"OI: <code>{_fmt(r_pe['oi'],0)}</code>  ΔOI: <code>{_fmt(r_pe.get('change_oi',0),0)}</code>  Vol: <code>{_fmt(r_pe['volume'],0)}</code>")
        ivv = float(r_pe.get('iv', 0.0))
        lines.append(f"IV: <code>{_fmt(ivv,2)}</code>")
        lines.append(f"Bid/Ask: <code>{_fmt(r_pe['bid'],2)} / {_fmt(r_pe['ask'],2)}</code>")

    lines.append("")

    # ATM neighbor context
    neighbor_table = []
    try:
        from compute.options.strike_selector import compute_strike_score
        if atm is not None:
            for side in ('CE', 'PE'):
                neighbors = []
                for i in range(-top_neighbors, top_neighbors + 1):
                    strike = atm + i * 100
                    sub = oc_df[(oc_df['strike']==strike) & ((oc_df.get('type')==side) | (oc_df.get('optionType')==side))]
                    if sub.empty:
                        continue
                    scored = compute_strike_score(sub, spot)
                    neighbors.append({'side': side, 'strike': strike, 'score': float(scored['score'].iloc[0]), 'oi': int(scored['oi'].iloc[0])})
                neighbor_table.append((side, neighbors))
    except Exception:
        pass

    if neighbor_table:
        lines.append("<b>🔎 ATM context (neighbor scores)</b>")
        for side, neighbors in neighbor_table:
            if not neighbors:
                continue
            bits = [f"{int(n['strike'])}: {n['score']:.3f} (OI:{n['oi']})" for n in neighbors]
            lines.append(f"<b>{side}</b>: " + " | ".join(bits))

    # Max pain
    if mp_strike is not None:
        lines.append("")
        lines.append(f"<b>⚖️ Max Pain:</b> <code>{mp_strike}</code>")

    # Footer / reason
    lines.append("")
    lines.append("<b>🧠 Reason</b>")
    lines.append("Selected by combined OI + ΔOI + Volume with liquidity penalty. ATM strikes favored.")
    lines.append("")

    return "\n".join(lines)
