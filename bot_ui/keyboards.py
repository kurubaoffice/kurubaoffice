# bot_ui/keyboards.py

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# =========================
# ✅ MAIN MENU
# =========================
def main_menu_keyboard():
    buttons = [
        [InlineKeyboardButton("📈 Market Analysis", callback_data="MARKET_MENU")],
        [InlineKeyboardButton("📊 Stock Analysis", callback_data="STOCK_MENU")],
        [InlineKeyboardButton("🧨 Options Analysis", callback_data="OPTION_MENU")],
        [InlineKeyboardButton("💼 Mutual Funds", callback_data="MF_MENU")],
        [InlineKeyboardButton("💎 Subscription", callback_data="SUB_MENU")],
        [InlineKeyboardButton("❓ Help", callback_data="HELP_MENU")],
    ]
    return InlineKeyboardMarkup(buttons)


# =========================
# ✅ MARKET MENU
# =========================
def market_menu_keyboard():
    buttons = [
        [InlineKeyboardButton("📉 NIFTY Overview", callback_data="MARKET_NIFTY")],
        [InlineKeyboardButton("📈 BankNifty Overview", callback_data="MARKET_BANK")],
        [InlineKeyboardButton("📈 MARKET VOLATILITY", callback_data="MARKET_VOL")],
        [InlineKeyboardButton("↩️ Back", callback_data="BACK")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="MAIN_MENU")],
    ]
    return InlineKeyboardMarkup(buttons)


# =========================
# ✅ STOCK MENU
# =========================
def stock_menu_keyboard():
    buttons = [
        [InlineKeyboardButton("🔍 Search Stock", callback_data="STOCK_SEARCH")],
        [InlineKeyboardButton("🔥 Top Gainers", callback_data="STOCK_GAINERS")],
        [InlineKeyboardButton("❄️ Top Losers", callback_data="STOCK_LOSERS")],
        [InlineKeyboardButton("↩️ Back", callback_data="BACK")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="MAIN_MENU")],
    ]
    return InlineKeyboardMarkup(buttons)


# =========================
# ✅ OPTIONS MENU
# =========================
def option_menu_keyboard():
    buttons = [
        [InlineKeyboardButton("📈 FnO Gainers", callback_data="FNO_GAINERS")],
        [InlineKeyboardButton("📉 FnO Losers", callback_data="FNO_LOSERS")],
        [InlineKeyboardButton("🎯 Best RR Trades", callback_data="FNO_RR")],
        [InlineKeyboardButton("🧠 OI Analysis", callback_data="FNO_OI")],
        [InlineKeyboardButton("↩️ Back", callback_data="BACK")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="MAIN_MENU")],
    ]
    return InlineKeyboardMarkup(buttons)
