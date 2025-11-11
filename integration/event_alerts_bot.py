### integration/event_alerts_bot.py
import os
from telegram import Bot


TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_ALERTS_CHAT_ID")


bot = Bot(token=TELEGRAM_TOKEN)


def send_event_alert(event):
msg = f"""
📢 [{event['category']}] Alert - {event['impact_level']}


🗓 {event['event_time'].strftime("%d %b %Y %H:%M")}
🌍 Region: {event['region'] or 'Global'}
📊 Event: {event['title']}
📌 Source: {event['source']}
📝 {event['description'] or ''}
"""
bot.send_message(chat_id=CHAT_ID, text=msg.strip())