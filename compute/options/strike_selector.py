# compute/options/strike_selector.py
import pandas as pd
import numpy as np
from typing import Dict, Any

# ---------- Defaults ----------
DEFAULT_WEIGHTS = {
    "w_oi": 0.30,
    "w_doi": 0.30,
    "w_vol": 0.20,
    "w_iv": 0.10,
    "w_dist": 0.06,
    "w_spread": 0.04,
}

# ---------- Helpers ----------
def _coerce_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize common column names and coerce numeric types safely."""
    df = df.copy()
    # normalize column names
    rename_map = {}
    for c in df.columns:
        lc = c.lower()
        if lc in ("instrument_type",):
            rename_map[c] = "optionType"
        if lc in ("changeinoopeninterest", "change_in_oi", "changeinopeninterest"):
            rename_map[c] = "change_oi"
        if lc == "lastprice":
            rename_map[c] = "lastPrice"
    if rename_map:
        df = df.rename(columns=rename_map)

    # ensure core columns exist
    for col in ["strike", "oi", "change_oi", "volume", "iv", "bid", "ask", "type", "optionType", "expiry", "spot"]:
        if col not in df.columns:
            df[col] = np.nan

    # unify option type into 'type' column for filtering (values: CE/PE)
    def _pick_type(row):
        for key in ("optionType", "type", "instrument_type"):
            if key in row and pd.notna(row.get(key)):
                return str(row.get(key)).upper()
        return np.nan

    if "type" not in df.columns or df["type"].isnull().all():
        df["type"] = df.apply(_pick_type, axis=1)

    # coerce numeric columns
    num_cols = ["strike", "oi", "change_oi", "volume", "iv", "bid", "ask", "lastPrice", "spot"]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

    return df

def _ensure_df(x):
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
            return pd.DataFrame([{"value": str(x)}])
    return pd.DataFrame([{"value": str(x)}])

def _normalize_series(s: pd.Series) -> pd.Series:
    if s.isnull().all():
        return pd.Series(0.0, index=s.index)
    mn, mx = s.min(), s.max()
    if pd.isna(mn) or pd.isna(mx) or mx == mn:
        return pd.Series(0.0, index=s.index)
    return (s - mn) / (mx - mn)

def _sigmoid(x):
    return 1 / (1 + np.exp(-x))

# ---------- Scoring ----------
def compute_base_scores(df: pd.DataFrame, spot: float, weights: Dict[str, float] = None) -> pd.DataFrame:
    """
    Compute normalized base score per option row using:
      - OI, |ΔOI|, Volume, IV, distance from spot, bid/ask spread
    """
    w = DEFAULT_WEIGHTS.copy()
    if weights:
        w.update(weights)

    df = df.copy()
    # safety numeric
    df = _coerce_cols(df)

    # spread and distance
    df["spread"] = (df["ask"] - df["bid"]).abs().fillna(0.0)
    df["dist_abs"] = (df["strike"] - spot).abs()

    # normalized factors
    df["n_oi"] = _normalize_series(df["oi"])
    df["n_doi"] = _normalize_series(df["change_oi"].abs())
    df["n_vol"] = _normalize_series(df["volume"])
    df["n_iv"] = _normalize_series(df["iv"])
    df["n_dist"] = _normalize_series(df["dist_abs"])
    df["n_spread"] = _normalize_series(df["spread"])

    df["base_score"] = (
        w["w_oi"] * df["n_oi"] +
        w["w_doi"] * df["n_doi"] +
        w["w_vol"] * df["n_vol"] +
        w["w_iv"] * df["n_iv"] -
        w["w_dist"] * df["n_dist"] -
        w["w_spread"] * df["n_spread"]
    )

    # ATM small bonus
    df.loc[df["dist_abs"] <= 100, "base_score"] += 0.05

    return df

# ---------- Liquidity penalty ----------
def apply_liquidity_penalty(df: pd.DataFrame) -> pd.DataFrame:
    """Apply stronger penalties for near-zero bid or very wide spreads."""
    df = df.copy()
    # if bid very small or zero, heavy penalty
    df["liq_penalty"] = 0.0
    # treat bid <= 0.1 as illiquid
    df.loc[df["bid"] <= 0.1, "liq_penalty"] += 0.4
    # moderate penalty if spread relative to lastPrice large
    df.loc[(df["lastPrice"] > 0) & ((df["spread"] / df["lastPrice"]) > 0.5), "liq_penalty"] += 0.2
    df["score_post_liq"] = (df["base_score"] - df["liq_penalty"]).clip(lower=0.0)
    return df

# ---------- IV skew & OI imbalance biases ----------
def compute_iv_pe_pair(df: pd.DataFrame) -> pd.DataFrame:
    """
    For each strike, compute CE IV and PE IV as columns ce_iv and pe_iv for biasing.
    Returns df with ce_iv/pe_iv merged on each row (NaN if missing).
    """
    # pivot ivs per strike
    ivs = df.pivot_table(index="strike", columns="type", values="iv", aggfunc="mean")
    ivs = ivs.rename(columns=lambda x: f"{x}_iv" if isinstance(x, str) else x)
    ivs = ivs.reset_index()
    return ivs  # columns like strike, CE_iv, PE_iv (or 'CE_iv' depending on data)

def _compute_oi_imbalance(option_chain_df: pd.DataFrame, atm: float, window_strikes: int = 3) -> float:
    """
    Compute CE - PE imbalance using change_oi (prefer) or oi across a window around atm.
    Positive => CE building more OI (bullish flow). Negative => PE building more OI (bearish).
    """
    df = option_chain_df.copy()
    df = _coerce_cols(df)
    half = window_strikes * 100
    subset = df[(df["strike"] >= (atm - half)) & (df["strike"] <= (atm + half))]
    if subset.empty:
        return 0.0
    if subset["change_oi"].abs().sum() > 0:
        ce_sum = subset[subset["type"].str.upper() == "CE"]["change_oi"].sum()
        pe_sum = subset[subset["type"].str.upper() == "PE"]["change_oi"].sum()
    else:
        ce_sum = subset[subset["type"].str.upper() == "CE"]["oi"].sum()
        pe_sum = subset[subset["type"].str.upper() == "PE"]["oi"].sum()
    return float(ce_sum - pe_sum)

def apply_biases(df: pd.DataFrame, iv_map: pd.DataFrame) -> pd.DataFrame:
    """
    Apply small additive biases to scores:
      - IV skew: if PE_iv >> CE_iv -> boost CE (calls relatively cheaper)
      - OI imbalance bias will be applied at higher level (not per-row here)
    """
    df = df.copy()
    # merge iv_map (CE_iv and PE_iv) onto df by strike
    if not iv_map.empty:
        ivmap = iv_map.copy()
        # rename to consistent names if present
        # ivmap columns might be like ('CE',) depending on pivot; handle generically
        # standard approach: attempt to extract CE_iv and PE_iv columns ignoring case
        ce_iv_col = next((c for c in ivmap.columns if str(c).upper().startswith("CE")), None)
        pe_iv_col = next((c for c in ivmap.columns if str(c).upper().startswith("PE")), None)
        # unify
        rename = {}
        if ce_iv_col and ce_iv_col != "CE_iv":
            rename[ce_iv_col] = "CE_iv"
        if pe_iv_col and pe_iv_col != "PE_iv":
            rename[pe_iv_col] = "PE_iv"
        if rename:
            ivmap = ivmap.rename(columns=rename)
        # ensure CE_iv/PE_iv exist
        if "CE_iv" in ivmap.columns or "PE_iv" in ivmap.columns:
            ivmap = ivmap.rename(columns={"strike": "strike"})
            df = df.merge(ivmap, on="strike", how="left")
            df["CE_iv"] = pd.to_numeric(df.get("CE_iv", np.nan), errors="coerce")
            df["PE_iv"] = pd.to_numeric(df.get("PE_iv", np.nan), errors="coerce")
            # iv bias: calls cheaper => boost CE, else boost PE
            # compute an iv_diff per row: (PE_iv - CE_iv)
            df["iv_diff"] = df["PE_iv"].fillna(0.0) - df["CE_iv"].fillna(0.0)
            df["iv_bias"] = _sigmoid(df["iv_diff"].fillna(0.0)) * 0.05
            # Apply bias: for CE rows add iv_bias, for PE rows add (-iv_bias) because sign reversed in iv_diff convention
            df.loc[df["type"].str.upper() == "CE", "score_post_liq"] += df.loc[df["type"].str.upper() == "CE", "iv_bias"]
            df.loc[df["type"].str.upper() == "PE", "score_post_liq"] += (-df.loc[df["type"].str.upper() == "PE", "iv_bias"])
    return df

# ---------- Pick top strikes with optional bias shifting ----------
def _find_neighbor(df: pd.DataFrame, strike_base: int, side: str, shift_dir: int, spot: float, weights=None, max_steps=5):
    """Search neighbor strikes by shift_dir (+1 higher strike, -1 lower strike)."""
    strikes = sorted(df["strike"].unique())
    if strike_base not in strikes:
        # try closest strike
        try:
            strike_base = min(strikes, key=lambda s: abs(s - strike_base))
        except Exception:
            return None
    idx = strikes.index(strike_base)
    step_val = 100
    for n in range(1, max_steps + 1):
        cand_strike = strike_base + shift_dir * n * step_val
        sub = df[(df["strike"] == cand_strike) & (df["type"].str.upper() == side)]
        if not sub.empty:
            scored = compute_base_scores(sub, spot, weights=weights)
            scored = apply_liquidity_penalty(scored)
            # apply iv map empty placeholder (no map available here)
            scored = scored.sort_values("score_post_liq", ascending=False)
            return _ensure_df(scored.head(1))
    return None

def top_strikes(df: pd.DataFrame, spot: float, top_n=3, option_type='CE', expiry=None, weights=None):
    """Return top_n strikes for a given option side using base scoring & liquidity penalty."""
    if expiry is not None:
        df = df[df["expiry"] == expiry].copy()
    df = _coerce_cols(df)
    side_df = df[df["type"].str.upper() == option_type].copy()
    if side_df.empty:
        return side_df
    scored = compute_base_scores(side_df, spot, weights=weights)
    scored = apply_liquidity_penalty(scored)
    # produce iv map for bias merging
    iv_map = compute_iv_pe_pair(df)
    scored = apply_biases(scored, iv_map)
    scored = scored.sort_values("score_post_liq", ascending=False)
    return scored.head(top_n)

# ---------- Final selection routine ----------
def pick_best_ce_pe(option_chain_df: pd.DataFrame, spot: float, expiry=None, top_n=1, weights=None, shift_steps: int = 1) -> Dict[str, pd.DataFrame]:
    """
    Returns a dict {'CE': DataFrame(1-row), 'PE': DataFrame(1-row)} with best picks.
    Applies OI imbalance bias and a hard-shift safety rule to avoid identical strikes.
    """
    if option_chain_df is None:
        return {"CE": pd.DataFrame(), "PE": pd.DataFrame()}

    df = option_chain_df.copy()
    df = _coerce_cols(df)

    if expiry is not None:
        df = df[df["expiry"] == expiry].copy()

    # safe spot fallback
    try:
        atm = int(min(df["strike"].unique(), key=lambda s: abs(s - spot)))
    except Exception:
        atm = int(round(spot / 100) * 100)

    # base candidates
    ce_base = top_strikes(df, spot, top_n=top_n, option_type="CE", expiry=expiry, weights=weights)
    pe_base = top_strikes(df, spot, top_n=top_n, option_type="PE", expiry=expiry, weights=weights)

    ce_df = _ensure_df(ce_base)
    pe_df = _ensure_df(pe_base)

    # compute OI imbalance
    oi_imb = _compute_oi_imbalance(df, atm, window_strikes=3)

    # dynamic threshold: scale to total OI in window
    total_oi_window = df[(df["strike"] >= atm - 300) & (df["strike"] <= atm + 300)]["oi"].sum()
    threshold = max(200.0, 0.005 * max(1.0, total_oi_window))  # lower sensitivity compared to previous

    bias = 0
    if oi_imb > threshold:
        bias = 1
    elif oi_imb < -threshold:
        bias = -1

    # Try directional shift if bias present
    if bias != 0:
        # compute base strike ints
        try:
            ce_base_strike = int(ce_df.iloc[0]["strike"])
        except Exception:
            ce_base_strike = atm
        try:
            pe_base_strike = int(pe_df.iloc[0]["strike"])
        except Exception:
            pe_base_strike = atm

        step = shift_steps * 100
        if bias == 1:
            # CE building (bullish): CE -> OTM (+), PE -> ITM (-)
            alt_ce = _find_neighbor(df, ce_base_strike, "CE", shift_dir=+1, spot=spot, weights=weights)
            alt_pe = _find_neighbor(df, pe_base_strike, "PE", shift_dir=-1, spot=spot, weights=weights)
        else:
            # PE building (bearish): PE -> OTM (+), CE -> ITM (-)
            alt_ce = _find_neighbor(df, ce_base_strike, "CE", shift_dir=-1, spot=spot, weights=weights)
            alt_pe = _find_neighbor(df, pe_base_strike, "PE", shift_dir=+1, spot=spot, weights=weights)

        if alt_ce is not None and not alt_ce.empty:
            ce_df = alt_ce
        if alt_pe is not None and not alt_pe.empty:
            pe_df = alt_pe

    # normalize name
    if "type" in ce_df.columns and "optionType" not in ce_df.columns:
        ce_df = ce_df.rename(columns={"type": "optionType"})
    if "type" in pe_df.columns and "optionType" not in pe_df.columns:
        pe_df = pe_df.rename(columns={"type": "optionType"})

    # HARD SHIFT SAFETY: if both same strike, force PE -> neighbor (prefer ITM) then CE -> neighbor
    try:
        if not ce_df.empty and not pe_df.empty:
            if int(ce_df.iloc[0]["strike"]) == int(pe_df.iloc[0]["strike"]):
                strikes = sorted(df["strike"].unique())
                base_strike = int(ce_df.iloc[0]["strike"])
                if base_strike in strikes:
                    idx = strikes.index(base_strike)
                    shifted = None
                    # prefer shifting PE down (ITM)
                    if idx - 1 >= 0:
                        alt = df[(df["strike"] == strikes[idx - 1]) & (df["type"].str.upper() == "PE")]
                        if not alt.empty:
                            shifted = alt
                    # else try PE up
                    if shifted is None and idx + 1 < len(strikes):
                        alt = df[(df["strike"] == strikes[idx + 1]) & (df["type"].str.upper() == "PE")]
                        if not alt.empty:
                            shifted = alt
                    if shifted is not None and not shifted.empty:
                        pe_df = _ensure_df(_coerce_cols(shifted))
                    else:
                        # fallback shift CE up
                        shifted = None
                        if idx + 1 < len(strikes):
                            alt = df[(df["strike"] == strikes[idx + 1]) & (df["type"].str.upper() == "CE")]
                            if not alt.empty:
                                shifted = alt
                        if shifted is None and idx - 1 >= 0:
                            alt = df[(df["strike"] == strikes[idx - 1]) & (df["type"].str.upper() == "CE")]
                            if not alt.empty:
                                shifted = alt
                        if shifted is not None and not shifted.empty:
                            ce_df = _ensure_df(_coerce_cols(shifted))
    except Exception as e:
        print("DEBUG: hard-shift safety error:", e)

    return {"CE": _ensure_df(ce_df), "PE": _ensure_df(pe_df)}
