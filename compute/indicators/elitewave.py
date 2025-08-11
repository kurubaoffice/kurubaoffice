"""
compute/indicators/elitewave.py

Lightweight pivot-based 'EliteWave' implementation (Elliott-style zigzag + labelling).
Returns pivot markers and a heuristic confidence score.
"""

from typing import Tuple, Dict
import pandas as pd
import numpy as np

def detect_pivots(df: pd.DataFrame, left: int = 5, right: int = 5, price_col: str = "close") -> pd.Series:
    """
    Mark pivot highs/lows.
    Returns a Series with values: 'high', 'low', or np.nan
    """
    prices = df[price_col].values
    n = len(prices)
    pivots = np.array([np.nan] * n, dtype=object)

    for i in range(left, n - right):
        window = prices[i - left: i + right + 1]
        center = prices[i]
        if center == window.max() and np.sum(window == center) == 1:
            pivots[i] = "high"
        elif center == window.min() and np.sum(window == center) == 1:
            pivots[i] = "low"
    return pd.Series(pivots, index=df.index)

def build_wave_labels(df: pd.DataFrame, pivots: pd.Series, price_col: str = "close") -> Tuple[pd.Series, pd.Series]:
    """
    Basic labelling:
    - Walk through pivot points and attempt to label a sequence 1-5 then A-B-C.
    - This is heuristic: label only when sufficient structure detected.
    Returns:
      - wave_label_series (labels at pivot bar indices)
      - pivot_price_series (price at pivot)
    """
    labels = pd.Series(index=df.index, dtype=object)
    pprice = pd.Series(index=df.index, dtype=float)

    pivot_idx = [i for i, v in enumerate(pivots.values) if pd.notna(v)]
    pivot_types = [pivots.values[i] for i in pivot_idx]
    prices = df[price_col].values

    # minimal state machine: try to detect motive 1-5 by alternating highs/lows pattern
    # We'll scan and attempt to assign numeric labels incrementally
    seq = []
    seq_idx = []
    for idx, ptype in zip(pivot_idx, pivot_types):
        seq.append(ptype)
        seq_idx.append(idx)

    # simple greedy labeller: find runs of 5 pivots that resemble 1-5
    # pattern for upward motive: low(1) high(2) low(3) high(4) low(5) with increasing highs/lows
    i = 0
    while i <= len(seq) - 5:
        window_types = seq[i:i+5]
        window_idx = seq_idx[i:i+5]
        window_prices = [prices[j] for j in window_idx]

        # check alternating low/high starting with 'low' (motive up) or starting with 'high' (motive down)
        def is_increasing_motive(wtypes, wprices):
            # expected low, high, low, high, low
            expected = ['low', 'high', 'low', 'high', 'low']
            if wtypes != expected:
                return False
            # check price monotonicity for motive up
            lows = [wprices[0], wprices[2], wprices[4]]
            highs = [wprices[1], wprices[3]]
            return (lows[0] < lows[1] < lows[2]) and (highs[0] < highs[1])

        def is_decreasing_motive(wtypes, wprices):
            expected = ['high', 'low', 'high', 'low', 'high']
            if wtypes != expected:
                return False
            highs = [wprices[0], wprices[2], wprices[4]]
            lows = [wprices[1], wprices[3]]
            return (highs[0] > highs[1] > highs[2]) and (lows[0] > lows[1])

        if is_increasing_motive(window_types, window_prices):
            # assign labels 1..5
            for j, pidx in enumerate(window_idx):
                labels.iloc[pidx] = str(j+1)
                pprice.iloc[pidx] = prices[pidx]
            i += 5
        elif is_decreasing_motive(window_types, window_prices):
            for j, pidx in enumerate(window_idx):
                labels.iloc[pidx] = str(j+1)
                pprice.iloc[pidx] = prices[pidx]
            i += 5
        else:
            i += 1

    # Attempt a simple corrective label A-B-C after last completed motive if possible
    # Find last labelled '5' and check next 3 pivots for A-B-C pattern (high/low alternation)
    labelled = [(idx, labels.iloc[idx]) for idx in range(len(labels)) if pd.notna(labels.iloc[idx])]
    if labelled:
        last_label_idx, last_label = labelled[-1]
        if last_label == '5':
            # find next pivots after last_label_idx
            after = [k for k in pivot_idx if k > last_label_idx]
            if len(after) >= 3:
                a,b,c = after[:3]
                # heuristic: A retraces, B partial retrace, C new low/high
                labels.iloc[a] = 'A'
                labels.iloc[b] = 'B'
                labels.iloc[c] = 'C'
                pprice.iloc[a] = prices[a]
                pprice.iloc[b] = prices[b]
                pprice.iloc[c] = prices[c]

    return labels, pprice

def compute_elitewave(df: pd.DataFrame, left: int = 5, right: int = 5, price_col: str = "close") -> Dict:
    """
    Add EliteWave columns to df (in-place-friendly).
    Returns a summary dict:
      {'trend': 'up'/'down'/'flat', 'current_wave': '3'/'A'/..., 'confidence': float}
    """
    df = df.copy()
    df['ew_pivot'] = detect_pivots(df, left=left, right=right, price_col=price_col)
    labels, pprice = build_wave_labels(df, df['ew_pivot'], price_col=price_col)
    df['ew_wave_label'] = labels
    df['ew_pivot_price'] = pprice

    # compute simple confidence:
    # + more labelled pivots -> higher confidence
    num_labels = df['ew_wave_label'].count()
    confidence = min(100.0, num_labels * 10.0)  # simple scaling: each labeled pivot adds 10%

    # current wave label (most recent non-null)
    recent = df['ew_wave_label'].dropna()
    current_wave = recent.iloc[-1] if len(recent) > 0 else None

    # infer trend
    if current_wave in ['1','3','5']:
        # earlier heuristic: if last motive wave number present, use pivot prices to decide direction
        last5 = df[df['ew_wave_label'].isin(['1','3','5'])]['ew_pivot_price'].dropna()
        if len(last5) >= 2:
            trend = 'up' if last5.iloc[-1] > last5.iloc[0] else 'down'
        else:
            trend = 'flat'
    elif current_wave in ['A','B','C']:
        trend = 'corrective'
    else:
        trend = 'flat'

    summary = {
        'trend': trend,
        'current_wave': str(current_wave) if current_wave is not None else None,
        'confidence': float(confidence),
        'num_labels': int(num_labels)
    }
    return {'df': df, 'summary': summary}
