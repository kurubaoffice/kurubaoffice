from telegram import Update
from telegram.ext import ContextTypes

from bot_handlers.main_router import button_router
from bot_handlers.stock_handler import handle_stock_menu
from bot_ui.keyboards import main_menu_keyboard
from reporting.report_single_stock import analyze_single_stock
from utils.symbol_resolver import resolve_symbol

import re
from telegram import Update
from telegram.ext import ContextTypes
from reporting.report_single_stock import analyze_single_stock

# ---------------------------
# MarkdownV2 Escaping
# ---------------------------
def escape_markdown_v2(text: str) -> str:
    """
    Escape special characters for Telegram MarkdownV2.
    """
    escape_chars = r'_*\[\]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)


# ---------------------------
# Message Handler
# ---------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query:
        await query.answer()
        from bot_handlers.main_router import button_router
        await button_router(update, context)
        return

    if update.message:
        user_text = update.message.text.strip()

        # Send the "Processing..." message and save the message object
        processing_msg = await update.message.reply_text(
            f"🔍 Processing `{user_text}`…", parse_mode="MarkdownV2"
        )

        # Resolve stock symbol
        symbol = resolve_symbol(user_text)
        if not symbol:
            await processing_msg.edit_text(
                "❌ Could not detect a valid stock name or symbol.",
                reply_markup=main_menu_keyboard()
            )
            return

        # Generate stock report
        report = analyze_single_stock(symbol)
        safe_report = escape_markdown_v2(report)

        # Edit the original "Processing..." message with the final report + menu
        await processing_msg.edit_text(
            safe_report,
            parse_mode="MarkdownV2",
            reply_markup=main_menu_keyboard()
        )