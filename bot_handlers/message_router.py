from telegram import Update
from telegram.ext import ContextTypes
from bot_handlers.stock_handler import handle_stock_menu


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().upper()

    # ✅ ONLY STOCK SYMBOL HANDLING HERE
    await handle_stock_menu(update, context)
