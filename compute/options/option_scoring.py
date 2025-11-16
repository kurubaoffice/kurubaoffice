import pandas as pd
import numpy as np


# -----------------------------------------
# Utility: Safe formatter
# -----------------------------------------
def _fmt(x, digits=2):
    """Safe number formatter used across alerts."""
    if x is None or pd.isna(x):
        return "-"
    try:
        return f"{float(x):.{digits}f}"
    except:
        return str(x)


# -----------------------------------------
# Utility: Ensure DataFrame
# -----------------------------------------
def _force_df(df):
    """Ensures df is a DataFrame and drops duplicates."""
    if df is None:
        return pd.DataFrame()
    if not isinstance(df, pd.DataFrame):
        df = pd.DataFrame(df)
    return df.drop_duplicates().reset_index(drop=True)


# -----------------------------------------
# BASE SCORE LOGIC
# -----------------------------------------
def _compute_base_score(df, atm_strike):
    """
    Computes normalised score based on:
    OI, Change OI, Volume and ATM proximity.
    """
    if df.empty:
        df["base_score"] = 0
        return df

    df["oi_norm"] = df["oi"] / (df["oi"].max() + 1e-6)
    df["coi_norm"] = df["change_oi"] / (df["change_oi"].abs().max() + 1e-6)
    df["vol_norm"] = df["volume"] / (df["volume"].max() + 1e-6)

    # ATM PROXIMITY BOOST
    df["atm_boost"] = 1 - (abs(df["strike"] - atm_strike) / atm_strike)

    df["base_score"] = (
        df["oi_norm"] * 0.45 +
        df["coi_norm"] * 0.30 +
        df["vol_norm"] * 0.20 +
        df["atm_boost"] * 0.05
    )

    return df


# -----------------------------------------
# LIQUIDITY PENALTY
# -----------------------------------------
def _apply_liquidity_penalty(df):
    """
    Applies a bid-ask spread penalty.
    Wider spreads → lower score.
    """
    if df.empty:
        df["liq_penalty"] = 0
        df["score_post_liq"] = 0
        return df

    df["bid"] = df["bid"].fillna(0)
    df["ask"] = df["ask"].fillna(0)

    df["spread"] = (df["ask"] - df["bid"]).clip(lower=0)

    # Normalise
    max_spread = df["spread"].max() + 1e-6
    df["spread_norm"] = df["spread"] / max_spread

    # Higher spread → more penalty
    df["liq_penalty"] = df["spread_norm"] * 0.30

    df["score_post_liq"] = df["base_score"] - df["liq_penalty"]
    df["score_post_liq"] = df["score_post_liq"].clip(lower=0)

    return df


# -----------------------------------------
# MAIN SCORING PIPELINE
# -----------------------------------------
def score_option_chain(df, spot):
    """
    Full pipeline:
    - ensure df
    - compute ATM strike
    - base score
    - liquidity penalty
    - final score
    """
    df = _force_df(df)
    if df.empty:
        return df

    # ATM strike rounding
    atm_strike = round(spot / 100) * 100

    df = _compute_base_score(df, atm_strike)
    df = _apply_liquidity_penalty(df)

    return df


# -----------------------------------------
# PICK BEST CE/PE
# -----------------------------------------
def select_best_ce_pe(df_ce, df_pe):
    """
    Selects highest scoring CE and PE after liquidity penalty.
    """
    df_ce = df_ce.sort_values("score_post_liq", ascending=False).reset_index(drop=True)
    df_pe = df_pe.sort_values("score_post_liq", ascending=False).reset_index(drop=True)

    best_ce = df_ce.iloc[0] if not df_ce.empty else None
    best_pe = df_pe.iloc[0] if not df_pe.empty else None

    return best_ce, best_pe


# -----------------------------------------
# FORMAT OUTPUT MESSAGE
# -----------------------------------------
def format_option_alert(spot, best_ce, best_pe):
    """
    Creates final formatted Telegram message.
    """

    def fmt_side(row):
        if row is None:
            return "⚠️ No liquid strikes found"

        return (
            f"Strike: {int(row['strike'])} ({row['type']})\n"
            f"Score: {_fmt(row['score_post_liq'], 3)}\n"
            f"OI: {_fmt(row['oi'], 0)}   ΔOI: {_fmt(row['change_oi'], 0)}   Vol: {_fmt(row['volume'], 0)}\n"
            f"IV: {_fmt(row.get('iv'), 2)}\n"
            f"Bid/Ask: {_fmt(row['bid'], 2)} / {_fmt(row['ask'], 2)}"
        )

    msg = (
        f"📘 **BankNifty Option Alert**\n"
        f"Spot: {spot}\n\n"

        f"🔥 **BEST CE**\n"
        f"{fmt_side(best_ce)}\n\n"

        f"🐻 **BEST PE**\n"
        f"{fmt_side(best_pe)}\n\n"

        f"🧠 *Reason*\n"
        f"Selected using OI + ΔOI + Volume with bid-ask liquidity penalty. "
        f"ATM strikes get priority.\n"
    )

    return msg
