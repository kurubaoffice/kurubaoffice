import os
import logging
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from bot_ui.keyboards import main_menu_keyboard
from bot_handlers.main_router import button_router
from bot_handlers.message_router import handle_message

# =========================
# ✅ LOAD ENV
# =========================
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN not found in environment variables")

# =========================
# ✅ LOGGING
# =========================
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)

# =========================
# ✅ COMMANDS
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏠 Welcome to Tidder 2.0",
        reply_markup=main_menu_keyboard()
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❓ Help Menu\n\nUse the buttons below to navigate.",
        reply_markup=main_menu_keyboard()
    )


# =========================
# ✅ BOT BOOTSTRAP
# =========================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # ✅ Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    # ✅ Buttons
    app.add_handler(CallbackQueryHandler(button_router))

    # ✅ Text Input
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Tidder 2.0 Bot Running...")
    app.run_polling()


if __name__ == "__main__":
    main()
