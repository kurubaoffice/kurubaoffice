# utils/nlp_utils.py

import re
import spacy

nlp = spacy.load("en_core_web_sm")

BUY_KEYWORDS = [
    "buy", "good to buy", "should i buy", "can i buy", "is it good to buy",
    "should i purchase", "recommend buying", "is it a buy",
    "thinking of buying", "planning to buy", "worth buying", "entry point"
]

SELL_KEYWORDS = [
    "sell", "should i sell", "can i sell", "is it good to sell",
    "recommend selling", "time to sell", "offload", "exit now",
    "thinking of selling", "planning to sell", "profit booking", "book profits"
]

FUTURE_KEYWORDS = [
    "future", "outlook", "prediction", "prospects", "forecast", "trend",
    "expected", "long term view", "next month", "coming days", "target price"
]

HOLD_KEYWORDS = [
    "hold", "should i hold", "keep holding", "continue holding",
    "stay invested", "not selling", "hold position", "maintain position"
]

STOPLOSS_KEYWORDS = [
    "stop loss", "stoploss", "sl", "protect profits", "limit losses",
    "set stop", "stop price", "support level", "exit point"
]


def extract_intent_and_symbol(text: str, company_df) -> tuple:
    text_lower = text.lower()
    # Remove noise words like 'stock'
    text_clean = re.sub(r"\bstock\b", "", text_lower).strip()

    # Detect intent
    intent = None
    for kw in BUY_KEYWORDS:
        if kw in text_clean:
            intent = "buy"
            break
    if not intent:
        for kw in SELL_KEYWORDS:
            if kw in text_clean:
                intent = "sell"
                break
    if not intent:
        for kw in FUTURE_KEYWORDS:
            if kw in text_clean:
                intent = "future"
                break
    if not intent:
        intent = "unknown"

    # Extract symbol from company_df
    text_upper = text_clean.upper()

    symbols = company_df["symbol"].astype(str).str.upper().tolist()
    names = company_df["name"].astype(str).str.upper().tolist()

    symbol_found = None
    # Try to find exact symbol in tokens
    tokens = set(text_upper.split())
    for sym in symbols:
        if sym in tokens:
            symbol_found = sym
            break

    # If no symbol found, try company name partial match
    if not symbol_found:
        for idx, name in enumerate(names):
            if name in text_upper:
                symbol_found = symbols[idx]
                break

    return intent, symbol_found
