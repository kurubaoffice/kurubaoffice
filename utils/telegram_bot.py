# telegram_bot.py
import os
import pandas as pd
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

from reporting.report_stock_summary import run_pipeline_for_symbol
from reporting.report_nifty_analysis import analyze_nifty
from reporting.report_single_stock import analyze_single_stock
from logs.logger import req_logger, err_logger, fetch_logger

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
        err_logger.error(f"Symbol resolution failed for '{user_input}': {e}", exc_info=True)
        return None


# --- /start and /help handlers ---
async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    req_logger.info(f"/start command received (ChatID={chat_id})")

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
    req_logger.info(f"/help command received (ChatID={chat_id})")

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

    req_logger.info(f"Message received (ChatID={chat_id}): '{text}'")

    if not text:
        return

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    # Command handling
    if text.lower() == "/start":
        await handle_start(update, context)
        return

    if text.lower() == "/help":
        await handle_help(update, context)
        return

    # NIFTY 50 analysis
    if text.strip().lower() == "nifty50":
        await context.bot.send_message(chat_id=chat_id, text="📊 Running NIFTY 50 analysis...")
        fetch_logger.info(f"Running NIFTY 50 analysis (ChatID={chat_id})")
        try:
            report = analyze_nifty(for_telegram=True)
            chunks = split_message(report)
            for chunk in chunks:
                await context.bot.send_message(chat_id=chat_id, text=chunk)
        except Exception as e:
            err_logger.error(f"NIFTY50 analysis failed (ChatID={chat_id}): {e}", exc_info=True)
            await context.bot.send_message(chat_id=chat_id, text=f"❌ Failed to analyze NIFTY50: {e}")
        return

    # Stock analysis
    symbol = resolve_symbol(text)
    if not symbol:
        err_logger.warning(f"Company not found: '{text}' (ChatID={chat_id})")
        await context.bot.send_message(chat_id=chat_id, text="❌ Company not found. Please check the name or symbol.")
        return

    await context.bot.send_message(chat_id=chat_id, text=f"🔍 Processing {symbol}...")
    fetch_logger.info(f"Fetching data for {symbol} (ChatID={chat_id})")

    try:
        # First try full pipeline (NIFTY50 stocks)
        success, report = run_pipeline_for_symbol(symbol, chat_id)
        if success and report:
            chunks = split_message(report)
            for chunk in chunks:
                await context.bot.send_message(chat_id=chat_id, text=chunk)
            return

        # Fallback to general stock analysis
        report = analyze_single_stock(symbol)
        chunks = split_message(report)
        for chunk in chunks:
            await context.bot.send_message(chat_id=chat_id, text=chunk)

    except Exception as e:
        err_logger.error(f"Analysis failed for {symbol} (ChatID={chat_id}): {e}", exc_info=True)
        try:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ Failed to generate report for '{symbol}'")
        except Exception as final_err:
            err_logger.critical(f"Failed to send error message (ChatID={chat_id}): {final_err}", exc_info=True)


# --- Utility: Split long messages ---
def split_message(text, max_length=4000):
    lines = text.split("\n")
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


# --- Entry point ---
def main():
    try:
        app = ApplicationBuilder().token(token).build()

        app.add_handler(CommandHandler("start", handle_start))
        app.add_handler(CommandHandler("help", handle_help))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        req_logger.info("🤖 Telegram bot starting...")
        app.run_polling()
    except Exception as e:
        err_logger.critical(f"Bot failed to start: {e}", exc_info=True)


if __name__ == "__main__":
    main()
