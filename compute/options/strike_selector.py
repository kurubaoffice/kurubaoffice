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
    """Normalize common column names and coerce numeric types safely.
    IMPORTANT: do NOT fill missing numeric columns with zeros (keep NaN)."""
    df = df.copy()

    # normalize some column names
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

    # ensure core columns exist (as NaN / None)
    REQUIRED_NUM = ["strike", "oi", "change_oi", "volume", "iv", "bid", "ask", "lastPrice", "spot"]
    REQUIRED_STR = ["type", "optionType", "expiry"]
    for col in REQUIRED_NUM:
        if col not in df.columns:
            df[col] = np.nan
    for col in REQUIRED_STR:
        if col not in df.columns:
            df[col] = None

    # unify option type into 'type' column for filtering (values: CE/PE)
    def _pick_type(row):
        for key in ("optionType", "type", "instrument_type"):
            if key in row and pd.notna(row.get(key)):
                return str(row.get(key)).upper()
        return np.nan

    if "type" not in df.columns or df["type"].isnull().all():
        df["type"] = df.apply(_pick_type, axis=1)

    # coerce numeric columns to numeric but keep NaN (do NOT fillna(0.0))
    num_cols = ["strike", "oi", "change_oi", "volume", "iv", "bid", "ask", "lastPrice", "spot"]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

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

def _sigmoid(x):
    return 1 / (1 + np.exp(-x))

