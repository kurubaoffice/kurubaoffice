### news_intelligence/event_ingestors/econ_calendar.py
import requests
from datetime import datetime


def fetch_economic_calendar():
# Example mock — replace with TradingEconomics API or Investing.com scraper
return [
{
"category": "Macroeconomic",
"source": "TradingEconomics",
"title": "US CPI Release",
"description": "CPI came at 3.2% vs forecast 3.0%",
"region": "US",
"impact_level": "High",
"event_time": datetime.utcnow(),
}
]