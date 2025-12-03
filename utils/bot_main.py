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
from nlp.intent_model.intent_classifier import predict_intent
from nlp.extract_entities import extract_stock_entity
from nlp.language_handler import translate_to_english
from nlp.context_manager import context
from telegram import ReplyKeyboardMarkup
from compute.options.fno_snapshot import fetch_fno_snapshot, get_top_movers
# FnO imports
from telegram import ReplyKeyboardMarkup
from utils.logo_utils import get_company_details
from compute.options.fno_analysis import analyze_fno_stock
from compute.options.fno_snapshot import fetch_fno_snapshot, get_top_movers

import json
import os
from datetime import datetime

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
        [InlineKeyboardButton("🧿 FnO Dashboard", callback_data="fno_menu")],   # 🔥 NEW
        [InlineKeyboardButton("📈 Market Volatility", callback_data="idx_volatility")],  # 🔥 NEW
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
        [InlineKeyboardButton("📉 Volatility Strategy", callback_data="idx_volatility")],
        [InlineKeyboardButton("⬅️ Back", callback_data="back_main")]
    ])
def ik_fno_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("📈 Top Gainers", callback_data="fno_gainers")],
        [InlineKeyboardButton("📉 Top Losers", callback_data="fno_losers")],
        [InlineKeyboardButton("🔎 Search FnO Stock", callback_data="fno_search")],
        [InlineKeyboardButton("⬅️ Back", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def ik_help_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_main")]])

def format_top_list(df, title):
    lines = [f"<b>{title}</b>\n"]
    for _, row in df.iterrows():
        lines.append(
            f"{row['symbol']}  {row['change_pct']:.2f}%\n"
            f"Price: {row['ltp']} | OI: {row['oi']}\n"
        )
    return "\n".join(lines)
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

# -----------------------------------
FILE = "storage/user_stats.json"

def load_stats():
    if not os.path.exists(FILE):
        return {}
    with open(FILE) as f:
        return json.load(f)

def save_stats(data):
    with open(FILE, "w") as f:
        json.dump(data, f, indent=4)

def update_user_access(user_id, username):
    data = load_stats()

    uid = str(user_id)
    if uid not in data:
        data[uid] = {
            "username": username,
            "first_seen": str(datetime.now()),
            "last_seen": str(datetime.now()),
            "access_count": 1
        }
    else:
        data[uid]["last_seen"] = str(datetime.now())
        data[uid]["access_count"] += 1

    save_stats(data)
#--------------------------------------------------------------
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
def format_fno_stock_summary(rr_output):
    lines = []

    for opt_type, payload in rr_output.items():
        cands = payload.get("candidates")
        if cands is None or cands.empty:
            continue

        lines.append(f"\n<b>{opt_type} Options</b>")

        for _, row in cands.iterrows():
            lines.append(
                f"Strike {row['strike']} | Premium {row['premium']}\n"
                f"• Breakeven: {row['breakeven']}\n"
                f"• PoP: {row['probability']:.1f}%\n"
                f"• SL: {row['sl_premium']}"
            )

    return "\n".join(lines)


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
                "🔍 Send a stock name or symbol (Eg: ICICIBANK ).\n(Or tap 🏠 Menu anytime)",
                reply_markup=ik_persistent()
            )
            return

        # options menu
        if data == "opt_menu":
            USER_STATE[uid] = "OPT"
            await query.edit_message_text("⚡ Options Menu", reply_markup=ik_opt_menu())
            return
        # -------------------------------
        # VOLATILITY STRATEGY REPORT
        # -------------------------------
        if data == "idx_volatility":
            await query.edit_message_text("⏳ Calculating Volatility Strategy…")

            try:
                from compute.vol_strategies import analyze_vix_and_nifty, format_vol_report_cli

                raw = analyze_vix_and_nifty()
                report = format_vol_report_cli(raw)

                for chunk in split_message(report):
                    await context.bot.send_message(
                        chat_id=uid,
                        text=chunk,
                        reply_markup=ik_persistent()
                    )

            except Exception as e:
                logger.exception("Volatility Strategy error")
                await context.bot.send_message(
                    chat_id=uid,
                    text=f"❌ Error generating Volatility Strategy Report:\n\n{e}",
                    reply_markup=ik_persistent()
                )
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
        # ---------------- FnO Menu ----------------
        if data == "fno_menu":
            USER_STATE[uid] = "FNO"
            await query.edit_message_text("🧿 FnO Dashboard", reply_markup=ik_fno_menu())
            return

        if data == "fno_gainers":
            snap = fetch_fno_snapshot()
            gainers, _ = get_top_movers(snap)
            msg = format_top_list(gainers, "📈 FnO Top Gainers")
            await query.edit_message_text(msg, parse_mode="HTML", reply_markup=ik_persistent())
            return

        if data == "fno_losers":
            snap = fetch_fno_snapshot()
            _, losers = get_top_movers(snap)
            msg = format_top_list(losers, "📉 FnO Top Losers")
            await query.edit_message_text(msg, parse_mode="HTML", reply_markup=ik_persistent())
            return

        if data == "fno_search":
            USER_STATE[uid] = "FNO_WAIT"
            await query.edit_message_text("🔍 Send FnO stock name/symbol", reply_markup=ik_persistent())
            return
        if data.startswith("fnoc_") or data.startswith("fnop_") or data.startswith("fnof_"):
            _, symbol = data.split("_", 1)
            rr_output = analyze_fno_stock(symbol)

            if rr_output.get("error"):
                await query.edit_message_text(rr_output["error"], reply_markup=ik_persistent())
                return

            if data.startswith("fnoc_"):
                msg = format_fno_stock_summary({"CE": rr_output["CE"]})
            elif data.startswith("fnop_"):
                msg = format_fno_stock_summary({"PE": rr_output["PE"]})
            else:
                msg = format_fno_stock_summary(rr_output)

            await query.edit_message_text(msg, parse_mode="HTML", reply_markup=ik_persistent())
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

    # typing feedback
    try:
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    except Exception:
        pass

    async def fno_menu(update, context):
        keyboard = [
            ["Top Gainers", "Top Losers"],
            ["Search FnO Stock"],
            ["Back"]
        ]
        await update.message.reply_text(
            "📊 <b>FnO Dashboard</b>",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
            parse_mode="HTML"
        )

    async def handle_top_gainers(update, context):
        snap = fetch_fno_snapshot()
        gainers, _ = get_top_movers(snap)
        msg = format_top_list(gainers, "📈 FnO Top Gainers")
        await update.message.reply_text(msg, parse_mode="HTML")

    async def handle_top_losers(update, context):
        snap = fetch_fno_snapshot()
        _, losers = get_top_movers(snap)
        msg = format_top_list(losers, "📉 FnO Top Losers")
        await update.message.reply_text(msg, parse_mode="HTML")



    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    from utils.logo_utils import get_company_details
    from compute.options.fno_analysis import analyze_fno_stock

    async def handle_fno_stock_query(update, context):
        symbol = update.message.text.upper()

        company_name, logo = get_company_details(symbol)

        # 🔹 Send logo (if exists)
        if logo and os.path.exists(logo):
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=open(logo, "rb"),
                caption=f"<b>{symbol}</b>\n{company_name}",
                parse_mode="HTML"
            )
        else:
            await update.message.reply_text(
                f"<b>{symbol}</b>\n{company_name}",
                parse_mode="HTML"
            )
        # -------- FnO STOCK SEARCH FLOW --------
        if USER_STATE.get(chat_id) == "FNO_WAIT":
            symbol = text.upper()
            company_name, logo = get_company_details(symbol)

            # send logo
            if logo and os.path.exists(logo):
                await update.message.reply_photo(
                    photo=open(logo, "rb"),
                    caption=f"<b>{symbol}</b>\n{company_name}",
                    parse_mode="HTML"
                )
            else:
                await update.message.reply_text(f"<b>{symbol}</b>\n{company_name}", parse_mode="HTML")

            # buttons
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("CE Options", callback_data=f"fnoc_{symbol}")],
                [InlineKeyboardButton("PE Options", callback_data=f"fnop_{symbol}")],
                [InlineKeyboardButton("Full Summary", callback_data=f"fnof_{symbol}")],
            ])
            await update.message.reply_text("Choose:", reply_markup=kb)

            USER_STATE[chat_id] = None
            return
        # 🔹 Buttons under logo
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("CE Options", callback_data=f"fno_ce_{symbol}")],
            [InlineKeyboardButton("PE Options", callback_data=f"fno_pe_{symbol}")],
            [InlineKeyboardButton("Full Summary", callback_data=f"fno_full_{symbol}")],
        ])

        await update.message.reply_text(
            "Choose what you want to view:",
            reply_markup=keyboard
        )

    async def fno_button_handler(update, context):
        query = update.callback_query
        await query.answer()

        action, symbol = query.data.split("_", 1)

        rr_output = analyze_fno_stock(symbol)

        if rr_output.get("error"):
            await query.edit_message_text(rr_output["error"])
            return

        if action == "fno":
            await query.edit_message_text("Unknown request")
            return

        if action == "fnoce":
            msg = format_fno_stock_summary({"CE": rr_output["CE"]})
        elif action == "fnope":
            msg = format_fno_stock_summary({"PE": rr_output["PE"]})
        else:
            msg = format_fno_stock_summary(rr_output)

        await query.edit_message_text(msg, parse_mode="HTML")

    # -------------------------------------------------------------------
    # 1️⃣ PENDING STATE (expiry selection / BNF flow)
    # -------------------------------------------------------------------
    if re.fullmatch(r"\d{1,3}", text):
        pending = get_pending(chat_id)
        if not pending:
            await update.message.reply_text(
                "⚠️ No pending expiry selection.",
                reply_markup=ik_persistent(),
            )
            return

        idx = int(text) - 1
        expiries = pending["state"]["expiries"]
        if idx < 0 or idx >= len(expiries):
            await update.message.reply_text(
                f"❌ Invalid choice. Pick 1..{len(expiries)}.",
                reply_markup=ik_persistent(),
            )
            return

        data = pop_pending(chat_id)
        try:
            # BankNifty special
            if isinstance(data, dict) and data.get("bnf"):
                expiry = expiries[idx]
                out = await analyze_bnf_for_expiry(expiry)
                for chunk in split_message(out):
                    await update.message.reply_text(chunk, reply_markup=ik_persistent())
            else:
                result = await process_option_rr_telegram(
                    data["message_text"],
                    expiry_selection=idx,
                    desired_rr=REQUEST_RR,
                )
                for chunk in split_message(result):
                    await update.message.reply_text(
                        chunk, parse_mode="Markdown", reply_markup=ik_persistent()
                    )
        except Exception as e:
            logger.exception("expiry selection error")
            await update.message.reply_text(
                f"❌ Option scan failed: {e}", reply_markup=ik_persistent()
            )
        return

    # -------------------------------------------------------------------
    # 2️⃣ OPTION QUERY DETECTION (Runs BEFORE NLP)
    # -------------------------------------------------------------------
    ticker_guess, dtype_guess, expiry_token = parse_tg_input(text)
    is_option_query = False

    if (
        "-" in text
        or re.search(r"\b(CE|PE)\b", text.upper())
        or re.search(r"\b(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\b", text.upper())
    ):
        is_option_query = True

    if is_option_query and ticker_guess:
        # daily limit
        if not can_user_request(user_id):
            await update.message.reply_text(
                "🚫 Daily free limit reached.",
                parse_mode="Markdown",
                reply_markup=ik_persistent(),
            )
            return

        log_user_request(user_id)

        # expiry given
        if expiry_token:
            await update.message.reply_text(
                f"📥 Processing {ticker_guess} {dtype_guess} for {expiry_token}…",
                parse_mode="Markdown",
            )
            try:
                res = await process_option_rr_telegram(
                    text, expiry_str=expiry_token, desired_rr=REQUEST_RR
                )
                for chunk in split_message(res):
                    await update.message.reply_text(
                        chunk, parse_mode="Markdown", reply_markup=ik_persistent()
                    )
            except Exception as e:
                logger.exception("option immediate scan failed")
                await update.message.reply_text(
                    f"❌ Option RR scan failed: {e}", reply_markup=ik_persistent()
                )
            return

        # expiry menu
        try:
            menu_text, state = await get_expiry_menu_and_state(text)
            set_pending(chat_id, {"message_text": text, "state": state})
            await update.message.reply_text(menu_text, reply_markup=ik_persistent())
        except Exception as e:
            logger.exception("could not fetch expiries")
            await update.message.reply_text(
                f"❌ Could not fetch expiries: {e}", reply_markup=ik_persistent()
            )
        return

    # -------------------------------------------------------------------
    # 3️⃣ QUICK KEYWORD — NIFTY50
    # -------------------------------------------------------------------
    if text.upper() == "NIFTY50":
        await update.message.reply_text(
            "📊 Running NIFTY50 analysis…", reply_markup=ik_persistent()
        )
        try:
            report = analyze_nifty(for_telegram=True)
            for chunk in split_message(report):
                await update.message.reply_text(chunk, reply_markup=ik_persistent())
        except Exception as e:
            logger.exception("NIFTY50 error")
            await update.message.reply_text(
                f"❌ Failed analyzing NIFTY50: {e}", reply_markup=ik_persistent()
            )
        return

    # -------------------------------------------------------------------
    # 4️⃣ NLP INTENT MODEL (Runs AFTER options / quick commands)
    # -------------------------------------------------------------------
    intent = predict_intent(text)
    print("Predicted Intent:", intent)
    # -------------------------------------------------------
    #  NLP INTENT-BASED COMMAND HANDLING (Stoploss/Target/etc.)
    # -------------------------------------------------------
    from nlp.extract_entities import extract_stock_entity
    from utils.symbol_resolver import resolve_symbol
    from compute.indicators.nlp_insights import (
        compute_hold_or_sell,
        compute_future_outlook,
        compute_stoploss,
        compute_target,
        compute_basic
    )

    # --------------------------------------------------------
    # 1) If message contains a stock-advise intent
    # --------------------------------------------------------
    if intent in ["hold_or_sell", "future_outlook", "stoploss", "target"]:

        # --- resolve the symbol ---
        resolved_symbol = resolve_symbol(text)
        if not resolved_symbol:
            await update.message.reply_text(
                "❌ Could not detect a valid symbol.\nPlease type a company name or stock symbol."
            )
            return

        symbol = resolved_symbol

        # --- load indicator-enriched DF ---
        df = analyze_single_stock(symbol, return_df=True)
        if df is None:
            await update.message.reply_text(
                f"⚠️ Could not fetch data for **{symbol}**."
            )
            return

        # --- route to correct NLP compute function ---
        if intent == "hold_or_sell":
            df = analyze_single_stock(symbol, return_df=True)
            advice = compute_hold_or_sell(df)

        elif intent == "future_outlook":
            advice = compute_future_outlook(df)
        elif intent == "stoploss":
            advice = compute_stoploss(df)
        elif intent == "target":
            advice = compute_target(df)

        await update.message.reply_text(
            f"📊 *{symbol}* — NLP advisory result:\n\n{advice}",
            parse_mode="Markdown"
        )

        return

    # extract symbol if NLP says so
    intent2, symbol = extract_intent_and_symbol(text.upper(), company_df)

    if intent2 and symbol:
        if not can_user_request(user_id):
            await update.message.reply_text(
                "🚫 Daily free limit reached.",
                parse_mode="Markdown",
                reply_markup=ik_persistent(),
            )
            return

        log_user_request(user_id)

        await update.message.reply_text(
            f"🔍 Processing {symbol} …",
            parse_mode="Markdown",
            reply_markup=ik_persistent(),
        )
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
            await update.message.reply_text(
                f"❌ Error analyzing {symbol}: {e}", reply_markup=ik_persistent()
            )
        return

    # -------------------------------------------------------------------
    # 5️⃣ FALLBACK (Unknown input)
    # -------------------------------------------------------------------
    await update.message.reply_text(
        "⚠️ Could not detect a valid symbol or request.\nPlease choose an option below 👇",
        reply_markup=ik_persistent(),
    )

async def handle_fno_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "🔎 Send FnO Stock Symbol (e.g., TCS, RELIANCE, HDFCBANK)",
        reply_markup=ik_persistent()
    )
    USER_STATE[update.effective_chat.id] = "FNO_WAIT"

def extract_symbol_from_text(text: str):
    import re
    from utils.symbol_resolver import resolve_symbol  # your existing resolver

    words = re.findall(r"[A-Za-z]+", text.upper())
    for w in words:
        symbol = resolve_symbol(w)
        if symbol:
            return symbol
    return None

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
