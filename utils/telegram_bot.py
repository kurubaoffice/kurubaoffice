import os
import re
import pandas as pd
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio
from reporting.report_stock_summary import run_pipeline_for_symbol
from reporting.report_nifty_analysis import analyze_nifty
from reporting.report_single_stock import analyze_single_stock
from utils.nlp_utils import extract_intent_and_symbol
from utils.subscription_utils import can_user_request, log_user_request, get_user_usage
from integration.mcp_client import get_mcp_enrichment





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
        "➡️ Give stock code (Ex: TCS )  – Analyze a stock\n"
        "➡️ `nifty50` – Analyze the NIFTY 50 index\n"
        "➡️ `marubozu` – Uptrend stocks\n"
        "➡️ `RSID` – RSI divergence scan\n"
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
    text = update.message.text.strip().upper()

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

        # ───────────────────────────────
    # Daily limit check
    # ───────────────────────────────
    if not can_user_request(user_id):
        await context.bot.send_message(
            chat_id=chat_id,
            text="🚫 You've reached your *daily free limit* (3 requests).\n\nUpgrade with `/subscribe` to unlock unlimited access.",
            parse_mode="Markdown"
        )
        return

    log_user_request(user_id)

    # ───────────────────────────────
    # NIFTY50 Command
    # ───────────────────────────────
    if text == "NIFTY50":
        await context.bot.send_message(chat_id=chat_id, text="📊 Running NIFTY 50 analysis...")
        try:
            report = analyze_nifty(for_telegram=True)
            for chunk in split_message(report):
                await context.bot.send_message(chat_id=chat_id, text=chunk)
        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ Failed to analyze NIFTY50: {e}")
        return

    # ───────────────────────────────
    # NLP intent + stock analysis
    # ───────────────────────────────
    intent, symbol = extract_intent_and_symbol(text, company_df)

    if not symbol:
        await context.bot.send_message(chat_id=chat_id, text="❌ Could not detect a valid company name or symbol.")
        return

    await context.bot.send_message(chat_id=chat_id, text=f"🔍 Processing `{symbol}` for intent '{intent}'...", parse_mode="Markdown")

    try:
        success, report = run_pipeline_for_symbol(symbol, chat_id)
        if success and report:
            # 💡 MCP Enrichment before sending to Telegram
            enriched_report = enrich_with_mcp(report, symbol)
            for chunk in split_message(enriched_report):
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


def enrich_with_mcp(report: str, symbol: str, chat_id=None, bot=None, max_news=5) -> str:
    """Append MCP-provided info/news to the report and optionally send top headlines to Telegram."""
    data = get_mcp_enrichment(symbol)
    if not data:
        return report

    # Add company info
    info = data.get("company_info", {})
    if info:
        company_block = (
            f"🏢 *{info.get('name', symbol)}*\n"
            f"Sector: {info.get('sector', '—')}\n"
            f"Market Cap: {info.get('market_cap', '—')}\n\n"
        )
        report = company_block + report

    # Add latest news
    news_items = data.get("news", [])
    if news_items:
        news_block = "🗞 *Latest News:*"
        for n in news_items[:5]:
            # Remove any URL at the end
            n_clean = re.sub(r"\s*\(https?://.*\)", "", n)  # removes "(https://...)"
            n_clean = n_clean.lstrip("• ").strip()  # remove any leading bullet or spaces
            news_block += f"\n- {n_clean}\n"
        report += "\n\n" + news_block

    # Send top 3 headlines to Telegram if bot is provided
    if chat_id and bot and news_items:
        top_headlines = []
        for n in news_items[:3]:
            match = re.match(r"^\s*•?\s*(.*?)\s*-\s*(https?://.*)", n)
            if match:
                headline, url = match.groups()
                top_headlines.append(f"• [{headline}]({url})")
            else:
                top_headlines.append(f"• {n.strip()}")
        asyncio.create_task(
            bot.send_message(
                chat_id=chat_id,
                text=f"🗞 *Top MCP News for {symbol}:*\n" + "\n".join(top_headlines),
                parse_mode="Markdown"
            )
        )

    return report


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
