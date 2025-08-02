import pandas as pd
import pytest
from compute.apply_indicators import apply_all_indicators

# ---------- Dummy data for testing ----------
def dummy_ohlcv_data(rows=30):
    return pd.DataFrame({
        'open': [100 + i for i in range(rows)],
        'high': [101 + i for i in range(rows)],
        'low':  [99 + i for i in range(rows)],
        'close': [100 + i for i in range(rows)],
        'volume': [1000 + i for i in range(rows)],
    })

# ---------- Test cases ----------
def test_rsi_only():
    df = dummy_ohlcv_data()
    config = {"indicators": {"rsi": True}}

    result = apply_all_indicators(df.copy(), config)
    assert 'rsi_14' in result.columns
    assert 'macd' not in result.columns
    assert 'atr_14' not in result.columns

def test_macd_only():
    df = dummy_ohlcv_data()
    config = {"indicators": {"macd": True}}

    result = apply_all_indicators(df.copy(), config)
    assert 'macd' in result.columns
    assert 'macd_signal' in result.columns
    assert 'rsi_14' not in result.columns

def test_all_indicators():
    df = dummy_ohlcv_data()
    config = {
        "indicators": {
            "rsi": True,
            "macd": True,
            "bollinger": True,
            "supertrend": True,
            "adx": True,
            "atr": True
        }
    }

    result = apply_all_indicators(df.copy(), config)

    expected_cols = ['rsi_14', 'macd', 'macd_signal', 'bb_upper', 'bb_lower',
                     'supertrend_7', 'supertrend_7_dir', 'adx_14', 'atr_14']
    for col in expected_cols:
        assert col in result.columns, f"Missing {col}"

def test_no_indicators():
    df = dummy_ohlcv_data()
    config = {"indicators": {}}

    result = apply_all_indicators(df.copy(), config)
    assert len(result.columns) == 5  # Only OHLCV
