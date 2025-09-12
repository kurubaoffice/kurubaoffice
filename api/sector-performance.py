@app.get("/sector-performance")
def sector_performance():
    sector_dict = {}
    for _, row in company_df.iterrows():
        sector = row["sector"] or "Other"
        symbol = row["symbol"] + ".NS"
        try:
            ticker = yf.Ticker(symbol)
            price = ticker.info.get("regularMarketPrice")
            previous = ticker.info.get("previousClose")
            change = round(((price - previous) / previous) * 100, 2) if price and previous else 0
            if sector not in sector_dict:
                sector_dict[sector] = []
            sector_dict[sector].append(change)
        except:
            continue
    result = []
    for sector, changes in sector_dict.items():
        avg_change = round(sum(changes) / len(changes), 2) if changes else 0
        result.append({"name": sector, "performance": avg_change})
    return result
