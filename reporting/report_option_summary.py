# reporting/report_option_summary.py
from typing import Dict


def build_option_alert_message(picks: Dict, spot: float):
    ce_df = picks.get('CE')
    pe_df = picks.get('PE')
    lines = [f"BankNifty Option Alert — Spot: {spot:.2f}\n"]

    def row_text(df):
        if df is None or df.empty:
            return "No data\n"

        r = df.iloc[0]

        # Safe fallback keys
        opt_type = (
                r.get("optionType")
                or r.get("type")
                or r.get("option_type")
                or r.get("option_type_x")
                or "?"
        )

        return (
            f"Strike {int(r['strike'])} ({opt_type}) — Score: {r['score']:.3f}\n"
            f" OI: {int(r['oi'])}, ΔOI: {int(r['change_oi'])}, Vol: {int(r['volume'])}, IV: {r['iv']:.2f}\n"
            f" Bid/Ask: {r['bid']:.2f}/{r['ask']:.2f}\n"
        )

    lines.append("BEST CE:\n")
    lines.append(row_text(ce_df))

    lines.append("BEST PE:\n")
    lines.append(row_text(pe_df))

    # simple reasoning
    lines.append(
        "Reason: Selected by combined OI + ΔOI + Volume with liquidity penalty. ATM strikes favored.\n"
    )

    return "\n".join(lines)
