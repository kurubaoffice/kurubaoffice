import os
import pandas as pd
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

from reporting.report_stock_summary import run_pipeline_for_symbol
from reporting.report_nifty_analysis import analyze_nifty
from reporting.report_single_stock import analyze_single_stock
from utils.nlp_utils import extract_intent_and_symbol  # import NLP function

CSV_PATH = r"C:\Users\KK\PycharmProjects\Tidder2.0\data\raw\listed_companies.csv"

load_dotenv()
token = os.getenv("TELEGRAM_TOKEN")

# Load company list once on start
company_df = pd.read_csv(CSV_PATH)

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    msg = (
        "👋 *Welcome to Tidder Bot!*\n\n"
        "You can:\n"
        "📊 Get stock analysis — just type a stock symbol like `TCS`, `RELIANCE`\n"
        "📈 Or type `nifty50` to get index & top stocks\n\n"
        "ℹ️ Use /help for details"
    )
    await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")

async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    msg = (
        "📖 *Bot Help Menu*\n\n"
        "You can:\n"
        "➡️ `/stock TCS` – Analyze a stock\n"
        "➡️ `nifty50` – Analyze the NIFTY 50 index\n"
        "➡️ Type any NSE-listed company name or symbol to get a report\n"
    )
    await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()

    if not text:
        return

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    if text.lower() == "nifty50":
        await context.bot.send_message(chat_id=chat_id, text="📊 Running NIFTY 50 analysis...")
        try:
            report = analyze_nifty(for_telegram=True)
            for chunk in split_message(report):
                await context.bot.send_message(chat_id=chat_id, text=chunk)
        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ Failed to analyze NIFTY50: {e}")
        return

    # Use NLP to extract intent and symbol
    intent, symbol = extract_intent_and_symbol(text, company_df)

    if not symbol:
        await context.bot.send_message(chat_id=chat_id, text="❌ Could not detect a company symbol or name in your query.")
        return

    await context.bot.send_message(chat_id=chat_id, text=f"🔍 Processing {symbol} for intent '{intent}'...")

    try:
        success, report = run_pipeline_for_symbol(symbol, chat_id)
        if success and report:
            for chunk in split_message(report):
                await context.bot.send_message(chat_id=chat_id, text=chunk)
            return

        # Fallback single stock analysis
        report = analyze_single_stock(symbol)
        for chunk in split_message(report):
            await context.bot.send_message(chat_id=chat_id, text=chunk)

    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Failed to generate report for '{symbol}': {e}")

def split_message(text, max_length=4000):
    lines = text.split("\n")
    chunks, chunk = [], ""
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
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(CommandHandler("help", handle_help))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🤖 Telegram bot starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
