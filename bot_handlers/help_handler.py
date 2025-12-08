from telegram import Update
from telegram.ext import ContextTypes
from bot_ui.keyboards import main_menu_keyboard


async def handle_help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    msg = (
        "❓ Tidder 2.0 Help\n\n"
        "• Market Analysis\n"
        "• Stock Analysis\n"
        "• FnO Signals\n"
        "• Mutual Funds\n"
        "• Live Automation\n\n"
        "Type stock name anytime for analysis."
    )

    await query.edit_message_text(msg, reply_markup=main_menu_keyboard())
