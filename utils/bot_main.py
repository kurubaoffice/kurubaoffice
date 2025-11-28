# bot_main.py (CLEAN / FIXED / REWRITE)
import os
import re
import logging
import pandas as pd
from dotenv import load_dotenv
from typing import Optional, Tuple, Dict, Any, List

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# project imports (assume these modules exist in your project)
from compute.options.rr_parser import parse_tg_input
from compute.options.rr_engine import (
    get_expiry_menu_and_state,
    process_option_rr_telegram,
)
from compute.options.bnf_engine import (
    get_bnf_expiry_menu_and_state,
    analyze_bnf_for_expiry,
)
from compute.options.state_manager import (
    set_pending,
    pop_pending,
    get_pending,
    cleanup_expired,
)
from utils.nlp_utils import extract_intent_and_symbol
from utils.subscription_utils import (
    can_user_request,
    log_user_request,
    get_user_usage,
)
from reporting.report_stock_summary import run_pipeline_for_symbol
from reporting.report_nifty_analysis import analyze_nifty
from reporting.report_single_stock import analyze_single_stock
from integration.mcp_client import get_mcp_enrichment

# ---------- config ----------
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
CSV_PATH = r"C:\Users\KK\PycharmProjects\Tidder2.0\data\raw\listed_companies.csv"
if os.path.exists(CSV_PATH):
    company_df = pd.read_csv(CSV_PATH)
else:
    company_df = pd.DataFrame()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger("tidder-bot")

USER_STATE: Dict[int, str] = {}
REQUEST_RR: float = 2.0

# ---------- menus ----------
def ik_main_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("📈 Stock Analysis", callback_data="stock_menu")],
        [InlineKeyboardButton("⚡ Options Analysis", callback_data="opt_menu")],
        [InlineKeyboardButton("📊 Index Tools", callback_data="index_menu")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def ik_persistent() -> InlineKeyboardMarkup:
    # permanent single-button bottom menu
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Menu", callback_data="back_main")]])


def ik_stock_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Analyze Stock", callback_data="stock_analyze")],
        [InlineKeyboardButton("⬅️ Back", callback_data="back_main")]
    ])


def ik_opt_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 Best Strike Finder", callback_data="opt_best")],
        [InlineKeyboardButton("📅 Expiry Scanner", callback_data="opt_expiry")],
        [InlineKeyboardButton("📊 OI Trend", callback_data="opt_oi")],
        [InlineKeyboardButton("⬅️ Back", callback_data="back_main")]
    ])


def ik_index_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📘 NIFTY Summary", callback_data="idx_nifty")],
        [InlineKeyboardButton("📙 BANKNIFTY Summary", callback_data="idx_banknifty")],
        [InlineKeyboardButton("🔥 OI Heatmap", callback_data="idx_heatmap")],
        [InlineKeyboardButton("⬅️ Back", callback_data="back_main")]
    ])


def ik_help_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_main")]])


# ---------- utils ----------
def split_message(text: str, max_length: int = 3900) -> List[str]:
    """Split text into chunks safe for Telegram (preserve lines)."""
    lines = text.splitlines()
    chunks: List[str] = []
    buf = ""
    for line in lines:
        if not buf:
            candidate = line
        else:
            candidate = buf + "\n" + line
        if len(candidate) > max_length:
            if buf:
                chunks.append(buf)
            # if single line > max_length, force-slice
            if len(line) > max_length:
                for i in range(0, len(line), max_length):
                    chunks.append(line[i:i + max_length])
                buf = ""
            else:
                buf = line
        else:
            buf = candidate
    if buf:
        chunks.append(buf)
    return chunks


def enrich_with_mcp(report: str, symbol: str) -> str:
    """Prepend company info and append cleaned news lines (safe f-strings)."""
    try:
        data = get_mcp_enrichment(symbol)
    except Exception as e:
        logger.debug("MCP enrichment failed: %s", e)
        data = None

    if not data:
        return report

    info = data.get("company_info", {}) or {}
    if info:
        company_block = (
            "*{name}*\nSector: {sector}\nMarket Cap: {mcap}\n\n"
        ).format(
            name=info.get("name", symbol),
            sector=info.get("sector", "—"),
            mcap=info.get("market_cap", "—"),
        )
        report = company_block + report

    news_items = data.get("news", []) or []
    if news_items:
        news_block_lines = ["🗞 *Latest News:*"]
        for n in news_items[:5]:
            # remove urls safely (no backslash in f-string expression)
            cleaned = re.sub(r"https?://\S+", "", n).strip()
            cleaned = cleaned.lstrip("• ").strip()
            if cleaned:
                news_block_lines.append("- " + cleaned)
        report += "\n\n" + "\n".join(news_block_lines)

    return report


