from compute.options.fno_list import get_fno_symbols
from fetcher.fetch_price_data import fetch_price_for_symbol

def fetch_fno_snapshot():
    """
    Fetch live FnO snapshot for all symbols from NSE.
    Returns a list of dicts with:
    - symbol
    - ltp
    - change_pct
    - open interest (oi)
    - implied volatility (iv)
    """
    symbols = get_fno_symbols()
    snapshot = []

    for symbol in symbols:
        data = fetch_price_for_symbol(symbol)
        if not data:
            # Log missing or failed fetch
            print(f"Warning: Failed to fetch data for {symbol}")
            continue

        snapshot.append({
            "symbol": symbol,
            "ltp": float(data.get("last_price", 0)),
            "change_pct": float(data.get("pChange", 0)),
            "oi": float(data.get("openInterest", 0)),
            "iv": float(data.get("impliedVolatility", 0)),
        })

    return snapshot
