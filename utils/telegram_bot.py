import os
import pandas as pd
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

from reporting.report_stock_summary import run_pipeline_for_symbol
from reporting.report_nifty_analysis import analyze_nifty
from reporting.report_single_stock import analyze_single_stock
# from logs.logger import log_request  # PostgreSQL logging function (removed)

# CSV path for symbol resolution
CSV_PATH = r"C:\Users\KK\PycharmProjects\Tidder2.0\data\raw\listed_companies.csv"

# Load environment variables
load_dotenv()
token = os.getenv("TELEGRAM_TOKEN")


# --- SYMBOL RESOLUTION ---
def resolve_symbol(user_input: str):
    user_input = user_input.strip().upper()
    try:
        df = pd.read_csv(CSV_PATH)
        df["symbol"] = df["symbol"].astype(str).str.upper()
        df["name"] = df["name"].astype(str).str.upper()

        if user_input in df["symbol"].values:
            return user_input

        match = df[df["name"].str.contains(user_input)]
        if not match.empty:
            return match.iloc[0]["symbol"]

        return None
    except Exception as e:
        print(f"[ERROR] Symbol resolution failed for '{user_input}': {e}")
        return None


# --- /start and /help handlers ---
async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    # log_request(chat_id, "/start", status="received")  # Removed logging

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
    # log_request(chat_id, "/help", status="received")  # Removed logging

    msg = (
        "📖 *Bot Help Menu*\n\n"
        "You can:\n"
        "➡️ `/stock TCS` – Analyze a stock\n"
        "➡️ `nifty50` – Analyze the NIFTY 50 index\n"
        "➡️ Type any NSE-listed company name or symbol to get a report\n"
    )
    await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")


# --- Main message handler ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()

    if not text:
        return

    # log_request(chat_id, text, status="received")  # Removed logging
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    # NIFTY 50 analysis
    if text.strip().lower() == "nifty50":
        # log_request(chat_id, "nifty50_analysis", status="started")  # Removed logging
        await context.bot.send_message(chat_id=chat_id, text="📊 Running NIFTY 50 analysis...")
        try:
            report = analyze_nifty(for_telegram=True)
            chunks = split_message(report)
            for chunk in chunks:
                await context.bot.send_message(chat_id=chat_id, text=chunk)
            # log_request(chat_id, "nifty50_analysis", status="completed")  # Removed logging
        except Exception as e:
            print(f"[ERROR] NIFTY50 analysis failed: {e}")
            # log_request(chat_id, "nifty50_analysis", status="failed")  # Removed logging
            await context.bot.send_message(chat_id=chat_id, text=f"❌ Failed to analyze NIFTY50: {e}")
        return

    # Stock analysis
    symbol = resolve_symbol(text)
    if not symbol:
        # log_request(chat_id, f"symbol_not_found: {text}", status="failed")  # Removed logging
        await context.bot.send_message(chat_id=chat_id, text="❌ Company not found. Please check the name or symbol.")
        return

    # log_request(chat_id, f"stock_analysis:{symbol}", status="started")  # Removed logging
    await context.bot.send_message(chat_id=chat_id, text=f"🔍 Processing {symbol}...")

    try:
        success, report = run_pipeline_for_symbol(symbol, chat_id)
        if success and report:
            chunks = split_message(report)
            for chunk in chunks:
                await context.bot.send_message(chat_id=chat_id, text=chunk)
            # log_request(chat_id, f"stock_analysis:{symbol}", status="completed")  # Removed logging
            return

        report = analyze_single_stock(symbol)
        chunks = split_message(report)
        for chunk in chunks:
            await context.bot.send_message(chat_id=chat_id, text=chunk)
        # log_request(chat_id, f"stock_analysis:{symbol}", status="completed")  # Removed logging

    except Exception as e:
        print(f"[ERROR] Analysis failed for {symbol}: {e}")
        # log_request(chat_id, f"stock_analysis:{symbol}", status="failed")  # Removed logging
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Failed to generate report for '{symbol}'")


# --- Utility: Split long messages ---
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


# --- Entry point ---
def main():
    try:
        app = ApplicationBuilder().token(token).build()
        app.add_handler(CommandHandler("start", handle_start))
        app.add_handler(CommandHandler("help", handle_help))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        print("🤖 Telegram bot starting...")
        app.run_polling()
    except Exception as e:
        print(f"[CRITICAL] Bot failed to start: {e}")


if __name__ == "__main__":
    main()