# ---------- callback router ----------
async def button_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    await query.answer()
    uid = query.message.chat_id
    data = query.data or ""
    logger.info("Callback from %s: %s", uid, data)

    try:
        # back to main
        if data == "back_main":
            USER_STATE[uid] = "MAIN"
            await query.edit_message_text("🏠 Main Menu", reply_markup=ik_main_menu())
            return

        # stock menu
        if data == "stock_menu":
            USER_STATE[uid] = "STOCK"
            await query.edit_message_text("📈 Stock Menu", reply_markup=ik_stock_menu())
            return

        if data == "stock_analyze":
            USER_STATE[uid] = "STOCK_WAIT"
            await query.edit_message_text(
                "🔍 Send a stock name or symbol.\n(Or tap 🏠 Menu anytime)",
                reply_markup=ik_persistent()
            )
            return

        # options menu
        if data == "opt_menu":
            USER_STATE[uid] = "OPT"
            await query.edit_message_text("⚡ Options Menu", reply_markup=ik_opt_menu())
            return

        if data == "opt_best":
            USER_STATE[uid] = "OPT_BEST"
            await query.edit_message_text("🎯 Send symbol for Best Strike Finder (e.g., TCS-CE).", reply_markup=ik_persistent())
            return

        if data == "opt_expiry":
            USER_STATE[uid] = "OPT_EXP"
            await query.edit_message_text("📅 Send symbol for Expiry Scanner (e.g., TCS-CE-DEC).", reply_markup=ik_persistent())
            return

        if data == "opt_oi":
            USER_STATE[uid] = "OPT_OI"
            await query.edit_message_text("📊 Send symbol for OI Trend.", reply_markup=ik_persistent())
            return

        # index menu
        if data == "index_menu":
            USER_STATE[uid] = "INDEX"
            await query.edit_message_text("📊 Index Menu", reply_markup=ik_index_menu())
            return

        if data == "idx_nifty":
            await query.edit_message_text("⏳ Running NIFTY Summary…")
            try:
                report = analyze_nifty(for_telegram=True)
                for chunk in split_message(report):
                    await context.bot.send_message(chat_id=uid, text=chunk, reply_markup=ik_persistent())
            except Exception as e:
                logger.exception("Nifty analysis error")
                await context.bot.send_message(chat_id=uid, text=f"❌ NIFTY analysis failed: {e}", reply_markup=ik_persistent())
            return

        if data == "idx_banknifty":
            await query.edit_message_text("⏳ Running BANKNIFTY Summary…")
            try:
                menu_text, state = await get_bnf_expiry_menu_and_state()
                expiry = state["expiries"][0]
                out = await analyze_bnf_for_expiry(expiry)
                for chunk in split_message(out):
                    await context.bot.send_message(chat_id=uid, text=chunk, reply_markup=ik_persistent())
            except Exception as e:
                logger.exception("BankNifty analysis error")
                await context.bot.send_message(chat_id=uid, text=f"❌ BANKNIFTY analysis failed: {e}", reply_markup=ik_persistent())
            return

        # unknown
        await query.edit_message_text("⚠️ Unknown action", reply_markup=ik_persistent())

    except Exception as exc:
        logger.exception("button_router error")
        await context.bot.send_message(chat_id=uid, text=f"❌ Internal error: {exc}", reply_markup=ik_persistent())


# ---------- commands ----------
async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 *Welcome to Tidder Bot!*\nChoose from the menu below 👇",
        parse_mode="Markdown",
        reply_markup=ik_main_menu()
    )


async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = (
        "📖 *Help Menu*\n"
        "• Send any stock symbol (TCS, RELIANCE)\n"
        "• Send `NIFTY50` for index analysis\n"
        "• For options: `STOCK-CE`, `STOCK-PE`, or `STOCK-CEPE`\n"
        "• Reply with a number (1/2/3) to choose expiry from menu\n"
    )
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=ik_persistent())


async def handle_usage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    used, limit = get_user_usage(user_id)
    msg = f"📊 You’ve used *{used} / {limit}* free requests today."
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=ik_persistent())


