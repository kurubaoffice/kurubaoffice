from fastapi import FastAPI
import yfinance as yf

app = FastAPI()

MARKET_SYMBOLS = {
    "nifty50": "^NSEI",
    "sensex": "^BSESN",
}

@app.get("/market")
def get_market_data():
    data = {}
    for name, symbol in MARKET_SYMBOLS.items():
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            price = info.get("regularMarketPrice")
            previous = info.get("previousClose")
            change = round(((price - previous) / previous) * 100, 2) if price and previous else 0.0
            data[name] = {"price": price, "change": change}
        except Exception as e:
            data[name] = {"price": None, "change": None}
    return data
