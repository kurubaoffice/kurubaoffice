# fetch_india_vix.py
"""
Reliable India VIX Fetcher for Tidder 2.0
Uses NSE's official allIndices API.
Handles cookies, user-agent, retries.
Returns:
{
    'vix': float,
    'change': float,
    'percent_change': float,
    'timestamp': 'YYYY-MM-DD HH:MM:SS'
}
"""

import requests
from requests.exceptions import RequestException
from datetime import datetime
import time

NSE_URL = "https://www.nseindia.com/api/allIndices"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "*/*",
    "Connection": "keep-alive"
}


def fetch_india_vix(retries=3, timeout=5):
    """
    Fetches India VIX from NSE's allIndices endpoint.
    Returns dict with last price, change, percent change.
    """
    session = requests.Session()
    session.headers.update(HEADERS)

    # Step 1 — Hit homepage to get cookies
    try:
        session.get("https://www.nseindia.com", timeout=timeout)
    except Exception:
        pass  # homepage may block but cookies still get set

    # Step 2 — Try API with retries
    for _ in range(retries):
        try:
            resp = session.get(NSE_URL, timeout=timeout)
            if resp.status_code == 200:
                data = resp.json().get("data", [])

                for idx in data:
                    if idx.get("index") == "INDIA VIX":
                        return {
                            "vix": float(idx.get("last", 0)),
                            "change": float(idx.get("change", 0)),
                            "percent_change": float(idx.get("pChange", 0)),
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }

                raise ValueError("INDIA VIX not found in NSE response")

        except RequestException:
            time.sleep(1)

    raise ConnectionError("Failed to fetch India VIX from NSE after retries.")


if __name__ == "__main__":
    print(fetch_india_vix())
