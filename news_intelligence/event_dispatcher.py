### news_intelligence/event_dispatcher.py
from storage.db_ops import save_event
from integration.event_alerts_bot import send_event_alert


def process_and_dispatch(events):
for e in events:
event_id = save_event(e)
send_event_alert(e)