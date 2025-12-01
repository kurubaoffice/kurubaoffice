import re

INTENT_KEYWORDS = {
    "greeting": ["hi", "hello", "hey", "gm", "good morning", "good evening"],
    "thank_you": ["thanks", "thank you", "thx"],
    "stoploss": ["sl", "stoploss", "stop loss", "stop-loss"],
    "target": ["target", "tg", "take profit", "tp"],
    "hold_or_sell": [
        "hold?", "hold or sell", "should i hold", "should i sell",
        "hold this", "sell this", "what to do"
    ],
    "future_outlook": ["future", "outlook", "next week", "coming days", "view"],
    "technical_analysis": ["chart", "technical", "indicator", "levels"],
}

def detect_intent(text: str) -> str:
    t = text.lower().strip()

    # direct keyword scoring
    for key, keywords in INTENT_KEYWORDS.items():
        for w in keywords:
            if re.search(rf"\b{re.escape(w)}\b", t):
                return key

    # natural language pattern-based matching
    if re.search(r"(stop ?loss|sl) for", t):
        return "stoploss"

    if re.search(r"(target|tg) for", t):
        return "target"

    if re.search(r"hold|sell", t):
        return "hold_or_sell"

    if re.search(r"(future|outlook|view)", t):
        return "future_outlook"

    # Generic stock query (short input)
    if re.search(r"[a-zA-Z]{2,}", t) and len(t.split()) <= 4:
        return "stock_query"

    return "unknown"
