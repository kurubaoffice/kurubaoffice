from telegram import Update
from telegram.ext import ContextTypes
from bot_ui.keyboards import main_menu_keyboard


async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "🏠 Main Menu",
        reply_markup=main_menu_keyboard()
    )


async def handle_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "🏠 Main Menu",
        reply_markup=main_menu_keyboard()
    )
