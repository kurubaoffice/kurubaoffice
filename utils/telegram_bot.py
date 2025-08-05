from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

import pandas as pd
import os
from dotenv import load_dotenv


from reporting.report_nifty_analysis import analyze_nifty
from reporting.report_stock_summary import run_pipeline_for_symbol

load_dotenv()
token = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

from utils.helpers import get_project_root

CSV_PATH = get_project_root() / "data" / "raw" / "listed_companies.csv"
print(f"[DEBUG] Looking for CSV at: {CSV_PATH}")


def resolve_symbol_from_name(name):
    try:
        df = pd.read_csv(CSV_PATH)
        match = df[df['name'].str.contains(name, case=False, na=False)]

        if not match.empty:
            return match.iloc[0]["symbol"]
        else:
            print(f"[WARN] No match found for: {name}")
            return None

    except Exception as e:
        print(f"[ERROR] While resolving symbol: {e}")
        return None

def resolve_symbol(user_input):
    user_input = user_input.strip().upper()

    try:
        df = pd.read_csv(CSV_PATH)
        df["symbol"] = df["symbol"].astype(str).str.upper()
        df["name"] = df["name"].astype(str).str.upper()

        # Check if input matches symbol
        if user_input in df["symbol"].values:
            return user_input

        # Check if input matches company name
        match = df[df["name"].str.contains(user_input)]
        if not match.empty:
            return match.iloc[0]["symbol"]

        return None
    except Exception as e:
        print(f"[ERROR] While resolving symbol: {e}")
        return None

# ---- NEW: Async /start and /help handlers ----

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    msg = (
        "👋 *Welcome to Tidder Bot!*\n\n"
        "I can help you with:\n"
        "📈 Stock analysis – /stock ICICIBANK\n"
        "🔎 Just type a stock symbol, or try /help to see what I can do!"
    )
    await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")

async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    msg = (
        "📖 *Bot Help Menu*\n\n"
        "Here’s what you can ask me:\n"
        "➡️ /stock TCS – Get technical analysis of a stock\n"
        "➡️ /health – Check if bot is running\n"
        "➡️ Just type a stock name like *INFY*, and I’ll analyze it!\n\n"
        "🔁 I respond in real-time with predictions & indicators."
    )
    await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")

# ---- Main handler for all text input ----

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text.strip().upper()

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    if text == "/START":
        await handle_start(update, context)
        return

    if text == "/HELP":
        await handle_help(update, context)
        return

    if text == "NIFTY50":
        await handle_nifty(update, context)
        return

    print(f"📩 Received from {chat_id}: {text}")

    symbol = resolve_symbol(text)
    if not symbol:
        await context.bot.send_message(chat_id=chat_id, text="❌ Company not found. Please check the name or symbol.")
        return

    await context.bot.send_message(chat_id=chat_id, text=f"🔍 Processing {symbol}...")

    success = run_pipeline_for_symbol(symbol, chat_id)
    if success:
        await context.bot.send_message(chat_id=chat_id, text=f"✅ Report sent for {symbol}")
    else:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Failed to generate report for {symbol}")


async def handle_nifty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    message_text = update.message.text.lower()

    await context.bot.send_message(chat_id=chat_id, text="📊 Running *NIFTY 50* analysis, please wait...", parse_mode="Markdown")

    try:
        print("🟨 Running analyze_nifty...")
        report = analyze_nifty(for_telegram=False)
        print("🟩 Report received from analyze_nifty")

        print(f"[DEBUG] Type of report: {type(report)}")
        if isinstance(report, tuple):
            print(f"[DEBUG] Report contents: {report}")
            report = report[0]

        # ❌ Don't send full report
        # await context.bot.send_message(chat_id=chat_id, text=str(report), parse_mode="Markdown")

        # ✅ Split & send in chunks
        chunks = split_message(report)
        for part in chunks:
            await context.bot.send_message(chat_id=chat_id, text=part, parse_mode="Markdown")

    except Exception as e:
        import traceback
        print("[❌ EXCEPTION TRACEBACK]")
        traceback.print_exc()

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ Analysis failed: {e}",
            parse_mode="Markdown"
        )


def split_message(text, max_length=4000):
    """Split long text into multiple parts for Telegram message limits."""
    lines = text.split('\n')
    chunks = []
    chunk = ""

    for line in lines:
        if len(chunk) + len(line) + 1 > max_length:
            chunks.append(chunk)
            chunk = line
        else:
            chunk += "\n" + line

    if chunk:
        chunks.append(chunk)

    return chunks

def main():
    import os
    from dotenv import load_dotenv
    load_dotenv()

    token = os.getenv("TELEGRAM_TOKEN")
    app = ApplicationBuilder().token(token).build()

    # Command handlers
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(CommandHandler("help", handle_help))
    app.add_handler(CommandHandler("nifty", handle_nifty))

    # Message handler
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    print("🤖 Telegram bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()