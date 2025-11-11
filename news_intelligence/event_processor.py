### news_intelligence/event_processor.py
def normalize_event(raw_event):
# Add extra scoring logic here
return {
"category": raw_event["category"],
"source": raw_event["source"],
"title": raw_event["title"],
"description": raw_event.get("description"),
"region": raw_event.get("region"),
"impact_level": raw_event.get("impact_level", "Medium"),
"event_time": raw_event.get("event_time"),
}