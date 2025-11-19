# bot_main.py
import os
import re
import logging
import pandas as pd
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio
import datetime as dt

from compute.options.rr_parser import parse_tg_input
from compute.options.rr_engine import get_expiry_menu_and_state, process_option_rr_telegram
from compute.options.state_manager import set_pending, pop_pending, get_pending, cleanup_expired
from utils.nlp_utils import extract_intent_and_symbol
from utils.subscription_utils import can_user_request, log_user_request, get_user_usage
from reporting.report_stock_summary import run_pipeline_for_symbol
from reporting.report_nifty_analysis import analyze_nifty
from reporting.report_single_stock import analyze_single_stock
from integration.mcp_client import get_mcp_enrichment



# configuration
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
CSV_PATH = r"C:\Users\KK\PycharmProjects\Tidder2.0\data\raw\listed_companies.csv"
company_df = pd.read_csv(CSV_PATH)
logging.basicConfig(level=logging.INFO)

# constants
REQUEST_RR = 2.0

# helpers
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
    data = get_mcp_enrichment(symbol)
    if not data:
        return report
    info = data.get("company_info", {})
    if info:
        company_block = (
            f"🏢 *{info.get('name', symbol)}*\n"
            f"Sector: {info.get('sector', '—')}\n"
            f"Market Cap: {info.get('market_cap', '—')}\n\n"
        )
        report = company_block + report
    news_items = data.get("news", [])
    if news_items:
        news_block = "🗞 *Latest News:*"
        for n in news_items[:5]:
            n_clean = re.sub(r"\s*\(https?://.*\)", "", n)
            n_clean = n_clean.lstrip("• ").strip()
            news_block += f"\n- {n_clean}\n"
        report += "\n\n" + news_block
    # optional async send of top headlines omitted for clarity
    return report

# -------------------------
# Commands
# -------------------------
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
        "➡️ `/bnf_oc` – Analyze the BANK NIFTY index Option\n"
        "➡️ `STOCKNAME-CE` or `STOCKNAME CE` – show expiry menu for CE\n"
        "➡️ `STOCKNAME-PE` – show expiry menu for PE\n"
        "➡️ `STOCKNAME-CEPE` – show expiry menu for CE & PE\n"
        "➡️ Reply with a number (1/2/3) to pick an expiry from the menu\n"
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg, parse_mode="Markdown")

async def handle_usage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    used, limit = get_user_usage(user_id)
    msg = f"📊 You’ve used *{used} / {limit}* free requests today.\n\nUpgrade with `/subscribe` to unlock unlimited access!"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg, parse_mode="Markdown")

async def handle_subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "💳 *Tidder Premium Coming Soon!*"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg, parse_mode="Markdown")

