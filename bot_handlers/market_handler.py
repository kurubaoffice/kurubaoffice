from telegram import Update
from telegram.ext import ContextTypes
from bot_ui.keyboards import market_menu_keyboard


async def handle_market_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "📈 Market Analysis Menu",
        reply_markup=market_menu_keyboard()
    )

from telegram import Update
from telegram.ext import ContextTypes

from bot_ui.keyboards import market_menu_keyboard

# ✅ IMPORT YOUR EXISTING ENGINE
from compute.market.volatility_engine import (
    analyze_vix_and_nifty,
    format_vol_report_telegram,
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

    msg = "📉 NIFTY Overview\n\nLive data wiring will be added shortly."
    await query.edit_message_text(msg, reply_markup=market_menu_keyboard())


async def handle_market_bank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    msg = "📈 Bank Nifty Overview\n\nLive data wiring will be added shortly."
    await query.edit_message_text(msg, reply_markup=market_menu_keyboard())
