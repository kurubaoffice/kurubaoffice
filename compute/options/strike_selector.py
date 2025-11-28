import pandas as pd
import numpy as np
from typing import Dict

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
    df = df.copy()
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
    REQUIRED_NUM = ["strike", "oi", "change_oi", "volume", "iv", "bid", "ask", "lastPrice", "spot"]
    REQUIRED_STR = ["type", "optionType", "expiry"]
    for col in REQUIRED_NUM:
        if col not in df.columns:
            df[col] = np.nan
    for col in REQUIRED_STR:
        if col not in df.columns:
            df[col] = None
    def _pick_type(row):
        for key in ("optionType", "type", "instrument_type"):
            if key in row and pd.notna(row.get(key)):
                return str(row.get(key)).upper()
        return np.nan
    if "type" not in df.columns or df["type"].isnull().all():
        df["type"] = df.apply(_pick_type, axis=1)
    num_cols = ["strike", "oi", "change_oi", "volume", "iv", "bid", "ask", "lastPrice", "spot"]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def _ensure_df(x):
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

def _synthesize_bids(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "bid" not in df.columns:
        return df
    mask_bad_bid = (df["bid"].isna()) | (df["bid"] <= 0.0)
    if mask_bad_bid.any():
        use_ask = mask_bad_bid & (df["ask"].notna()) & (df["ask"] > 0)
        df.loc[use_ask, "bid"] = df.loc[use_ask, "ask"] * 0.85
        use_mid = mask_bad_bid & (df["ask"].notna()) & (df["lastPrice"].notna()) & (df["ask"] > 0) & (df["lastPrice"] > 0)
        df.loc[use_mid, "bid"] = (df.loc[use_mid, "ask"] + df.loc[use_mid, "lastPrice"]) / 2.0
        still_bad = mask_bad_bid & (df["bid"].isna() | (df["bid"] <= 0.0))
        if still_bad.any():
            df.loc[still_bad, "bid"] = 0.01
    return df

def _normalize_series(s: pd.Series) -> pd.Series:
    if s is None or s.empty:
        return pd.Series(dtype=float)
    if s.isnull().all():
        return pd.Series(0.0, index=s.index)
    mn, mx = s.min(), s.max()
    if pd.isna(mn) or pd.isna(mx):
        return pd.Series(0.0, index=s.index)
    if mx == mn:
        return pd.Series(0.5, index=s.index)
    return (s - mn) / (mx - mn)

# ---------- Scoring ----------
def compute_base_scores(df: pd.DataFrame, spot: float, weights: Dict[str, float] = None) -> pd.DataFrame:
    w = DEFAULT_WEIGHTS.copy()
    if weights:
        w.update(weights)
    df = _coerce_cols(df)
    df = df[~((df["bid"].isna() | (df["bid"] <= 0)) & (df["ask"].isna() | (df["ask"] <= 0)))]
    if df.empty:
        return df
    df = _synthesize_bids(df)
    df["spread"] = (df["ask"] - df["bid"]).abs()
    df["dist_abs"] = (df["strike"] - spot).abs()
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
    df.loc[df["dist_abs"] <= 100, "base_score"] += 0.05
    df["base_score"] = df["base_score"].fillna(0.0) + 0.01
    return df

def apply_liquidity_penalty(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if df.empty:
        return df
    df["spread"] = (df.get("ask", 0.0) - df.get("bid", 0.0)).abs().fillna(0.0)
    df["lastPrice"] = df.get("lastPrice", 0.0)
    df["liq_penalty"] = 0.0
    df.loc[df["bid"].fillna(0.0) <= 0.1, "liq_penalty"] += 0.3
    df.loc[(df["lastPrice"] > 0) & ((df["spread"] / df["lastPrice"]) > 0.5), "liq_penalty"] += 0.2
    df["score_post_liq"] = (df["base_score"] - df["liq_penalty"]).clip(lower=0.0)
    return df

def compute_iv_pe_pair(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["strike", "CE_iv", "PE_iv"])
    tmp = _coerce_cols(df)
    pivot = tmp.pivot_table(index="strike", columns="type", values="iv", aggfunc="mean")
    pivot = pivot.rename(columns={c: f"{c}_iv" for c in pivot.columns})
    pivot = pivot.reset_index()
    if "CE_iv" not in pivot.columns:
        pivot["CE_iv"] = np.nan
    if "PE_iv" not in pivot.columns:
        pivot["PE_iv"] = np.nan
    return pivot[["strike", "CE_iv", "PE_iv"]]

def apply_biases(df: pd.DataFrame, iv_map: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if df.empty or iv_map is None or iv_map.empty:
        return df
    ivmap = iv_map.copy()
    if "strike" not in ivmap.columns:
        return df
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

def top_strikes(df: pd.DataFrame, spot: float, top_n=3, option_type='CE', expiry=None, weights=None):
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
    return scored.head(top_n)

def pick_best_ce_pe(option_chain_df: pd.DataFrame, spot: float, expiry=None, top_n=1, weights=None) -> Dict[str, pd.DataFrame]:
    if option_chain_df is None:
        return {"CE": pd.DataFrame(), "PE": pd.DataFrame()}
    df = _coerce_cols(option_chain_df)
    if expiry is not None:
        df = df[df["expiry"] == expiry].copy()
    try:
        atm = int(min(df["strike"].dropna().unique(), key=lambda s: abs(s - spot)))
    except Exception:
        atm = int(round(spot / 100) * 100)
    ce_base = top_strikes(df, spot, top_n=top_n, option_type="CE", expiry=expiry, weights=weights)
    pe_base = top_strikes(df, spot, top_n=top_n, option_type="PE", expiry=expiry, weights=weights)
    return {"CE": _ensure_df(ce_base), "PE": _ensure_df(pe_base)}