# synthesize bids only when bid missing/zero and ask/lastPrice available
def _synthesize_bids(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "bid" not in df.columns:
        return df
    # mask rows missing both bid and ask -> will be filtered earlier
    # For rows where bid is NaN or <= 0, but ask>0 or lastPrice>0, create conservative bid
    mask_bad_bid = (df["bid"].isna()) | (df["bid"] <= 0.0)
    if mask_bad_bid.any():
        # prefer conservative fraction of ask if present
        use_ask = mask_bad_bid & (df["ask"].notna()) & (df["ask"] > 0)
        df.loc[use_ask, "bid"] = df.loc[use_ask, "ask"] * 0.85
        # fallback to midpoint of ask & lastPrice if both present
        use_mid = mask_bad_bid & (df["ask"].notna()) & (df["lastPrice"].notna()) & (df["ask"] > 0) & (df["lastPrice"] > 0)
        df.loc[use_mid, "bid"] = (df.loc[use_mid, "ask"] + df.loc[use_mid, "lastPrice"]) / 2.0
        # final fallback tiny epsilon to avoid strict zero if nothing else
        still_bad = mask_bad_bid & (df["bid"].isna() | (df["bid"] <= 0.0))
        if still_bad.any():
            df.loc[still_bad, "bid"] = 0.01
    return df

# ---------- Scoring ----------
def _normalize_series(s: pd.Series) -> pd.Series:
    """Normalize series to 0..1. If series constant -> 0.5. NaN-handling: if all NaN -> zeros."""
    if s is None:
        return pd.Series(dtype=float)
    if s.isnull().all():
        return pd.Series(0.0, index=s.index)
    mn, mx = s.min(), s.max()
    if pd.isna(mn) or pd.isna(mx):
        return pd.Series(0.0, index=s.index)
    if mx == mn:
        return pd.Series(0.5, index=s.index)
    return (s - mn) / (mx - mn)

def compute_base_scores(df: pd.DataFrame, spot: float, weights: Dict[str, float] = None) -> pd.DataFrame:
    """Compute normalized base score per option row."""
    w = DEFAULT_WEIGHTS.copy()
    if weights:
        w.update(weights)

    df = df.copy()
    df = _coerce_cols(df)

    # Drop rows with absolutely no price info (both bid and ask missing or zero)
    df = df[~((df["bid"].isna() | (df["bid"] <= 0)) & (df["ask"].isna() | (df["ask"] <= 0)))]
    if df.empty:
        return df

    # synthesize conservative bids if required (but only after we filtered totally empty rows)
    df = _synthesize_bids(df)

    # compute spread and distance
    df["spread"] = (df["ask"] - df["bid"]).abs()
    df["dist_abs"] = (df["strike"] - spot).abs()

    # normalized factors (NaNs handled inside _normalize_series)
    df["n_oi"] = _normalize_series(df["oi"].fillna(0.0))
    df["n_doi"] = _normalize_series(df["change_oi"].abs().fillna(0.0))
    df["n_vol"] = _normalize_series(df["volume"].fillna(0.0))
    df["n_iv"] = _normalize_series(df["iv"].fillna(0.0))
    df["n_dist"] = _normalize_series(df["dist_abs"].fillna(0.0))
    df["n_spread"] = _normalize_series(df["spread"].fillna(0.0))

    df["base_score"] = (
        w["w_oi"] * df["n_oi"] +
        w["w_doi"] * df["n_doi"] +
        w["w_vol"] * df["n_vol"] +
        w["w_iv"] * df["n_iv"] -
        w["w_dist"] * df["n_dist"] -
        w["w_spread"] * df["n_spread"]
    )

    # ATM bonus
    df.loc[df["dist_abs"] <= 100, "base_score"] += 0.05

    # tiny floor so later clipping doesn't remove all signal
    df["base_score"] = df["base_score"].fillna(0.0) + 0.01

    return df

# ---------- Liquidity penalty ----------
def apply_liquidity_penalty(df: pd.DataFrame) -> pd.DataFrame:
    """Apply reasonable liquidity penalties. Uses synthesized bids if present."""
    df = df.copy()
    if df.empty:
        return df
    if "spread" not in df.columns:
        df["spread"] = (df.get("ask", 0.0) - df.get("bid", 0.0)).abs().fillna(0.0)
    if "lastPrice" not in df.columns:
        df["lastPrice"] = df.get("lastPrice", 0.0)

    df["liq_penalty"] = 0.0
    # penalty for very small bids
    df.loc[df["bid"].fillna(0.0) <= 0.1, "liq_penalty"] += 0.3
    # penalty for large spread relative to lastPrice
    df.loc[(df["lastPrice"].fillna(0.0) > 0) & ((df["spread"].fillna(0.0) / df["lastPrice"].fillna(1.0)) > 0.5), "liq_penalty"] += 0.2

    df["score_post_liq"] = (df["base_score"] - df["liq_penalty"]).clip(lower=0.0)
    return df

# ---------- IV skew & OI imbalance biases ----------
def compute_iv_pe_pair(df: pd.DataFrame) -> pd.DataFrame:
    """Pivot IV per strike into CE_iv / PE_iv columns."""
    if df is None or df.empty:
        return pd.DataFrame(columns=["strike", "CE_iv", "PE_iv"])
    tmp = _coerce_cols(df)
    pivot = tmp.pivot_table(index="strike", columns="type", values="iv", aggfunc="mean")
    # rename to CE_iv / PE_iv where present
    pivot = pivot.rename(columns={c: f"{c}_iv" for c in pivot.columns})
    pivot = pivot.reset_index()
    if "CE_iv" not in pivot.columns:
        pivot["CE_iv"] = np.nan
    if "PE_iv" not in pivot.columns:
        pivot["PE_iv"] = np.nan
    return pivot[["strike", "CE_iv", "PE_iv"]]

def _compute_oi_imbalance(option_chain_df: pd.DataFrame, atm: float, window_strikes: int = 3) -> float:
    """Compute CE - PE imbalance using change_oi preferred, else oi."""
    if option_chain_df is None or option_chain_df.empty:
        return 0.0
    df = _coerce_cols(option_chain_df)
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
    """Apply IV-based small biases to score_post_liq."""
    df = df.copy()
    if df.empty:
        return df
    if iv_map is None or iv_map.empty:
        return df
    ivmap = iv_map.copy()
    if "strike" not in ivmap.columns:
        return df
    # normalize ivmap columns to CE_iv / PE_iv
    rename = {}
    for c in ivmap.columns:
        if str(c).upper().startswith("CE") and c != "CE_iv":
            rename[c] = "CE_iv"
        if str(c).upper().startswith("PE") and c != "PE_iv":
            rename[c] = "PE_iv"
    if rename:
        ivmap = ivmap.rename(columns=rename)
    df = df.merge(ivmap, on="strike", how="left")
    df["CE_iv"] = pd.to_numeric(df.get("CE_iv", np.nan), errors="coerce")
    df["PE_iv"] = pd.to_numeric(df.get("PE_iv", np.nan), errors="coerce")
    df["iv_diff"] = df["PE_iv"].fillna(0.0) - df["CE_iv"].fillna(0.0)
    df["iv_bias"] = _sigmoid(df["iv_diff"].fillna(0.0)) * 0.05
    df.loc[df["type"].str.upper() == "CE", "score_post_liq"] += df.loc[df["type"].str.upper() == "CE", "iv_bias"]
    df.loc[df["type"].str.upper() == "PE", "score_post_liq"] += (-df.loc[df["type"].str.upper() == "PE", "iv_bias"])
    return df

# ---------- Pick top strikes with optional bias shifting ----------
def _find_neighbor(df: pd.DataFrame, strike_base: int, side: str, shift_dir: int, spot: float, weights=None, max_steps=5):
    """Search neighbor strikes by shift_dir (+1 higher strike, -1 lower strike)."""
    if df is None or df.empty:
        return None
    strikes = sorted(df["strike"].dropna().unique())
    if not strikes:
        return None
    if strike_base not in strikes:
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
            scored = scored.sort_values("score_post_liq", ascending=False)
            return _ensure_df(scored.head(1))
    return None

def top_strikes(df: pd.DataFrame, spot: float, top_n=3, option_type='CE', expiry=None, weights=None):
    """Return top_n strikes for a given option side using base scoring & liquidity penalty."""
    if df is None or df.empty:
        return pd.DataFrame()
    if expiry is not None:
        df = df[df["expiry"] == expiry].copy()
    df = _coerce_cols(df)
    side_df = df[df["type"].str.upper() == option_type].copy()
    if side_df.empty:
        return side_df
    scored = compute_base_scores(side_df, spot, weights=weights)
    scored = apply_liquidity_penalty(scored)
    iv_map = compute_iv_pe_pair(df)
    scored = apply_biases(scored, iv_map)
    scored = scored.sort_values("score_post_liq", ascending=False)
    tmp = compute_base_scores(side_df, spot)
    tmp = apply_liquidity_penalty(tmp)
    print(tmp[['strike', 'oi', 'change_oi', 'n_oi', 'n_doi', 'base_score', 'liq_penalty', 'score_post_liq']].head(10))

    return scored.head(top_n)

def pick_best_ce_pe(option_chain_df: pd.DataFrame, spot: float, expiry=None, top_n=1, weights=None, shift_steps: int = 1) -> Dict[str, pd.DataFrame]:
    """Return best CE/PE picks with bias shifts and safety."""
    if option_chain_df is None:
        return {"CE": pd.DataFrame(), "PE": pd.DataFrame()}
    df = option_chain_df.copy()
    df = _coerce_cols(df)
    if df.empty:
        return {"CE": pd.DataFrame(), "PE": pd.DataFrame()}
    if expiry is not None:
        df = df[df["expiry"] == expiry].copy()
    try:
        atm = int(min(df["strike"].dropna().unique(), key=lambda s: abs(s - spot)))
    except Exception:
        atm = int(round(spot / 100) * 100)

    ce_base = top_strikes(df, spot, top_n=top_n, option_type="CE", expiry=expiry, weights=weights)
    pe_base = top_strikes(df, spot, top_n=top_n, option_type="PE", expiry=expiry, weights=weights)

    ce_df = _ensure_df(ce_base)
    pe_df = _ensure_df(pe_base)

    oi_imb = _compute_oi_imbalance(df, atm, window_strikes=3)
    total_oi_window = df[(df["strike"] >= atm - 300) & (df["strike"] <= atm + 300)]["oi"].sum()
    threshold = max(200.0, 0.005 * max(1.0, total_oi_window))

    bias = 0
    if oi_imb > threshold:
        bias = 1
    elif oi_imb < -threshold:
        bias = -1

    # directional shifting
    if bias != 0:
        try:
            ce_base_strike = int(ce_df.iloc[0]["strike"])
        except Exception:
            ce_base_strike = atm
        try:
            pe_base_strike = int(pe_df.iloc[0]["strike"])
        except Exception:
            pe_base_strike = atm

        if bias == 1:
            alt_ce = _find_neighbor(df, ce_base_strike, "CE", shift_dir=+1, spot=spot, weights=weights)
            alt_pe = _find_neighbor(df, pe_base_strike, "PE", shift_dir=-1, spot=spot, weights=weights)
        else:
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

    # hard safety: avoid same strike for both
    try:
        if not ce_df.empty and not pe_df.empty:
            if int(ce_df.iloc[0]["strike"]) == int(pe_df.iloc[0]["strike"]):
                strikes = sorted(df["strike"].dropna().unique())
                base_strike = int(ce_df.iloc[0]["strike"])
                if base_strike in strikes:
                    idx = strikes.index(base_strike)
                    shifted = None
                    if idx - 1 >= 0:
                        alt = df[(df["strike"] == strikes[idx - 1]) & (df["type"].str.upper() == "PE")]
                        if not alt.empty:
                            shifted = alt
                    if shifted is None and idx + 1 < len(strikes):
                        alt = df[(df["strike"] == strikes[idx + 1]) & (df["type"].str.upper() == "PE")]
                        if not alt.empty:
                            shifted = alt
                    if shifted is not None and not shifted.empty:
                        pe_df = _ensure_df(_coerce_cols(shifted))
                    else:
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
