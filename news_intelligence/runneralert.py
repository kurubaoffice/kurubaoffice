### Example runner (could be placed in a script under /news_intelligence)
from news_intelligence.event_ingestors.econ_calendar import fetch_economic_calendar
from news_intelligence.event_processor import normalize_event
from news_intelligence.event_dispatcher import process_and_dispatch


raw_events = fetch_economic_calendar()
normalized = [normalize_event(e) for e in raw_events]
process_and_dispatch(normalized)