import os
import pandas as pd
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

from reporting.report_stock_summary import run_pipeline_for_symbol
from reporting.report_nifty_analysis import analyze_nifty
from reporting.report_single_stock import analyze_single_stock
from utils.nlp_utils import extract_intent_and_symbol
from utils.subscription_utils import can_user_request, log_user_request, get_user_usage

load_dotenv()

CSV_PATH = r"C:\Users\KK\PycharmProjects\Tidder2.0\data\raw\listed_companies.csv"
company_df = pd.read_csv(CSV_PATH)

token = os.getenv("TELEGRAM_TOKEN")

# ────────────────────────────────────────────
# 🔹 Commands
# ────────────────────────────────────────────

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "👋 *Welcome to Tidder Bot!*\n\n"
        "You can:\n"
        "📊 Get stock analysis — just type a stock symbol like `TCS`, `RELIANCE`\n"
        "📈 Or type `nifty50` to get index & top stocks\n\n"
        "ℹ️ Use /help for details"
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg, parse_mode="Markdown")

async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "📖 *Bot Help Menu*\n\n"
        "Commands:\n"
        "➡️ `/stock TCS` – Analyze a stock\n"
        "➡️ `nifty50` – Analyze the NIFTY 50 index\n"
        "➡️ `/usage` – Check your request usage\n"
        "➡️ `/subscribe` – Upgrade for unlimited access (coming soon)"
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg, parse_mode="Markdown")

async def handle_usage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    used, limit = get_user_usage(user_id)
    msg = (
        f"📊 You’ve used *{used} / {limit}* free requests today.\n\n"
        "💳 Upgrade with `/subscribe` to unlock unlimited access!"
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg, parse_mode="Markdown")

async def handle_subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "💳 *Tidder Premium Coming Soon!*\n\n"
        "Unlimited analysis, priority access, and more.\n"
        "_This feature is under development._"
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg, parse_mode="Markdown")

# ────────────────────────────────────────────
# 🔹 Main Message Handler
# ────────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    text = update.message.text.strip()

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    # Check limit
    if not can_user_request(user_id):
        await context.bot.send_message(
            chat_id=chat_id,
            text="🚫 You've reached your *daily free limit* (3 requests).\n\nUpgrade with `/subscribe` to unlock unlimited access.",
            parse_mode="Markdown"
        )
        return

    # Log usage
    log_user_request(user_id)

    if text.lower() == "nifty50":
        await context.bot.send_message(chat_id=chat_id, text="📊 Running NIFTY 50 analysis...")
        try:
            report = analyze_nifty(for_telegram=True)
            for chunk in split_message(report):
                await context.bot.send_message(chat_id=chat_id, text=chunk)
        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ Failed to analyze NIFTY50: {e}")
        return

    # NLP intent + symbol
    intent, symbol = extract_intent_and_symbol(text, company_df)

    if not symbol:
        await context.bot.send_message(chat_id=chat_id, text="❌ Could not detect a valid company name or symbol.")
        return

    await context.bot.send_message(chat_id=chat_id, text=f"🔍 Processing `{symbol}` for intent '{intent}'...", parse_mode="Markdown")

    try:
        success, report = run_pipeline_for_symbol(symbol, chat_id)
        if success and report:
            for chunk in split_message(report):
                await context.bot.send_message(chat_id=chat_id, text=chunk)
            return

        # fallback single stock
        report = analyze_single_stock(symbol)
        for chunk in split_message(report):
            await context.bot.send_message(chat_id=chat_id, text=chunk)

    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Error analyzing {symbol}: {e}")

# ────────────────────────────────────────────
# 🔹 Utilities
# ────────────────────────────────────────────

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

# ────────────────────────────────────────────
# 🔹 Main
# ────────────────────────────────────────────

def main():
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(CommandHandler("help", handle_help))
    app.add_handler(CommandHandler("usage", handle_usage))
    app.add_handler(CommandHandler("subscribe", handle_subscribe))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Tidder Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
