# modules/utils/telegram_sender.py

import os
import requests
from dotenv import load_dotenv

load_dotenv()
# Hardcoded for now
token = "8057700354:AAHhYwu2naR6ul5YTMQBaI_cO-_PNNDmwRc"
chat_id = "675105848"

BASE_URL = f"https://api.telegram.org/bot{token}"

def send_message(chat_id, message):
    url = f"{BASE_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    response = requests.post(url, data=payload)
    if response.status_code != 200:
        print(f"❌ Failed to send message: {response.text}")
    else:
        print(f"✅ Message sent to chat {chat_id}")
