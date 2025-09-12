import yfinance as yf
from fastapi import FastAPI, HTTPException
import pandas as pd
import os
from fastapi.middleware.cors import CORSMiddleware
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
import datetime

app = FastAPI()

# CORS setup
origins = ["http://localhost:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load company list
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW_COMPANY_LIST = os.path.join(BASE_DIR, "data", "raw", "listed_companies.csv")
company_df = pd.read_csv(RAW_COMPANY_LIST)


@app.get("/stocks")
def get_stock_list():
    return company_df[["symbol", "name"]].to_dict(orient="records")


@app.get("/stock/{symbol}")
def get_stock(symbol: str):
    symbol = symbol.upper()
    row = company_df[company_df["symbol"] == symbol]
    if row.empty:
        raise HTTPException(status_code=404, detail="Stock not found")

    company = row.iloc[0].to_dict()

    price = day_high = day_low = year_high = year_low = change_percent = None
    volume = avg_volume = None
    history = []

    try:
        yf_symbol = symbol if symbol.endswith(".NS") else symbol + ".NS"
        ticker = yf.Ticker(yf_symbol)
        info = ticker.info

        price = info.get("regularMarketPrice")
        prev_close = info.get("previousClose")
        day_high = info.get("dayHigh")
        day_low = info.get("dayLow")
        year_high = info.get("fiftyTwoWeekHigh")
        year_low = info.get("fiftyTwoWeekLow")
        change_percent = round(((price - prev_close) / prev_close) * 100, 2) if price and prev_close else 0.0

        # Last 14 days historical
        hist = ticker.history(period="14d")
        history = [{"date": str(idx.date()), "close": round(row["Close"], 2)} for idx, row in hist.iterrows()]

        volume = info.get("volume")
        avg_volume = info.get("averageVolume")

    except Exception as e:
        print(f"yfinance failed for {symbol}: {e}")

    return {
        "symbol": company["symbol"],
        "name": company["name"],
        "sector": company.get("sector", ""),
        "marketCap": company.get("market_cap") if pd.notnull(company.get("market_cap")) else None,
        "peRatio": company.get("pe_ratio") if pd.notnull(company.get("pe_ratio")) else None,
        "roe": company.get("roe") if pd.notnull(company.get("roe")) else None,
        "eps": company.get("eps") if pd.notnull(company.get("eps")) else None,
        "promoterHolding": company.get("promoter_holding") if pd.notnull(company.get("promoter_holding")) else None,
        "institutionalHolding": company.get("institutional_holding") if pd.notnull(company.get("institutional_holding")) else None,
        "lastUpdated": company.get("last_updated") if pd.notnull(company.get("last_updated")) else datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "price": price,
        "changePercent": change_percent,
        "dayHigh": day_high,
        "dayLow": day_low,
        "yearHigh": year_high,
        "yearLow": year_low,
        "volume": volume,
        "avgVolume": avg_volume,
        "history": history,
        "indicators": {},
        "insights": []
    }


# --- Helper for concurrent fetching ---
def fetch_symbol_data(symbol):
    try:
        yf_symbol = symbol if symbol.endswith(".NS") else symbol + ".NS"
        ticker = yf.Ticker(yf_symbol)
        info = ticker.info
        price = info.get("regularMarketPrice")
        prev = info.get("previousClose")
        if price is not None and prev is not None:
            change = round(((price - prev) / prev) * 100, 2)
            return {
                "symbol": symbol,
                "name": company_df.loc[company_df["symbol"] == symbol, "name"].values[0],
                "price": price,
                "changePercent": change
            }
    except:
        return None


# ---- Cached market summary for faster dashboard ----
@lru_cache(maxsize=1)
def get_cached_market(limit=10):
    symbols = company_df["symbol"].tolist()
    gainers = []
    losers = []

    # Fetch data concurrently
    with ThreadPoolExecutor(max_workers=15) as executor:
        results = list(executor.map(fetch_symbol_data, symbols))

    results = [r for r in results if r]
    gainers = sorted(results, key=lambda x: x["changePercent"], reverse=True)[:limit]
    losers = sorted(results, key=lambda x: x["changePercent"])[:limit]

    # Sector performance
    sector_perf = []
    for sector in company_df['sector'].dropna().unique():
        sector_symbols = company_df[company_df['sector'] == sector]['symbol'].tolist()
        sector_changes = [r["changePercent"] for r in results if r["symbol"] in sector_symbols]
        if sector_changes:
            sector_perf.append({
                "sector": sector,
                "avgChangePercent": round(sum(sector_changes)/len(sector_changes), 2)
            })

    return {
        "topGainers": gainers,
        "topLosers": losers,
        "sectorPerformance": sector_perf
    }


# ---- API Endpoints ----
@app.get("/market")
def get_market_summary():
    return get_cached_market(limit=5)


@app.get("/top-gainers")
def top_gainers(limit: int = 10):
    return get_cached_market(limit=limit)["topGainers"]


@app.get("/top-losers")
def top_losers(limit: int = 10):
    return get_cached_market(limit=limit)["topLosers"]


@app.get("/sector-performance")
def sector_performance():
    return get_cached_market(limit=5)["sectorPerformance"]