# -------------------------
# Main message handler
# -------------------------


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # periodic cleanup of stale pending entries
    cleanup_expired()

    if not update.message or not update.message.text:
        return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    text_raw = update.message.text.strip()
    text = text_raw.strip()
    # Handle known commands FIRST (before option detection)
    if text.startswith("/"):
        # allow the CommandHandler to take over
        return

    # quick 'typing' feedback
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    # 1) Numeric reply handling (select expiry)
    if re.fullmatch(r"\d{1,3}", text):
        pending = get_pending(chat_id)
        if not pending:
            await context.bot.send_message(chat_id=chat_id,
                                           text="⚠️ No pending expiry selection. Please send a stock+option command (e.g., TCS-CE).")
            return
        idx = int(text) - 1
        expiries = pending["state"]["expiries"]
        if idx < 0 or idx >= len(expiries):
            await context.bot.send_message(chat_id=chat_id,
                                           text=f"❌ Invalid choice. Please send a number between 1 and {len(expiries)}.")
            return

        # remove pending state (one-shot)
        data = pop_pending(chat_id)

        await context.bot.send_message(chat_id=chat_id, text=f"📥 Running scan for expiry *{expiries[idx]}* …",
                                       parse_mode="Markdown")
        try:
            # If this pending was created by BankNifty flow, call analyze_bnf_for_expiry
            if isinstance(data, dict) and data.get("bnf"):
                expiry = expiries[idx]
                out = await analyze_bnf_for_expiry(expiry)
                for chunk in split_message(out):
                    await context.bot.send_message(chat_id=chat_id, text=chunk)
            else:
                # generic path: run option RR scanner which will use saved message_text
                result = await process_option_rr_telegram(data["message_text"], expiry_selection=idx,
                                                          desired_rr=REQUEST_RR)
                for chunk in split_message(result):
                    await context.bot.send_message(chat_id=chat_id, text=chunk, parse_mode="Markdown")
        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ Option scan failed: {e}")
        return

    # 2) OPTION QUERY DETECTION (STRICT)
    is_option_query = False

    # A) Contains dash → definitely option (TCS-CE, TCS-PE-DEC)
    if "-" in text:
        is_option_query = True

    # B) Contains CE / PE as standalone token
    elif re.search(r"\b(CE|PE)\b", text.upper()):
        is_option_query = True

    # C) Contains month token (DEC / JAN / FEB etc.)
    elif re.search(r"\b(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\b", text.upper()):
        is_option_query = True

    ticker_guess, dtype_guess, expiry_token = parse_tg_input(text)

    if is_option_query and ticker_guess:
        # daily-limit check
        if not can_user_request(user_id):
            await context.bot.send_message(chat_id=chat_id,
                                           text="🚫 You've reached your *daily free limit* (3 requests).",
                                           parse_mode="Markdown")
            return
        log_user_request(user_id)

        # user gave expiry (DEC / 25DEC)
        if expiry_token:
            await context.bot.send_message(chat_id=chat_id,
                                           text=f"📥 Fetching {ticker_guess} {dtype_guess} for expiry *{expiry_token}*…",
                                           parse_mode="Markdown")
            try:
                result = await process_option_rr_telegram(text, expiry_str=expiry_token, desired_rr=REQUEST_RR)
                for chunk in split_message(result):
                    await context.bot.send_message(chat_id=chat_id, text=chunk, parse_mode="Markdown")
            except Exception as e:
                await context.bot.send_message(chat_id=chat_id, text=f"❌ Option RR scan failed: {e}")
            return

        # otherwise: show expiry menu
        try:
            await context.bot.send_message(chat_id=chat_id,
                                           text=f"📥 Fetching available expiries for *{ticker_guess}* …",
                                           parse_mode="Markdown")
            menu_text, state = await get_expiry_menu_and_state(text)
            set_pending(chat_id, {"message_text": text, "state": state})
            await context.bot.send_message(chat_id=chat_id, text=menu_text)
        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ Could not fetch expiries: {e}")
        return

        # otherwise fetch expiries and show menu
        try:
            await context.bot.send_message(chat_id=chat_id, text=f"📥 Fetching available expiries for *{ticker_guess}* …", parse_mode="Markdown")
            menu_text, state = await get_expiry_menu_and_state(text)
            set_pending(chat_id, {"message_text": text, "state": state})
            await context.bot.send_message(chat_id=chat_id, text=menu_text)
        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ Could not fetch expiries: {e}")
        return

    # 3) NIFTY50
    if text.strip().upper() == "NIFTY50":
        await context.bot.send_message(chat_id=chat_id, text="📊 Running NIFTY 50 analysis...")
        try:
            report = analyze_nifty(for_telegram=True)
            for chunk in split_message(report):
                await context.bot.send_message(chat_id=chat_id, text=chunk)
        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ Failed to analyze NIFTY50: {e}")
        return

    # 4) NLP-driven stock analysis
    intent, symbol = extract_intent_and_symbol(text.upper(), company_df)
    if not symbol:
        await context.bot.send_message(chat_id=chat_id, text="❌ Could not detect a valid company name or symbol.")
        return

    # daily limit for general stock analysis
    if not can_user_request(user_id):
        await context.bot.send_message(chat_id=chat_id, text="🚫 You've reached your *daily free limit* (3 requests).", parse_mode="Markdown")
        return
    log_user_request(user_id)

    await context.bot.send_message(chat_id=chat_id, text=f"🔍 Processing `{symbol}` for intent '{intent}'...", parse_mode="Markdown")
    try:
        success, report = run_pipeline_for_symbol(symbol, chat_id)
        if success and report:
            enriched_report = enrich_with_mcp(report, symbol)
            for chunk in split_message(enriched_report):
                await context.bot.send_message(chat_id=chat_id, text=chunk)
            return


        # Fallback single stock
        report = analyze_single_stock(symbol)
        for chunk in split_message(report):
            await context.bot.send_message(chat_id=chat_id, text=chunk)
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Error analyzing {symbol}: {e}")
#----------------------------------
# in bot_main.py: imports (add)
from compute.options.bnf_engine import get_bnf_expiry_menu_and_state, analyze_bnf_for_expiry
from compute.options.state_manager import set_pending, pop_pending, get_pending

# -------------------------
# BankNifty handlers
# -------------------------
async def handle_bnf_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id=chat_id, text="📥 Preparing BankNifty expiries...")
    try:
        menu_text, state = await get_bnf_expiry_menu_and_state()
        # mark state specially so numeric reply will be routed here
        state_update = {"message_text": "BANKNIFTY-CEPE", "state": state, "bnf": True}
        set_pending(chat_id, state_update)
        await context.bot.send_message(chat_id=chat_id, text=menu_text)
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Could not fetch BankNifty expiries: {e}")

async def handle_bnf_ce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id=chat_id, text="📥 Fetching Best BankNifty CE (nearest weekly)...")
    try:
        # auto select nearest weekly (index 0 from menu)
        menu_text, state = await get_bnf_expiry_menu_and_state()
        expiry = state["expiries"][0]
        out = await analyze_bnf_for_expiry(expiry)
        await context.bot.send_message(chat_id=chat_id, text=out, parse_mode=None)
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Error: {e}")

async def handle_bnf_pe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id=chat_id, text="📥 Fetching Best BankNifty PE (nearest weekly)...")
    try:
        menu_text, state = await get_bnf_expiry_menu_and_state()
        expiry = state["expiries"][0]
        out = await analyze_bnf_for_expiry(expiry)
        await context.bot.send_message(chat_id=chat_id, text=out, parse_mode=None)
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Error: {e}")

async def handle_bnf_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id=chat_id, text="📥 Fetching full BankNifty analysis (nearest weekly)...")
    try:
        menu_text, state = await get_bnf_expiry_menu_and_state()
        expiry = state["expiries"][0]
        out = await analyze_bnf_for_expiry(expiry)
        await context.bot.send_message(chat_id=chat_id, text=out, parse_mode=None)
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Error: {e}")


# -------------------------
# Bot running
# -------------------------
def main():
    if not TOKEN:
        raise RuntimeError("TELEGRAM_TOKEN not set in env")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(CommandHandler("help", handle_help))
    app.add_handler(CommandHandler("usage", handle_usage))
    app.add_handler(CommandHandler("subscribe", handle_subscribe))
    app.add_handler(CommandHandler("bnf", handle_bnf_cmd))
    app.add_handler(CommandHandler("bnf_ce", handle_bnf_ce))
    app.add_handler(CommandHandler("bnf_pe", handle_bnf_pe))
    app.add_handler(CommandHandler("bnf_all", handle_bnf_all))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))



    # you can add other command handlers (bnf_oc/bnf_live) if they rely on other modules
    print("🤖 Tidder Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
