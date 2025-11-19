# compute/options/rr_parser.py
import re
from datetime import datetime
from typing import Tuple, Optional

def normalize_token(token: str) -> str:
    return token.strip().upper()

def parse_tg_input(msg: str) -> Tuple[Optional[str], str, Optional[str]]:
    """
    Parse input into (ticker, dtype, expiry_raw)
    Accept both `TCS-CE`, `TCS CE`, `TCS CE DEC`, `TCS-CEPE-DEC`, `TCS CEPE 25DEC`
    dtype -> "CE" | "PE" | "CEPE"
    expiry_raw -> raw expiry token (maybe None). Caller will resolve against live expiries.

    Returns (ticker or None, dtype, expiry_raw)
    """
    if not msg or not msg.strip():
        return None, "CEPE", None

    # split on whitespace or hyphen, allow multiple separators
    parts = [p for p in re.split(r"[\s\-]+", msg.strip().upper()) if p]

    if not parts:
        return None, "CEPE", None

    ticker = parts[0]
    dtype = None
    expiry_raw = None

    for p in parts[1:]:
        if p in ("CE", "PE", "CEPE"):
            dtype = p
        else:
            # first non-CE/PE token is treated as expiry
            if expiry_raw is None:
                expiry_raw = p

    if dtype is None:
        dtype = "CEPE"

    return ticker, dtype, expiry_raw
