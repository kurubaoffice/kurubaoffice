# File: compute/indicators/atr.py

import pandas as pd
import yfinance as yf
import ta
from datetime import datetime


def fetch_price_data(symbol, period="9mo", interval="1d"):
    try:
        df = yf.download(symbol, period=period, interval=interval, auto_adjust=False, actions=False)
        if df.empty:
            raise ValueError(f"[ERROR] No data returned for {symbol}")

        # Flatten multi-index columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0].lower() for col in df.columns]
        else:
            df.columns = [col.lower() for col in df.columns]

        df.reset_index(inplace=True)

        print(f"[INFO] Data downloaded for {symbol}: {len(df)} rows")
        return df

    except Exception as e:
        print(f"[ERROR] fetch_price_data failed: {e}")
        return pd.DataFrame()



def apply_atr(df, config=None):
    try:
        if config and not config.get("atr", True):
            print("[INFO] ATR is disabled in config.")
            return df, False

        assert isinstance(df, pd.DataFrame), "[apply_atr] Input is not a DataFrame"

        required_cols = ["high", "low", "close"]
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"[apply_atr] Missing required column: {col}")

        atr_period = config.get("atr_period", 14) if config else 14

        print(f"[DEBUG] Columns present: {df.columns.tolist()}")
        print(f"[DEBUG] Sample data:\n{df[['high', 'low', 'close']].tail(3)}")

        atr = ta.volatility.AverageTrueRange(
            high=df["high"], low=df["low"], close=df["close"], window=atr_period
        )
        atr_series = atr.average_true_range()

        print(f"[DEBUG] ATR Series type: {type(atr_series)}")
        print(f"[DEBUG] ATR Series sample:\n{atr_series.tail(3)}")

        if not isinstance(atr_series, pd.Series):
            raise TypeError("[apply_atr] Computed ATR is not a Series")

        df[f"atr_{atr_period}"] = atr_series

        print(f"[DEBUG] ✅ ATR applied with window={atr_period}")
        return df, True

    except Exception as e:
        print(f"[ERROR] apply_atr failed: {e}")
        return df, False


def interpret_atr(df, atr_column="atr_14"):
    try:
        assert isinstance(df, pd.DataFrame), "[interpret_atr] Input is not a DataFrame"
        if atr_column not in df.columns:
            raise ValueError(f"[interpret_atr] Missing ATR column: {atr_column}")

        last_atr = df[atr_column].iloc[-1]
        last_close = df['close'].iloc[-1]

        if pd.isna(last_atr) or pd.isna(last_close):
            raise ValueError("[interpret_atr] NaN detected in ATR or Close")

        volatility_pct = round((last_atr / last_close) * 100, 2)
        atr_value = round(last_atr, 2)

        if volatility_pct >= 3:
            interpretation = f"High Volatility: ATR is {volatility_pct:.2f}% of price"
        elif volatility_pct <= 1:
            interpretation = f"Low Volatility: ATR is {volatility_pct:.2f}% of price"
        else:
            interpretation = f"Moderate Volatility: ATR is {volatility_pct:.2f}% of price"

        return pd.DataFrame([{
            "indicator": "ATR",
            "atr_value": atr_value,
            "volatility_pct": volatility_pct,
            "interpretation": interpretation
        }])

    except Exception as e:
        print(f"[ERROR] interpret_atr failed: {e}")
        return pd.DataFrame([{
            "indicator": "ATR",
            "atr_value": None,
            "volatility_pct": None,
            "interpretation": "ATR interpretation failed"
        }])


# ✅ MAIN BLOCK FOR TESTING
def main():
    symbol = "ITC.NS"
    config = {
        "atr": True,
        "atr_period": 14
    }

    df = fetch_price_data(symbol)
    if df.empty:
        print("[ABORT] No data available.")
        return

    df, applied = apply_atr(df, config)

    if applied:
        result_df = interpret_atr(df, atr_column=f"atr_{config['atr_period']}")
    else:
        result_df = pd.DataFrame([{
            "indicator": "ATR",
            "atr_value": None,
            "volatility_pct": None,
            "interpretation": "ATR not applied (disabled in config or failed)"
        }])

    print("\n[FINAL ATR RESULT]")
    print(result_df.to_string(index=False))


if __name__ == "__main__":
    main()
