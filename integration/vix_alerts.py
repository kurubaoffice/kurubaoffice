# vix_alerts.py
from telegram import Bot
from vol_strategies import analyze_vix_and_nifty

BOT_TOKEN = 'PASTE_YOUR_TOKEN'
CHAT_ID = 'YOUR_CHAT_ID'

bot = Bot(BOT_TOKEN)


def send_vix_alert():
    out = analyze_vix_and_nifty()
    regime = out['regime']
    v = out['vix']['v']
    msg = f"VIX Alert — regime: {regime}\nVIX: {v:.2f}\nNIFTY: {out['nifty_close']:.0f}\nSuggestions:\n"
    for s in out['suggestions']:
        msg += f"- {s['strategy']}: {s['notes']}\n"
    bot.send_message(chat_id=CHAT_ID, text=msg)


if __name__ == '__main__':
    send_vix_alert()