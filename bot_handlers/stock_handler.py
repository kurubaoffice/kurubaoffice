# bot_handlers/stock_handler.py

from telegram import Update
from telegram.ext import ContextTypes
from bot_ui.keyboards import main_menu_keyboard


async def handle_stock_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    msg = (
        "📊 Stock Analysis Menu\n\n"
        "✅ Send any stock name like:\n"
        "• RELIANCE\n"
        "• INFY\n"
        "• HDFCBANK\n"
    )

    await query.edit_message_text(msg, reply_markup=main_menu_keyboard())
