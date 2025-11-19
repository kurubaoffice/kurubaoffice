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




import asyncio
#from services.zerodha_oi import ZerodhaOIService
# add these imports near other imports
from compute.options.option_rr_scanner import get_expiry_menu_and_state, process_option_rr_telegram, parse_tg_input

load_dotenv()
# pending expiry selection state per chat
# structure: { chat_id: {"message_text": original_user_text, "state": state_dict_from_scanner, "timestamp": datetime } }
pending_expiry = {}

CSV_PATH = r"C:\Users\KK\PycharmProjects\Tidder2.0\data\raw\listed_companies.csv"
company_df = pd.read_csv(CSV_PATH)

token = os.getenv("TELEGRAM_TOKEN")
from compute.options.option_rr_scanner import process_option_rr_telegram
import asyncio
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
        "➡️ `/bnf_oc` – Analyze the BANK NIFTY index Option\n"
        "➡️ `STOCKNAME-CE` – Eg: TCS-CE will give Current month CE Option\n"
        "➡️ `STOCKNAME-PE` – Eg: TCS-CE will give Current month PE Option\n"
        "➡️ `STOCKNAME-CEPE` – Eg: TCS-CEPE will give Current month CE & PE Option\n"
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

import calendar
from datetime import datetime

MONTH_MAP = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12
}

def parse_option_input(text):
    """
    Supports:
        RELIANCE-CE
        RELIANCE-PE
        RELIANCE-CEPE
        RELIANCE-CE-DEC
        RELIANCE-PE-NOV
        RELIANCE-CE-25APR
    """

    text = text.upper().replace(" ", "")

    pattern = r"([A-Z]{2,20})-(CE|PE|CEPE)(?:-(\d{2})?([A-Z]{3}))?$"
    m = re.match(pattern, text)

    if not m:
        return None

    stock, opt_type, day, month_str = m.groups()

    today = datetime.today()

    # Determine expiry
    if month_str:
        month = MONTH_MAP.get(month_str)
        year = today.year

        if month < today.month:
            year += 1

        if day:
            expiry = datetime(year, month, int(day))
        else:
            # Monthly expiry → last Thursday
            expiry = get_monthly_expiry(year, month)

    else:
        # No month specified → nearest weekly expiry
        expiry = get_nearest_expiry(today)

    return {
        "stock": stock,
        "type": opt_type,
        "expiry": expiry.strftime("%Y-%m-%d")
    }


def get_monthly_expiry(year, month):
    last_day = datetime(year, month, calendar.monthrange(year, month)[1])
    while last_day.weekday() != 3:  # Thursday
        last_day = last_day.replace(day=last_day.day - 1)
    return last_day


def get_nearest_expiry(date):
    while date.weekday() != 3:  # Thursday
        date = date.replace(day=date.day + 1)
    return date

