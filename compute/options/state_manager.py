# compute/options/state_manager.py
import time
from typing import Dict, Any

# pending store with TTL
_PENDING: Dict[int, Dict] = {}
_DEFAULT_TTL_SECONDS = 5 * 60  # 5 minutes

def set_pending(chat_id: int, payload: Dict, ttl: int = _DEFAULT_TTL_SECONDS):
    _PENDING[chat_id] = {
        "payload": payload,
        "expires_at": time.time() + ttl
    }

def pop_pending(chat_id: int):
    item = _PENDING.pop(chat_id, None)
    if not item:
        return None
    if item["expires_at"] < time.time():
        return None
    return item["payload"]

def get_pending(chat_id: int):
    item = _PENDING.get(chat_id)
    if not item or item["expires_at"] < time.time():
        return None
    return item["payload"]

def cleanup_expired():
    now = time.time()
    to_remove = [k for k,v in _PENDING.items() if v["expires_at"] < now]
    for k in to_remove:
        _PENDING.pop(k, None)
