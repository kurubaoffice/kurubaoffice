# bot_handlers/mf_handler.py

from telegram import Update
from telegram.ext import ContextTypes
from bot_ui.keyboards import main_menu_keyboard


async def handle_mf_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    msg = (
        "💼 Mutual Funds\n\n"
        "✅ Features coming soon:\n"
        "• Top Performers\n"
        "• SIP Planner\n"
        "• Risk Analyzer"
    )

    await query.edit_message_text(msg, reply_markup=main_menu_keyboard())
