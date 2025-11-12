import logging
from fastapi import FastAPI
from pydantic import BaseModel
import feedparser
import urllib.parse

# ------------------- Logging Setup -------------------
logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for more details
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ------------------- FastAPI App -------------------
app = FastAPI()

class QueryRequest(BaseModel):
    symbol: str

@app.post("/api/query")
def get_news(req: QueryRequest):
    keyword = req.symbol.upper().strip()
    logger.info(f"Received request for symbol: {keyword}")
    results = []

    rss_feeds = [
        f"https://news.google.com/rss/search?q={urllib.parse.quote(keyword)}+stock",
        f"https://news.google.com/rss/search?q={urllib.parse.quote(keyword)}+share+site:moneycontrol.com",
        f"https://feeds.feedburner.com/ndtvprofit-latest",  # NDTV Profit
        f"https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",  # ET Markets
    ]

    seen_titles = set()

    for feed_url in rss_feeds:
        logger.info(f"Parsing feed: {feed_url}")
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
            logger.warning(f"Failed to parse feed {feed_url}: {e}")

    if not results:
        results.append("• No recent news found (—)")

    logger.info(f"Returning {len(results[:5])} news items for {keyword}")
    return {"news": results[:5]}
