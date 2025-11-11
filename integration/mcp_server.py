from fastapi import FastAPI
from pydantic import BaseModel
import feedparser
import urllib.parse

app = FastAPI()

class QueryRequest(BaseModel):
    symbol: str

@app.post("/api/query")
def get_news(req: QueryRequest):
    keyword = req.symbol.upper().strip()
    results = []

    # ---- Feeds (global + India-based) ----
    rss_feeds = [
        f"https://news.google.com/rss/search?q={urllib.parse.quote(keyword)}+stock",
        f"https://news.google.com/rss/search?q={urllib.parse.quote(keyword)}+share+site:moneycontrol.com",
        f"https://feeds.feedburner.com/ndtvprofit-latest",  # NDTV Profit
        f"https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",  # ET Markets
    ]

    seen_titles = set()

    for feed_url in rss_feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]:
                title = entry.get("title", "")
                link = entry.get("link", "")
                if title and title not in seen_titles:
                    if keyword.lower() in title.lower() or "stock" in title.lower():
                        results.append(f"• {title} ({link})")
                        seen_titles.add(title)
        except Exception as e:
            print(f"[WARN] Failed to parse feed {feed_url}: {e}")

    # ---- Fallback ----
    if not results:
        results.append("• No recent news found (—)")

    return {"news": results[:5]}
