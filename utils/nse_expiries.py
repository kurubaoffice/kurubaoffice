import httpx
from datetime import datetime

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch_nse_expiries(symbol="BANKNIFTY"):
    """
    Fetch expiry dates directly from NSE option chain API.
    Works reliably, no yfinance dependency.
    """
    url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"

    try:
        with httpx.Client(headers=NSE_HEADERS, timeout=10) as client:
            # step 1: get cookies
            client.get("https://www.nseindia.com", timeout=10)

            # step 2: fetch json
            r = client.get(url)
            data = r.json()

        expiries = data["records"]["expiryDates"]
        # Convert to consistent DD-MMM-YYYY format
        formatted = [
            datetime.strptime(x, "%d-%b-%Y").strftime("%d-%b-%Y").upper()
            for x in expiries
        ]
        return formatted

    except Exception as e:
        raise RuntimeError(f"Failed to fetch NSE expiries: {e}")
