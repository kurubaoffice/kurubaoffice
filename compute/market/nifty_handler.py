from fetcher.nse_session import nse_session
from compute.apply_indicators import apply_indicators
import pandas as pd
import requests
import yfinance as yf
from bot_ui.keyboards import market_menu_keyboard

# ------------------------------------------
# NSE Fetch Helper
# ------------------------------------------
def nsefetch(url: str):
    res = nse_session.get(url, timeout=5)
    res.raise_for_status()
    return res.json()


# ------------------------------------------
# Fetch Live NIFTY Price
# ------------------------------------------
def fetch_nifty_live():
    url = "https://www.nseindia.com/api/market-data-pre-open?key=NIFTY"
    data = nsefetch(url)

    # The structure is: data["data"] -> list -> first element -> metadata
    ndx = data["data"][0]["metadata"]

    price = float(ndx["last"])
    change = float(ndx["change"])
    percent = float(ndx["pChange"])
    prev_close = price - change

    return {
        "price": price,
        "change": change,
        "percent": percent,
        "prev_close": prev_close,
    }


# ------------------------------------------
# Fetch Historical for Indicators
# ------------------------------------------
def fetch_nifty_history():
    url = "https://www.nseindia.com/api/chart-databyindex?index=NIFTY%2050&preopen=false"
    data = nsefetch(url)

    raw = data.get("grapthData", [])

    if not raw:
        raise ValueError("No historical data received from NSE")

    # raw = [ [timestamp, close], ... ]
    df = pd.DataFrame(raw, columns=["timestamp", "close"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df["close"] = df["close"].astype(float)

    df = df.sort_values("timestamp").reset_index(drop=True)

    # Create OHLC from close (NSE doesn't give OHLC)
    df["open"] = df["close"]
    df["high"] = df["close"]
    df["low"] = df["close"]
    df["volume"] = 0

    return df


# ------------------------------------------
# Master Fetch + Indicators
# ------------------------------------------
def fetch_nifty_data():

    # ---------------------------------------------------
    # 1️⃣ LIVE PRICE FROM NSE (very reliable)
    # ---------------------------------------------------
    try:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.nseindia.com",
        }

        session = requests.Session()
        session.headers.update(headers)
        session.get("https://www.nseindia.com", timeout=5)

        data = session.get(
            "https://www.nseindia.com/api/allIndices", timeout=5
        ).json()

        nifty = next(
            (x for x in data["data"] if x["index"] == "NIFTY 50"),
            None
        )

        if not nifty:
            raise ValueError("NIFTY 50 not found")

        live_price = float(nifty["last"])

    except Exception as e:
        raise ValueError(f"NSE live price fetch failed: {e}")

    # ---------------------------------------------------
    # 2️⃣ RELIABLE OHLC FROM YAHOO (never blocked)
    # ---------------------------------------------------
    try:
        df = yf.download("^NSEI", period="3mo", interval="1d", auto_adjust=False, progress=False)
        if df.empty:
            raise ValueError("Yahoo returned empty data")

        df.reset_index(inplace=True)

        # ---- FIX MULTIINDEX ----
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [
                "_".join([str(c) for c in col if c]).strip()
                for col in df.columns
            ]

        # ---- LOWERCASE ----
        df.columns = [c.lower().strip() for c in df.columns]

        # ---- REMOVE SUFFIXES LIKE _^nsei ----
        for base in ["open", "high", "low", "close", "adj close", "volume"]:
            for col in list(df.columns):
                if col.startswith(base.replace(" ", "_")):
                    df.rename(
                        columns={col: base.replace("adj close", "close")},
                        inplace=True
                    )

        # ---- DROP DUPLICATE COLUMNS ----
        df = df.loc[:, ~df.columns.duplicated()]

        expected = ["date", "open", "high", "low", "close", "volume"]
        missing = set(expected) - set(df.columns)
        if missing:
            raise ValueError(f"OHLC missing after normalization: {missing}")

    except Exception as e:
        raise ValueError(f"Yahoo historical fetch failed: {e}")

    # ---------------------------------------------------
    # 3️⃣ APPLY INDICATORS
    # ---------------------------------------------------
    config = {"indicators": {
        "rsi": True, "macd": True, "bollinger": False,
        "supertrend": True, "adx": False, "atr": True
    }}

    df = apply_indicators(df, config)

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    price = live_price   # overwrite OHLC close with REAL NSE price
    change = price - prev["close"]
    pct = (change / prev["close"]) * 100

    rsi = next((latest[c] for c in latest.index if c.lower().startswith("rsi")), None)
    atr = latest.get("atr_14")
    st = latest.get("supertrend_7_dir")

    trend = "Bullish 🟢" if st and rsi and rsi > 50 else "Bearish 🔴"

    support = price - atr if atr else None
    resistance = price + atr if atr else None

    confidence = 0
    if rsi:
        confidence += min(max((rsi - 50) * 2, 0), 30)
    if st:
        confidence += 40
    if abs(pct) > 0.4:
        confidence += 10
    if atr:
        confidence += 20
    confidence = min(100, int(confidence))

    return {
        "price": round(price, 2),
        "change_abs": round(change, 2),
        "change_pct": round(pct, 2),
        "trend": trend,
        "rsi": round(rsi, 2) if rsi else None,
        "atr": round(atr, 2) if atr else None,
        "support": round(support, 2) if support else None,
        "resistance": round(resistance, 2) if resistance else None,
        "confidence": confidence
    }


# ------------------------------------------
# Telegram Formatter
# ------------------------------------------
def format_nifty_overview_text(data):
    return (
        f"📊 <b>NIFTY Overview</b>\n\n"
        f"Price: {data['price']} "
        f"({data['change_abs']} / {data['change_pct']}%)\n"
        f"Trend: {data['trend']}\n\n"
        f"• Support: {data['support']}\n"
        f"• Resistance: {data['resistance']}\n\n"
        f"⚡ ATR: {data['atr']}\n"
        f"RSI: {data['rsi']}\n"
        f"Confidence Score: <b>{data['confidence']}%</b>"
    )


# ------------------------------------------
# Telegram Handler
# ------------------------------------------
async def send_nifty_overview(update, context):
    query = update.callback_query
    try:
        data = fetch_nifty_data()
        text = format_nifty_overview_text(data)



        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=market_menu_keyboard()
        )
    except Exception as e:
        print("NIFTY Handler Error:", e)
        await query.edit_message_text(
            "❌ Unable to fetch NIFTY Overview.\nPlease try again later.",
            parse_mode="HTML",
            reply_markup = market_menu_keyboard())
