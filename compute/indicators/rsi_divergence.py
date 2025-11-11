# compute/indicators/rsi_divergence.py
"""
Detect RSI divergences (bullish / bearish) between price and RSI.
Returns a list of divergence dicts with details ready for alerting.
"""

from typing import List, Dict, Optional
import pandas as pd
import numpy as np


def _is_local_min(series: pd.Series, idx: int, left: int = 3, right: int = 3) -> bool:
    """Simple local min check over neighborhood [idx-left, idx+right]."""
    start = max(0, idx - left)
    end = min(len(series) - 1, idx + right)
    val = series.iloc[idx]
    return val == series.iloc[start:end+1].min()


def _is_local_max(series: pd.Series, idx: int, left: int = 3, right: int = 3) -> bool:
    start = max(0, idx - left)
    end = min(len(series) - 1, idx + right)
    val = series.iloc[idx]
    return val == series.iloc[start:end+1].max()


def find_rsi_divergences(
    df: pd.DataFrame,
    price_col: str = "close",
    rsi_col: str = "rsi",
    lookback: int = 60,
    neighbor: int = 3,
    require_confirmation: bool = True,
    confirmation_ma: int = 20,
    require_green_candle: bool = True,
    rr_ratio: float = 3.0,
    min_rsi_diff: float = 2.0,
) -> List[Dict]:
    """
    Detect RSI divergences in the last `lookback` bars of df.

    Parameters
    ----------
    df : DataFrame
        Must include columns price_col and rsi_col (and open if require_green_candle).
    lookback : int
        How many latest bars to scan.
    neighbor : int
        Neighborhood size for local min/max detection.
    require_confirmation : bool
        If True, require confirmation condition (green candle and/or close > MA).
    confirmation_ma : int
        Moving average period used as "trend" check (close above MA = bullish confirmation).
    require_green_candle : bool
        If True require last candle close > open for bullish confirmation.
    rr_ratio : float
        Suggested risk:reward (1:3 = 3.0)
    min_rsi_diff : float
        Minimum RSI difference between pivots to consider (helps avoid tiny noise)

    Returns
    -------
    List[Dict]
        Each dict contains:
            'symbol', 'type' ('bullish'/'bearish'),
            'price_pivots': [(idx, price), (...)] ,
            'rsi_pivots': [(idx, rsi), (...)] ,
            'last_index', 'confidence' (0-1), 'rr_ratio', 'notes'
    """

    # Work on a copy and recent slice
    df2 = df.tail(lookback).reset_index(drop=False)  # keep original index if present
    price = df2[price_col]
    rsi = df2[rsi_col]
    idx_map = df2.index  # integer indices 0..n

    divergences = []

    # Precompute MA if needed
    if require_confirmation:
        df2["ma_trend"] = df2[price_col].rolling(confirmation_ma, min_periods=1).mean()

    n = len(df2)
    # collect local minima and maxima indices for price and rsi
    price_lows = [i for i in range(n) if _is_local_min(price, i, neighbor, neighbor)]
    price_highs = [i for i in range(n) if _is_local_max(price, i, neighbor, neighbor)]
    rsi_lows = [i for i in range(n) if _is_local_min(rsi, i, neighbor, neighbor)]
    rsi_highs = [i for i in range(n) if _is_local_max(rsi, i, neighbor, neighbor)]

    # For bullish divergence: find consecutive price lows (prev_low, recent_low) where recent_low < prev_low
    # and corresponding RSI lows where recent_rsi > prev_rsi
    # We'll match nearest prior pivot (simple heuristic)
    def match_pivots(price_pivots, rsi_pivots, bullish=True):
        results = []
        # iterate over pairs of pivots in price_pivots (older -> newer)
        for j in range(1, len(price_pivots)):
            i_prev = price_pivots[j-1]
            i_now = price_pivots[j]
            # ensure chronological order
            if i_prev >= i_now:
                continue

            price_prev = price.iloc[i_prev]
            price_now = price.iloc[i_now]

            # bullish: price_now lower than price_prev (lower low)
            if bullish and not (price_now < price_prev):
                continue
            # bearish: price_now higher than price_prev (higher high)
            if (not bullish) and not (price_now > price_prev):
                continue

            # Find nearest rsi pivot before or around the same indices (simple heuristic)
            # locate rsi pivot indices around the price pivot indexes
            def nearest_rsi(idx):
                # choose rsi pivot with minimal abs distance
                if not rsi_pivots:
                    return None
                distances = [(abs(idx - r), r) for r in rsi_pivots]
                return sorted(distances, key=lambda x: x[0])[0][1]

            r_prev_idx = nearest_rsi(i_prev)
            r_now_idx = nearest_rsi(i_now)
            if r_prev_idx is None or r_now_idx is None:
                continue

            r_prev = rsi.iloc[r_prev_idx]
            r_now = rsi.iloc[r_now_idx]

            # bullish divergence: r_now > r_prev (higher low in RSI)
            if bullish and not (r_now > r_prev + min_rsi_diff * 0.01 * 100):  # avoid tiny differences, but keep tolerance small
                # simpler: require r_now > r_prev + min_rsi_diff (absolute)
                # we'll use absolute diff
                if not (r_now - r_prev >= min_rsi_diff):
                    continue
            # bearish divergence: r_now < r_prev (lower high in RSI)
            if (not bullish) and not (r_now < r_prev - min_rsi_diff):
                if not (r_prev - r_now >= min_rsi_diff):
                    continue

            # gather details
            last_idx = max(i_prev, i_now, r_prev_idx, r_now_idx)
            # confirmation checks
            notes = []
            confirm_pass = True
            if require_confirmation:
                # green candle requirement (for bullish) or red candle (for bearish) can be optional - apply for bullish only as default
                if bullish and require_green_candle:
                    # check last candle (i_now) open/close
                    o_col = df2.columns[df2.columns.str.lower() == "open"]
                    if len(o_col) == 0:
                        # can't check candle color
                        notes.append("open not present; skipped green-candle confirmation")
                    else:
                        o_col = o_col[0]
                        if not (df2.loc[i_now, price_col] > df2.loc[i_now, o_col]):
                            confirm_pass = False
                            notes.append("no green candle confirmation at recent pivot")

                # check close above trend MA for bullish
                if bullish and require_confirmation and "ma_trend" in df2.columns:
                    if not (df2.loc[i_now, price_col] > df2.loc[i_now, "ma_trend"]):
                        confirm_pass = False
                        notes.append(f"close below {confirmation_ma}-MA")

                # for bearish we could check close below MA - optional (not enforced)
                if (not bullish) and require_confirmation and "ma_trend" in df2.columns:
                    if not (df2.loc[i_now, price_col] < df2.loc[i_now, "ma_trend"]):
                        notes.append(f"bearish pivot not below {confirmation_ma}-MA (no confirmation)")

            # confidence heuristic (simple): magnitude of divergence in RSI relative to range -> scaled 0-1
            rsi_range = rsi.max() - rsi.min() if rsi.max() != rsi.min() else 1.0
            confidence = min(1.0, max(0.0, abs(r_now - r_prev) / (rsi_range)))  # simple proxy

            results.append({
                "type": "bullish" if bullish else "bearish",
                "price_pivots": [(int(i_prev), float(price_prev)), (int(i_now), float(price_now))],
                "rsi_pivots": [(int(r_prev_idx), float(r_prev)), (int(r_now_idx), float(r_now))],
                "last_index": int(last_idx),
                "confidence": round(float(confidence), 3),
                "rr_ratio": rr_ratio,
                "confirmed": bool(confirm_pass),
                "notes": notes
            })

        return results

    # compute bullish matches
    bullish = match_pivots(price_lows, rsi_lows, bullish=True)
    bearish = match_pivots(price_highs, rsi_highs, bullish=False)

    divergences.extend(bullish)
    divergences.extend(bearish)

    # attach absolute timestamps/index mapping if df had original index/DatetimeIndex
    # if original df had a datetime index we can map using df.tail(lookback).index
    try:
        original_index = df.tail(lookback).index
        for d in divergences:
            li = d["last_index"]
            # map li (0..n-1 in df2) to original index value
            if len(original_index) > li:
                d["last_index_label"] = str(original_index[li])
            else:
                d["last_index_label"] = None
    except Exception:
        for d in divergences:
            d["last_index_label"] = None

    return divergences
