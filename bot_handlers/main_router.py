from telegram import Update
from telegram.ext import ContextTypes

from bot_ui.keyboards import main_menu_keyboard

from bot_handlers.market_handler import (
    handle_market_menu,
    handle_market_nifty,
    handle_market_bank,
    handle_volatility_menu,
)
from bot_handlers.stock_handler import handle_stock_menu
from bot_handlers.help_handler import handle_help_menu
from bot_handlers.mf_handler import handle_mf_menu
from bot_handlers.subscription_handler import handle_subscription_menu
from bot_handlers.fno_handler import (
    handle_fno_menu,
    handle_fno_gainers,
    handle_fno_losers,
)


async def button_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    # =========================
    # ✅ MAIN MENUS
    # =========================
    if data == "MARKET_MENU":
        await handle_market_menu(update, context)

    elif data == "STOCK_MENU":
        await handle_stock_menu(update, context)

    elif data == "OPTION_MENU":
        await handle_fno_menu(update, context)

    elif data == "MF_MENU":
        await handle_mf_menu(update, context)

    elif data == "SUB_MENU":
        await handle_subscription_menu(update, context)

    elif data == "HELP_MENU":
        await handle_help_menu(update, context)

    # =========================
    # ✅ MARKET SUB MENUS
    # =========================
    elif data == "MARKET_NIFTY":
        await handle_market_nifty(update, context)

    elif data == "MARKET_BANK":
        await handle_market_bank(update, context)

    elif data == "MARKET_VOL":
        await handle_volatility_menu(update, context)

    # =========================
    # ✅ FNO
    # =========================
    elif data == "FNO_GAINERS":
        await handle_fno_gainers(update, context)

    elif data == "FNO_LOSERS":
        await handle_fno_losers(update, context)

    # =========================
    # ✅ GLOBAL NAVIGATION
    # =========================
    elif data == "BACK":
        await query.edit_message_text("⬅️ Back", reply_markup=main_menu_keyboard())

    elif data == "MAIN_MENU":
        await query.edit_message_text("🏠 Main Menu", reply_markup=main_menu_keyboard())
