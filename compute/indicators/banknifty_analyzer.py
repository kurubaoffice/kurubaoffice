import os
import pandas as pd
import yfinance as yf
from tqdm import tqdm

from modules.data_fetcher.fetch_price_data import fetch_price_data
from modules.indicators.indicators import apply_all_indicators
import os
import pandas as pd
import yfinance as yf
from tqdm import tqdm

from modules.data_fetcher.fetch_price_data import fetch_price_data
from modules.indicators.indicators import apply_all_indicators

BANKNIFTY_STOCKS = [
    'AXISBANK', 'BANDHANBNK', 'BANKBARODA', 'FEDERALBNK', 'HDFCBANK',
    'ICICIBANK', 'IDFCFIRSTB', 'INDUSINDBK', 'KOTAKBANK', 'PNB', 'RBLBANK',
    'SBIN', 'YESBANK'
]

CONFIG = {
    "indicators": {
        "rsi": True,
        "macd": True,
        "bollinger": True,
        "supertrend": True,
        "adx": True,
        "atr": True
    }
}
def get_index_historical(ticker="^NSEBANK", period="6mo", interval="1d") -> pd.DataFrame:
    df = yf.download(ticker, period=period, interval=interval, progress=False)

    if df.empty:
        raise ValueError(f"Failed to fetch data for index: {ticker}")

    df.reset_index(inplace=True)

    # Handle MultiIndex column names safely
    df.columns = [col[0].lower() if isinstance(col, tuple) else col.lower().strip() for col in df.columns]

    # Handle prefixed columns like 'close_^nsebank'
    suffix = ticker.lower().replace("^", "")
    suffix = f"_{suffix}"

    renamed = {}
    for col in df.columns:
        for base in ['open', 'high', 'low', 'close', 'volume']:
            if col == f"{base}{suffix}":
                renamed[col] = base
    df.rename(columns=renamed, inplace=True)

    # Rename first column to 'date' if not present
    if 'date' not in df.columns and df.columns[0] not in ['open', 'high', 'low', 'close', 'volume']:
        df.rename(columns={df.columns[0]: 'date'}, inplace=True)

    expected = ["date", "open", "high", "low", "close", "volume"]
    missing = set(expected) - set(df.columns)

    if missing:
        raise ValueError(f"[get_index_historical] Missing columns: {missing}\nColumns present: {df.columns.tolist()}")

    return df[expected]



def analyze_banknifty_index():
    try:
        df = get_index_historical("^NSEBANK", period="6mo", interval="1d")

        required_cols = {'open', 'high', 'low', 'close', 'volume'}
        if not required_cols.issubset(df.columns):
            return {"error": f"Missing columns: {required_cols - set(df.columns)}"}

        df = apply_all_indicators(df, CONFIG)
        latest = df.iloc[-1]

        cmp = latest["close"]
        atr = latest.get("atr_14", 0)
        rsi = latest.get("rsi_14", None)
        macd = latest.get("macd", None)
        macd_signal = latest.get("macd_signal", None)
        st_dir = latest.get("supertrend_7_dir", None)
        adx = latest.get("adx_14", None)
        bb_upper = latest.get("bb_upper", None)
        bb_lower = latest.get("bb_lower", None)

        projected_high = cmp + atr if atr else None
        projected_low = cmp - atr if atr else None
        trend = "Bullish" if st_dir and rsi and rsi > 50 else "Bearish"

        return {
            "cmp": cmp,
            "rsi": rsi,
            "macd": macd,
            "macd_signal": macd_signal,
            "supertrend": st_dir,
            "adx": adx,
            "bb_upper": bb_upper,
            "bb_lower": bb_lower,
            "atr": atr,
            "projected_high": projected_high,
            "projected_low": projected_low,
            "trend": trend
        }

    except Exception as e:
        return {"error": str(e)}


def is_bullish_signal(latest):
    supertrend = latest.get('supertrend_7_dir')
    rsi = latest.get('rsi_14')
    macd = latest.get('macd')
    macd_signal = latest.get('macd_signal')
    adx = latest.get('adx_14')

    if None in [supertrend, rsi, macd, macd_signal]:
        return None

    return (
        supertrend is True and
        rsi > 50 and
        macd > macd_signal and
        (adx is None or adx > 20)
    )


