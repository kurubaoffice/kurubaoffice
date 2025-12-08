#/bot_handlers/market_handler.py

from telegram import Update
from telegram.ext import ContextTypes
from bot_ui.keyboards import market_menu_keyboard

# ✅ IMPORT YOUR EXISTING ENGINE
from compute.market.volatility_engine import (
    analyze_vix_and_nifty,
    format_vol_report_telegram,
)
from compute.market.nifty_handler import send_nifty_overview  # ADD THIS

async def handle_market_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📈 Market Analysis Menu",
        reply_markup=market_menu_keyboard()
    )

async def handle_volatility_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        data = analyze_vix_and_nifty()
        msg = format_vol_report_telegram(data)
        await query.edit_message_text(
            msg,
            reply_markup=market_menu_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        print("Volatility Handler Error:", e)
        await query.edit_message_text(
            "❌ Unable to generate volatility report right now.\nPlease try again later.",
            reply_markup=market_menu_keyboard()
        )

async def handle_market_nifty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        # Optional loading message
        loading_msg = "📊 NIFTY Overview\n\nFetching latest data..."
        await query.edit_message_text(loading_msg, reply_markup=market_menu_keyboard())

        # Call the NIFTY Overview function
        await send_nifty_overview(update, context)
    except Exception as e:
        print("NIFTY Handler Error:", e)
        await query.edit_message_text(
            "❌ Unable to fetch NIFTY Overview right now.\nPlease try again later.",
            reply_markup=market_menu_keyboard()
        )

async def handle_market_bank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        loading_msg = "📊 Bank Nifty Overview\n\nFetching latest data..."
        await query.edit_message_text(loading_msg, reply_markup=market_menu_keyboard())
        # TODO: Replace with live Bank Nifty function
    except Exception as e:
        print("Bank Nifty Handler Error:", e)
        await query.edit_message_text(
            "❌ Unable to fetch Bank Nifty Overview right now.\nPlease try again later.",
            reply_markup=market_menu_keyboard()
        )
