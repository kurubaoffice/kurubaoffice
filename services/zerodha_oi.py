# services/zerodha_oi.py
from kiteconnect import KiteConnect
import pandas as pd
import os
from typing import Tuple

class ZerodhaOIService:
    """
    Lightweight helper to fetch BANKNIFTY option quotes from Zerodha Kite Connect.
    Returns (oc_df, spot)
    NOTE: requires kiteconnect library and valid API_KEY + ACCESS_TOKEN.
    """

    def __init__(self, api_key: str = None, access_token: str = None):
        api_key = api_key or os.getenv("ZERODHA_API_KEY")
        access_token = access_token or os.getenv("ZERODHA_ACCESS_TOKEN")
        if not api_key or not access_token:
            raise ValueError("ZERODHA_API_KEY and ZERODHA_ACCESS_TOKEN required (env vars).")
        self.kc = KiteConnect(api_key=api_key)
        self.kc.set_access_token(access_token)

    def fetch_option_chain(self, symbol="BANKNIFTY", expiry=None) -> Tuple[pd.DataFrame, float]:
        instruments = self.kc.instruments("NFO")
        # filter instruments for BANKNIFTY options
        instruments = [i for i in instruments if i.get("name") == symbol and i.get("segment") == "NFO-OPT"]
        if not instruments:
            raise RuntimeError("No BANKNIFTY instruments found via Zerodha instruments().")

        # pick expiry (latest if not provided)
        if expiry is None:
            exps = sorted({i["expiry"] for i in instruments})
            expiry = exps[0] if exps else None

        rows = []
        # for each instrument matching expiry
        for inst in instruments:
            if expiry and str(inst.get("expiry")) != str(expiry):
                continue
            token = inst.get("instrument_token")
            if token is None:
                continue
            try:
                quote = self.kc.quote(token)
            except Exception:
                # best-effort: continue if single quote fails
                continue

            # quote payload shape can vary; try to extract
            q = None
            # sometimes the API returns a dict keyed by 'NFO:' + tradingsymbol etc,
            # but kite.quote(token) returns nested dict keyed by token string as well
            if isinstance(quote, dict):
                # try first value
                if str(token) in quote:
                    q = quote[str(token)]
                else:
                    # pick first nested value (best-effort)
                    try:
                        q = next(iter(quote.values()))
                    except StopIteration:
                        q = None

            if q is None:
                continue

            # safe extraction with defaults
            oi = q.get("oi", 0) or 0
            change_oi = q.get("change_in_oi", 0) or q.get("oiChange", 0) or 0
            vol = q.get("volume", 0) or q.get("total_traded_volume", 0) or 0
            iv = q.get("implied_volatility", 0) or q.get("iv", 0) or 0

            # depth: get first bid/ask price if present
            bid = 0.0
            ask = 0.0
            try:
                depth = q.get("depth", {})
                buys = depth.get("buy", [])
                sells = depth.get("sell", [])
                if buys:
                    bid = buys[0].get("price", 0) or 0
                if sells:
                    ask = sells[0].get("price", 0) or 0
            except Exception:
                bid = q.get("depth", {}).get("buy", [{}])[0].get("price", 0) if isinstance(q.get("depth", {}), dict) else 0
                ask = q.get("depth", {}).get("sell", [{}])[0].get("price", 0) if isinstance(q.get("depth", {}), dict) else 0

            rows.append({
                "strike": inst.get("strike"),
                "type": inst.get("instrument_type") or inst.get("option_type") or inst.get("instrument_type"),
                "oi": oi,
                "change_oi": change_oi,
                "volume": vol,
                "iv": iv,
                "lastPrice": q.get("last_price", q.get("lastPrice", 0)) or 0,
                "bid": bid,
                "ask": ask,
                "expiry": inst.get("expiry"),
                "instrument_token": token,
                "spot": None,  # will set below
            })

        # fetch spot (NSE cash quote)
        try:
            spot_quote = self.kc.quote("NSE:" + symbol)
            spot = None
            if isinstance(spot_quote, dict):
                # best-effort extraction
                val = None
                for v in spot_quote.values():
                    if isinstance(v, dict) and v.get("last_price") is not None:
                        val = v.get("last_price")
                        break
                spot = val or 0.0
            else:
                spot = 0.0
        except Exception:
            spot = 0.0

        df = pd.DataFrame(rows)
        if not df.empty:
            df["spot"] = spot
        return df, spot
