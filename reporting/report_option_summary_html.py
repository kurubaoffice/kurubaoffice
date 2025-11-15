# reporting/report_option_summary_html.py
from typing import Dict, Optional
import pandas as pd
import numpy as np

# reuse max_pain if you created analysis/option_chain_analysis.py
def max_pain(df, expiry=None):
    """
    Compute Max Pain strike.

    Logic:
    - For each strike X:
        - For calls: loss = max(0, spot - X) * OI_call
        - For puts:  loss = max(0, X - spot) * OI_put
    - Strike with minimum total loss = Max Pain

    This works without reliance on any external module.
    """
    if df is None or df.empty:
        return {"max_pain_strike": None, "loss_map": {}}

    # Make shallow copy to avoid mutation
    oc = df.copy()

    # Safety: ensure columns exist
    for c in ["strike", "oi", "type", "optionType"]:
        if c not in oc.columns:
            oc[c] = None

    spot = float(oc['spot'].iloc[0])

    # Normalize option type column
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

    # strike that minimizes total loss
    best_strike = min(loss_map, key=lambda s: loss_map[s])

    return {
        "max_pain_strike": int(best_strike),
        "loss_map": loss_map
    }



def _get_opt_type_from_row(r: pd.Series) -> str:
    return (
        (r.get('optionType') if isinstance(r, dict) else None)
        or r.get('type') or r.get('option_type') or r.get('optionType_x') or '??'
    )


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


def _fmt(v, precision=2):
    if v is None:
        return "—"
    try:
        if isinstance(v, float):
            return f"{v:.{precision}f}"
        return str(int(v)) if float(v).is_integer() else str(v)
    except Exception:
        return str(v)


