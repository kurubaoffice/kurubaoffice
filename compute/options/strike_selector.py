# compute/options/strike_selector.py
import pandas as pd
import numpy as np


DEFAULT_WEIGHTS = {
    "w_oi": 0.30,
    "w_doi": 0.30,
    "w_vol": 0.20,
    "w_iv": 0.10,
    "w_dist": 0.06,
    "w_spread": 0.04,
}


# ----------------------------------------------------
# Helpers
# ----------------------------------------------------
def normalize_series(s: pd.Series) -> pd.Series:
    if s.isnull().all():
        return s.fillna(0.0)
    mn, mx = s.min(), s.max()
    if pd.isna(mn) or pd.isna(mx) or mx == mn:
        return pd.Series(0.0, index=s.index)
    return (s - mn) / (mx - mn)


def sigmoid(x):
    return 1 / (1 + np.exp(-x))


# ----------------------------------------------------
# Base Score (your original method)
# ----------------------------------------------------
def compute_strike_score(df: pd.DataFrame, spot: float, weights: dict = None) -> pd.DataFrame:
    w = DEFAULT_WEIGHTS.copy()
    if weights:
        w.update(weights)

    df = df.copy()

    # safety fill
    for c in ['oi', 'change_oi', 'volume', 'iv', 'bid', 'ask']:
        if c not in df.columns:
            df[c] = 0.0

    df['spread'] = (df['ask'] - df['bid']).abs().fillna(0.0)
    df['dist_abs'] = (df['strike'] - spot).abs()

    df['n_oi']    = normalize_series(df['oi'])
    df['n_doi']   = normalize_series(df['change_oi'].abs())
    df['n_vol']   = normalize_series(df['volume'])
    df['n_iv']    = normalize_series(df['iv'])
    df['n_dist']  = normalize_series(df['dist_abs'])
    df['n_spread']= normalize_series(df['spread'])

    # Base weighted score
    df['score'] = (
        w['w_oi'] * df['n_oi'] +
        w['w_doi'] * df['n_doi'] +
        w['w_vol'] * df['n_vol'] +
        w['w_iv'] * df['n_iv'] -
        w['w_dist'] * df['n_dist'] -
        w['w_spread'] * df['n_spread']
    )

    # ATM bonus
    df.loc[df['dist_abs'] <= 100, 'score'] += 0.05

    return df


# ----------------------------------------------------
# Add optional advanced CE/PE correction
# ----------------------------------------------------
def apply_advanced_biasing(df: pd.DataFrame, option_type: str) -> pd.DataFrame:
    df = df.copy()

    # IV skew (CE-IV vs PE-IV)
    if 'iv' in df.columns and 'pe_iv' in df.columns:
        if option_type == 'CE':
            df['score'] += 0.05 * sigmoid(df['pe_iv'] - df['iv'])
        else:
            df['score'] += 0.05 * sigmoid(df['iv'] - df['pe_iv'])

    # OI imbalance bias
    if 'change_oi' in df.columns and 'pe_change_oi' in df.columns:
        if option_type == 'CE':
            df['score'] += 0.05 * sigmoid(df['change_oi'] - df['pe_change_oi'])
        else:
            df['score'] += 0.05 * sigmoid(df['pe_change_oi'] - df['change_oi'])

    return df


# ----------------------------------------------------
# Generic top strikes selector
# ----------------------------------------------------
def top_strikes(df: pd.DataFrame, spot: float, top_n=3, option_type='CE', expiry=None, weights=None):
    if expiry is not None:
        df = df[df['expiry'] == expiry].copy()

    side = df[df['type'].str.upper() == option_type].copy()
    if side.empty:
        return side

    # base scoring
    scored = compute_strike_score(side, spot, weights=weights)

    # optional advanced adjustments
    scored = apply_advanced_biasing(scored, option_type)

    scored = scored.sort_values('score', ascending=False)
    return scored.head(top_n)


# ----------------------------------------------------
# Safety function for dict/list inputs
# ----------------------------------------------------
def _ensure_df(x):
    if x is None:
        return pd.DataFrame()
    if isinstance(x, pd.DataFrame):
        return x
    if isinstance(x, pd.Series):
        return pd.DataFrame([x.to_dict()])
    if isinstance(x, dict):
        return pd.DataFrame([x])
    if isinstance(x, list):
        try:
            return pd.DataFrame(x)
        except:
            return pd.DataFrame([{"value": str(x)}])
    return pd.DataFrame([{"value": str(x)}])


# ----------------------------------------------------
# FINAL: pick best CE & PE (NEVER same strike)
# ----------------------------------------------------
def pick_best_ce_pe(option_chain_df: pd.DataFrame, spot: float, expiry=None, top_n=1, weights=None):
    ce = top_strikes(option_chain_df, spot, top_n=top_n, option_type='CE', expiry=expiry, weights=weights)
    pe = top_strikes(option_chain_df, spot, top_n=top_n, option_type='PE', expiry=expiry, weights=weights)

    ce_df = _ensure_df(ce)
    pe_df = _ensure_df(pe)

    # Normalize "type"
    if 'type' in ce_df.columns and 'optionType' not in ce_df.columns:
        ce_df = ce_df.rename(columns={'type': 'optionType'})
    if 'type' in pe_df.columns and 'optionType' not in pe_df.columns:
        pe_df = pe_df.rename(columns={'type': 'optionType'})

    # --------------------------------------------------------
    # IMPORTANT: Prevent CE and PE from using the same strike
    # --------------------------------------------------------
    if not ce_df.empty and not pe_df.empty:
        if ce_df.iloc[0]["strike"] == pe_df.iloc[0]["strike"]:
            # Replace PE with next best NON-matching strike
            pe_sorted = pe.sort_values("score", ascending=False)
            for _, row in pe_sorted.iterrows():
                if row["strike"] != ce_df.iloc[0]["strike"]:
                    pe_df = _ensure_df(row)
                    break

    return {'CE': ce_df, 'PE': pe_df}
