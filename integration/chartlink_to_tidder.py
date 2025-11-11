import requests

url = "https://chartink.com/screener/process"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Referer": "https://chartink.com/screener/1st-15-min-marubozu",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://chartink.com",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
}

payload = {
    "scan_clause": "( {cash} ( [=-1] 15 minute open = [=-1] 15 minute low and [=-1] 15 minute close = [=-1] 15 minute high and [0] daily close > 100 ) )"
}

r = requests.post(url, headers=headers, data=payload)

print("Status Code:", r.status_code)
print("Content:", r.text[:300])  # preview first 300 chars

if "data" in r.text:
    data = r.json()
    print("\nStocks:")
    for row in data["data"]:
        print(row["nsecode"])
else:
    print("\n⚠️ Looks like Chartink blocked or redirected the request.")
