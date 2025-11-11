import requests

MCP_URL = "http://localhost:8080/api/query"  # replace with your MCP endpoint

def get_mcp_enrichment(symbol: str):
    """Safely fetch company info + latest news from MCP server."""
    try:
        payload = {"type": "stock_enrichment", "symbol": symbol}
        resp = requests.post(MCP_URL, json=payload, timeout=9)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"[MCP] Error fetching enrichment for {symbol}: {e}")
    return {}