def save_with_indicators(df, symbol, path="data/processed_with_signals"):
    os.makedirs(path, exist_ok=True)
    file_path = os.path.join(path, f"{symbol}.csv")
    df.to_csv(file_path, index=False)
    print(f"✅ Saved indicators for {symbol} → {file_path}")


def analyze_banknifty_stocks(save_data=False):
    summary = []
    bullish_count = 0
    bearish_count = 0

    print("📊 Analyzing Stocks:")
    for symbol in tqdm(BANKNIFTY_STOCKS):
        try:
            df = fetch_price_data(symbol)
            if df is None or df.empty:
                raise ValueError(f"No historical data for {symbol}")

            # Sanitize columns
            df.columns = [col.lower().strip() for col in df.columns]
            if not all(col in df.columns for col in ['open', 'high', 'low', 'close']):
                raise ValueError(f"Missing OHLC columns in data: {df.columns.tolist()}")

            if isinstance(df['close'], pd.DataFrame):
                print(f"[WARNING] df['close'] is a DataFrame, converting to Series")
                df['close'] = df['close'].iloc[:, 0]

            df = apply_all_indicators(df, CONFIG)
            latest = df.iloc[-1]

            signal = is_bullish_signal(latest)
            if signal is None:
                status = "Insufficient Data"
            elif signal:
                status = "Bullish"
                bullish_count += 1
            else:
                status = "Bearish"
                bearish_count += 1

            summary.append((symbol, status))

            if save_data:
                save_with_indicators(df, symbol)

        except Exception as e:
            print(f"[ERROR] {symbol}: {e}")
            summary.append((symbol, f"Error: {str(e)}"))

    overall_trend = "Bullish" if bullish_count > bearish_count else "Bearish"
    return summary, overall_trend


def format_banknifty_report(summary, overall, index_info=None):
    report = "+-------------------+-----------+\n"
    report += "| Bank              | Status    |\n"
    report += "+-------------------+-----------+\n"
    for symbol, status in summary:
        report += f"| {symbol.ljust(18)} | {status.ljust(9)} |\n"
    report += "+-------------------+-----------+\n"
    report += f"📊 Overall Bank Nifty Trend: {overall}\n"

    if index_info and "cmp" in index_info:
        report += "\n📈 Bank Nifty Index Snapshot:\n"
        report += f"  CMP         : {index_info['cmp']:.2f}\n"
        report += f"  RSI         : {index_info['rsi']:.2f}\n"
        report += f"  MACD        : {index_info['macd']:.2f}\n"
        report += f"  MACD Signal : {index_info['macd_signal']:.2f}\n"
        report += f"  Supertrend  : {'Bullish' if index_info['supertrend'] else 'Bearish'}\n"
        report += f"  ADX         : {index_info['adx']:.2f}\n"
        report += f"  Bollinger   : {index_info['bb_lower']:.2f} - {index_info['bb_upper']:.2f}\n"
        report += f"  ATR         : {index_info['atr']:.2f}\n"
        report += f"  📌 1-ATR Projection: {index_info['projected_low']:.2f} - {index_info['projected_high']:.2f}\n"
        report += f"  🔮 Inferred Trend : {index_info['trend']}\n"
    elif index_info and "error" in index_info:
        report += f"\n📊 Index Info Error: {index_info['error']}\n"

    return report


# ✅ CLI Entry Point
if __name__ == "__main__":
    print("🚀 Starting BANKNIFTY Analysis...\n")
    try:
        summary, overall_trend = analyze_banknifty_stocks(save_data=True)
        index_info = analyze_banknifty_index()
        report = format_banknifty_report(summary, overall_trend, index_info=index_info)
        print(report)
        print(f"📦 Stock Summary: {summary}")
        print(f"📊 Index Info: {index_info}")
    except Exception as e:
        print(f"❌ ERROR: {e}")