def build_option_alert_html(
    picks: Dict,
    oc_df: pd.DataFrame,
    spot: float,
    previous_df: Optional[pd.DataFrame] = None,
    trend_text: Optional[str] = None,
    top_neighbors: int = 1
) -> str:
    """
    Build an HTML formatted Telegram message with extra analytics:
    - Trend text (optional)
    - ATM +/- neighbor scores
    - IV premium / comparison
    - MaxPain
    - Grades and HTML formatting
    """

    # defensive: ensure oc_df numeric columns exist
    # ==== HARD DEFENSIVE BLOCK (fix dict leak) ====

    # If oc_df is not a DataFrame, try to convert it.
    if not isinstance(oc_df, pd.DataFrame):
        print("DEBUG WARNING: oc_df arrived as", type(oc_df))
        try:
            oc_df = pd.DataFrame(oc_df)
            print("DEBUG: oc_df converted to DataFrame; cols:", list(oc_df.columns))
        except Exception as e:
            print("DEBUG FATAL: Cannot convert oc_df:", e)
            return "⚠️ Error: Failed to parse option chain (oc_df invalid)."

    # Coerce picks → always DataFrames
    def _force_df(x):
        if isinstance(x, pd.DataFrame):
            return x
        if isinstance(x, pd.Series):
            return pd.DataFrame([x.to_dict()])
        if isinstance(x, dict):
            return pd.DataFrame([x])
        if isinstance(x, list):
            try:
                return pd.DataFrame(x)
            except Exception:
                return pd.DataFrame([{"bad_input": str(x)}])
        return pd.DataFrame()

    if isinstance(picks, dict):
        ce_df = _force_df(picks.get("CE"))
        pe_df = _force_df(picks.get("PE"))
    else:
        print("DEBUG WARNING: picks is not a dict:", type(picks))
        ce_df = pd.DataFrame()
        pe_df = pd.DataFrame()

    # Replace picks safely
    picks = {"CE": ce_df, "PE": pe_df}

    # Debug logs showing exactly what reporter received
    try:
        print("\n===== DEBUG OPTION REPORT =====")
        print("oc_df:", type(oc_df), "cols:", list(oc_df.columns))
        print("CE pick:", type(ce_df), "cols:", list(ce_df.columns))
        if not ce_df.empty:
            print("CE row:", ce_df.iloc[0].to_dict())
        print("PE pick:", type(pe_df), "cols:", list(pe_df.columns))
        if not pe_df.empty:
            print("PE row:", pe_df.iloc[0].to_dict())
        print("================================\n")
    except Exception as e:
        print("DEBUG LOGGING ERROR:", e)

    # ==== END HARD DEFENSIVE BLOCK ====

    for c in ['oi', 'change_oi', 'volume', 'iv', 'bid', 'ask', 'strike']:
        if c not in oc_df.columns:
            oc_df[c] = 0.0

    # picks may be dataframes
    ce_df = picks.get('CE')
    pe_df = picks.get('PE')

    # get selected rows (first row)
    def pick_row(df):
        if df is None or getattr(df, "empty", True):
            return None
        return df.iloc[0]

    r_ce = pick_row(ce_df)
    r_pe = pick_row(pe_df)

    # ATM strike: prefer the strike closest to spot
    try:
        atm = int(min(oc_df['strike'].unique(), key=lambda s: abs(s - spot)))
    except Exception:
        atm = None

    # compute neighbor scores using strike selector if available
    neighbor_table = []
    try:
        from compute.options.strike_selector import compute_strike_score
        if atm is not None:
            for side in ('CE', 'PE'):
                neighbors = []
                for i in range(-top_neighbors, top_neighbors + 1):
                    strike = atm + i * 100
                    sub = oc_df[(oc_df['strike'] == strike) & ((oc_df.get('type') == side) | (oc_df.get('optionType') == side))]
                    if sub.empty:
                        continue
                    scored = compute_strike_score(sub, spot)
                    neighbors.append({
                        'side': side,
                        'strike': strike,
                        'score': float(scored['score'].iloc[0]) if 'score' in scored else 0.0,
                        'oi': int(scored['oi'].iloc[0])
                    })
                neighbor_table.append((side, neighbors))
    except Exception:
        # silently ignore if compute_strike_score not available
        pass

    # IV analytics
    iv_mean = oc_df['iv'].replace(0, np.nan).dropna()
    iv_mean_val = float(iv_mean.mean()) if not iv_mean.empty else None

    def iv_premium(iv_val):
        if iv_mean_val is None or iv_val is None or iv_mean_val == 0:
            return None
        return (iv_val - iv_mean_val) / iv_mean_val * 100.0

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

    if trend_text:
        # include first meaningful line of trend_text
        trend_summary = trend_text.strip().splitlines()[0]
        lines.append(f"<i>Trend:</i> {trend_summary}")

    lines.append("")  # blank line

    # CE block
    lines.append("<b>🔥 BEST CE</b>")
    if r_ce is None:
        lines.append("No CE pick.")
    else:
        opt_type = _get_opt_type_from_row(r_ce)
        score = float(r_ce.get('score', 0.0)) if isinstance(r_ce, (dict, pd.Series)) else 0.0
        lines.append(f"Strike: <code>{int(r_ce['strike'])}</code> ({opt_type})")
        lines.append(f"Score: <b>{score:.3f}</b> ({_grade_score(score)})")
        lines.append(f"OI: <code>{_fmt(r_ce['oi'],0)}</code>  ΔOI: <code>{_fmt(r_ce.get('change_oi', r_ce.get('change_in_oi',0)),0)}</code>  Vol: <code>{_fmt(r_ce['volume'],0)}</code>")
        ivv = float(r_ce.get('iv', 0.0))
        ip = iv_premium(ivv)
        if ip is not None:
            lines.append(f"IV: <code>{_fmt(ivv,2)}</code>  (<i>{_fmt(ip,2)}%</i> vs strike mean)")
        else:
            lines.append(f"IV: <code>{_fmt(ivv,2)}</code>")
        lines.append(f"Bid/Ask: <code>{_fmt(r_ce['bid'],2)} / {_fmt(r_ce['ask'],2)}</code>")

    lines.append("")  # blank

    # PE block
    lines.append("<b>🐻 BEST PE</b>")
    if r_pe is None:
        lines.append("No PE pick.")
    else:
        opt_type = _get_opt_type_from_row(r_pe)
        score = float(r_pe.get('score', 0.0)) if isinstance(r_pe, (dict, pd.Series)) else 0.0
        lines.append(f"Strike: <code>{int(r_pe['strike'])}</code> ({opt_type})")
        lines.append(f"Score: <b>{score:.3f}</b> ({_grade_score(score)})")
        lines.append(f"OI: <code>{_fmt(r_pe['oi'],0)}</code>  ΔOI: <code>{_fmt(r_pe.get('change_oi', r_pe.get('change_in_oi',0)),0)}</code>  Vol: <code>{_fmt(r_pe['volume'],0)}</code>")
        ivv = float(r_pe.get('iv', 0.0))
        ip = iv_premium(ivv)
        if ip is not None:
            lines.append(f"IV: <code>{_fmt(ivv,2)}</code>  (<i>{_fmt(ip,2)}%</i> vs strike mean)")
        else:
            lines.append(f"IV: <code>{_fmt(ivv,2)}</code>")
        lines.append(f"Bid/Ask: <code>{_fmt(r_pe['bid'],2)} / {_fmt(r_pe['ask'],2)}</code>")

    lines.append("")  # blank

    # ATM neighbor comparison
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

    # Short footer / reason
    lines.append("")
    lines.append("<b>🧠 Reason</b>")
    lines.append("Selected by combined OI + ΔOI + Volume with liquidity penalty. ATM strikes favored.")
    lines.append("")  # blank

    return "\n".join(lines)