# ────────────────────────────────────────────
# 🔹 Main Message Handler
# ────────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    text_raw = update.message.text.strip()
    text = text_raw.upper()

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    # --- Numeric selection handling (if user replies with '1', '2', etc. to choose expiry) ---
    if re.fullmatch(r"\d{1,3}", text.strip()):
        if chat_id in pending_expiry:
            idx = int(text.strip()) - 1
            saved = pending_expiry.pop(chat_id, None)
            if not saved:
                await context.bot.send_message(chat_id=chat_id, text="⚠️ Session expired. Please resend the stock command.")
                return

            original_user_text = saved["message_text"]
            expiries = saved["state"]["expiries"]
            if idx < 0 or idx >= len(expiries):
                await context.bot.send_message(chat_id=chat_id, text=f"❌ Invalid choice. Please send a number between 1 and {len(expiries)}.")
                return

            # Run the scan for the selected expiry (idx)
            await context.bot.send_message(chat_id=chat_id, text=f"📥 Running scan for expiry *{expiries[idx]}* …", parse_mode="Markdown")
            try:
                result = await process_option_rr_telegram(original_user_text, expiry_selection=idx, desired_rr=2.0)
                await context.bot.send_message(chat_id=chat_id, text=result, parse_mode="Markdown")
            except Exception as e:
                await context.bot.send_message(chat_id=chat_id, text=f"❌ Option scan failed: {e}")
            return

    # ───────────────────────────────
    # Option RR Scan Detection
    # ───────────────────────────────
    # Matches: ICICIBANK-CE / ICICIBANKCE / RELIANCE4200CE / SBIN24JANPE etc.
    parsed = parse_option_input(text)

    if parsed:
        stock = parsed["stock"]
        opt_type = parsed["type"]
        expiry = parsed["expiry"]

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"📥 Fetching {stock} {opt_type} for expiry *{expiry}*…",
            parse_mode="Markdown"
        )

        try:
            # Build formatted command for RR scanner
            rr_query = f"{stock}-{opt_type}-{expiry}"
            result = await process_option_rr_telegram(rr_query)
            await context.bot.send_message(chat_id=chat_id, text=result, parse_mode="Markdown")
        except Exception as e:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ Option scan failed:\n`{e}`",
                parse_mode="Markdown"
            )
        return

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
# 🔹 BankNifty Option Chain Command
# ────────────────────────────────────────────

from fetcher.fetch_banknifty_option_chain import fetch_banknifty_option_chain
from compute.options.strike_selector import pick_best_ce_pe
from reporting.report_option_summary_html import build_option_alert_html

async def handle_bnf_oc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    await context.bot.send_message(chat_id=chat_id, text="📥 Fetching BankNifty Option Chain...")

    try:
        # Fetch ONLY ONCE
        oc_df = fetch_banknifty_option_chain()

        if oc_df is None or oc_df.empty:
            await context.bot.send_message(chat_id=chat_id, text="❌ Could not fetch option chain (empty).")
            return

        # Extract spot
        try:
            spot = float(oc_df["spot"].iloc[0])
        except:
            await context.bot.send_message(chat_id=chat_id, text="⚠ Error: spot price missing in data.")
            return

        # Get best CE & PE
        picks = pick_best_ce_pe(oc_df, spot)

        # Build summary HTML
        html = build_option_alert_html(picks, oc_df, spot)

        await context.bot.send_message(chat_id=chat_id, text=html, parse_mode="HTML")

    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"⚠ Error: {e}")


async def handle_bnf_live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id=chat_id, text="📥 Fetching BANKNIFTY live from Zerodha...")

    try:
        # call Zerodha in a thread to avoid blocking event loop
        def _fetch():
            zs = ZerodhaOIService()
            df, spot = zs.fetch_option_chain()
            return df, spot

        oc_df, spot = await asyncio.to_thread(_fetch)

        if oc_df is None or oc_df.empty:
            await context.bot.send_message(chat_id=chat_id, text="❌ Zerodha returned empty option chain.")
            return

        # reuse your existing pipeline: pick_best_ce_pe and build_option_alert_html
        picks = pick_best_ce_pe(oc_df, float(spot))
        html = build_option_alert_html(picks, oc_df, float(spot), trend_text="Live Zerodha feed")
        await context.bot.send_message(chat_id=chat_id, text=html, parse_mode="HTML")

    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"⚠ Zerodha live error: {e}")


async def handle_user_message(update, context):
    text = update.message.text.strip()

    # Detect option RR scan request
    if "-CE" in text.upper() or "-PE" in text.upper():
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(process_option_rr_telegram(text))
        update.message.reply_text(result, parse_mode="Markdown")
        await update.message.reply_text("⏳ Scanning option chain… please wait 2–5 seconds…")

        try:
            formatted = await process_option_rr_telegram(text)
            await update.message.reply_text(formatted, parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Error: {e}")
        return

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
    app.add_handler(CommandHandler("bnf_oc", handle_bnf_oc))
    app.add_handler(CommandHandler("bnf_live", handle_bnf_live))

    print("🤖 Tidder Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