# ---------- main message handler ----------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cleanup_expired()
    if not update.message or not update.message.text:
        return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # quick typing feedback
    try:
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    except Exception:
        pass

    # 1) numeric -> expiry selection
    if re.fullmatch(r"\d{1,3}", text):
        pending = get_pending(chat_id)
        if not pending:
            await update.message.reply_text("⚠️ No pending expiry selection.", reply_markup=ik_persistent())
            return

        idx = int(text) - 1
        expiries = pending["state"]["expiries"]
        if idx < 0 or idx >= len(expiries):
            await update.message.reply_text(f"❌ Invalid choice. Pick 1..{len(expiries)}.", reply_markup=ik_persistent())
            return

        data = pop_pending(chat_id)
        # route to BankNifty special flow if bnf flag present
        try:
            if isinstance(data, dict) and data.get("bnf"):
                expiry = expiries[idx]
                out = await analyze_bnf_for_expiry(expiry)
                for chunk in split_message(out):
                    await update.message.reply_text(chunk, reply_markup=ik_persistent())
            else:
                result = await process_option_rr_telegram(data["message_text"], expiry_selection=idx, desired_rr=REQUEST_RR)
                for chunk in split_message(result):
                    await update.message.reply_text(chunk, parse_mode="Markdown", reply_markup=ik_persistent())
        except Exception as e:
            logger.exception("expiry selection error")
            await update.message.reply_text(f"❌ Option scan failed: {e}", reply_markup=ik_persistent())
        return

    # 2) option detection
    ticker_guess, dtype_guess, expiry_token = parse_tg_input(text)
    option_tokens = ("CE", "PE", "-")
    is_option_query = False
    if "-" in text or re.search(r"\b(CE|PE|CEPE)\b", text.upper()) or re.search(r"\b(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\b", text.upper()):
        is_option_query = True

    if is_option_query and ticker_guess:
        if not can_user_request(user_id):
            await update.message.reply_text("🚫 Daily free limit reached.", parse_mode="Markdown", reply_markup=ik_persistent())
            return
        log_user_request(user_id)

        # expiry provided -> run immediately
        if expiry_token:
            await update.message.reply_text(f"📥 Processing {ticker_guess} {dtype_guess} for {expiry_token}…", parse_mode="Markdown")
            try:
                res = await process_option_rr_telegram(text, expiry_str=expiry_token, desired_rr=REQUEST_RR)
                for chunk in split_message(res):
                    await update.message.reply_text(chunk, parse_mode="Markdown", reply_markup=ik_persistent())
            except Exception as e:
                logger.exception("option immediate scan failed")
                await update.message.reply_text(f"❌ Option RR scan failed: {e}", reply_markup=ik_persistent())
            return

        # otherwise show expiry menu
        try:
            menu_text, state = await get_expiry_menu_and_state(text)
            set_pending(chat_id, {"message_text": text, "state": state})
            await update.message.reply_text(menu_text, reply_markup=ik_persistent())
        except Exception as e:
            logger.exception("could not fetch expiries")
            await update.message.reply_text(f"❌ Could not fetch expiries: {e}", reply_markup=ik_persistent())
        return

    # 3) NIFTY50 quick
    if text.upper() == "NIFTY50":
        await update.message.reply_text("📊 Running NIFTY50 analysis…", reply_markup=ik_persistent())
        try:
            report = analyze_nifty(for_telegram=True)
            for chunk in split_message(report):
                await update.message.reply_text(chunk, reply_markup=ik_persistent())
        except Exception as e:
            logger.exception("NIFTY50 error")
            await update.message.reply_text(f"❌ Failed analyzing NIFTY50: {e}", reply_markup=ik_persistent())
        return

    # 4) NLP-driven stock analysis
    intent, symbol = extract_intent_and_symbol(text.upper(), company_df)
    if not symbol:
        await update.message.reply_text("❌ Could not detect a valid company name or symbol.", reply_markup=ik_persistent())
        return

    if not can_user_request(user_id):
        await update.message.reply_text("🚫 Daily free limit reached.", parse_mode="Markdown", reply_markup=ik_persistent())
        return
    log_user_request(user_id)

    await update.message.reply_text(f"🔍 Processing {symbol} …", parse_mode="Markdown", reply_markup=ik_persistent())

    try:
        success, report = run_pipeline_for_symbol(symbol, chat_id)
        if success and report:
            enriched = enrich_with_mcp(report, symbol)
            for chunk in split_message(enriched):
                await update.message.reply_text(chunk, reply_markup=ik_persistent())
            return

        # fallback
        report = analyze_single_stock(symbol)
        for chunk in split_message(report):
            await update.message.reply_text(chunk, reply_markup=ik_persistent())

    except Exception as e:
        logger.exception("stock analysis error")
        await update.message.reply_text(f"❌ Error analyzing {symbol}: {e}", reply_markup=ik_persistent())


# ---------- BankNifty convenience commands ----------
async def handle_bnf_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    await update.message.reply_text("📥 Preparing BankNifty expiries…", reply_markup=ik_persistent())
    try:
        menu_text, state = await get_bnf_expiry_menu_and_state()
        state_update = {"message_text": "BANKNIFTY-CEPE", "state": state, "bnf": True}
        set_pending(chat_id, state_update)
        await update.message.reply_text(menu_text, reply_markup=ik_persistent())
    except Exception as e:
        logger.exception("bnf cmd error")
        await update.message.reply_text(f"❌ Could not fetch BankNifty expiries: {e}", reply_markup=ik_persistent())


# ---------- app bootstrap ----------
def main() -> None:
    if not TOKEN:
        raise RuntimeError("TELEGRAM_TOKEN not set in environment")

    app = ApplicationBuilder().token(TOKEN).build()

    # commands
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(CommandHandler("help", handle_help))
    app.add_handler(CommandHandler("usage", handle_usage))
    app.add_handler(CommandHandler("bnf", handle_bnf_cmd))

    # callbacks + messages
    app.add_handler(CallbackQueryHandler(button_router))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Tidder Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()
