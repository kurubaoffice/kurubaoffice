# bot_handlers/fno_handler.py

from telegram import Update
from telegram.ext import ContextTypes

from bot_ui.formatters import format_simple_list
from bot_ui.keyboards import option_menu_keyboard


async def handle_fno_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "🧨 FnO Analysis Menu",
        reply_markup=option_menu_keyboard()
    )


async def handle_fno_gainers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Temporary mock data (we'll wire live NSE safely later)
    data = [
        {"symbol": "RELIANCE", "ltp": 2850, "change_pct": 2.1},
        {"symbol": "INFY", "ltp": 1620, "change_pct": 1.7},
    ]

    msg = format_simple_list(data, "📈 FnO Top Gainers")
    await query.edit_message_text(msg, reply_markup=option_menu_keyboard())


async def handle_fno_losers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = [
        {"symbol": "TATASTEEL", "ltp": 134, "change_pct": -1.6},
        {"symbol": "ONGC", "ltp": 249, "change_pct": -1.2},
    ]

    msg = format_simple_list(data, "📉 FnO Top Losers")
    await query.edit_message_text(msg, reply_markup=option_menu_keyboard())
