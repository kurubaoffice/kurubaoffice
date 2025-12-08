from telegram import Update
from telegram.ext import ContextTypes
from bot_ui.keyboards import main_menu_keyboard


async def handle_subscription_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    msg = (
        "💎 Subscription Plans\n\n"
        "✅ Free Plan\n"
        "✅ Pro Plan\n"
        "✅ Algo Premium\n\n"
        "Payment gateway integration coming soon."
    )

    await query.edit_message_text(msg, reply_markup=main_menu_keyboard())
