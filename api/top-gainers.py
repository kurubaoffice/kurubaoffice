import pandas as pd

BASE_DIR = "data/raw"
company_df = pd.read_csv(f"{BASE_DIR}/listed_companies.csv")

@app.get("/top-gainers")
def top_gainers(limit: int = 10):
    companies = []
    for _, row in company_df.iterrows():
        symbol = row["symbol"] + ".NS"
        try:
            ticker = yf.Ticker(symbol)
            price = ticker.info.get("regularMarketPrice")
            previous = ticker.info.get("previousClose")
            change = round(((price - previous) / previous) * 100, 2) if price and previous else 0
            companies.append({"symbol": row["symbol"], "name": row["name"], "change": change})
        except:
            continue
    companies.sort(key=lambda x: x["change"], reverse=True)
    return companies[:limit]

@app.get("/top-losers")
def top_losers(limit: int = 10):
    companies = top_gainers(limit=100)  # get all first
    companies.sort(key=lambda x: x["change"])  # sort ascending
    return companies[:limit]
