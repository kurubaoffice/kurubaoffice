import os
from datetime import datetime
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()  # Load environment variables from .env

# 🔐 DB credentials from .env
DB_CONFIG = {
    'dbname': os.getenv("DB_NAME"),
    'user': os.getenv("DB_USER"),
    'password': os.getenv("DB_PASSWORD"),
    'host': os.getenv("DB_HOST", "localhost"),
    'port': int(os.getenv("DB_PORT", 5432))
}

# 🔢 Free user request limit per day
FREE_LIMIT_PER_DAY = 6

# ─────────────────────────────────────
# 🔌 DB Connection Helper
# ─────────────────────────────────────
def get_db_connection():
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)

# ─────────────────────────────────────
# 🧾 User Setup
# ─────────────────────────────────────
def ensure_user_exists(user_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
            if not cur.fetchone():
                cur.execute("""
                    INSERT INTO users (id, is_subscribed, subscription_expiry, created_at)
                    VALUES (%s, false, NULL, NOW())
                """, (user_id,))

# ─────────────────────────────────────
# 🔍 Subscription Check
# ─────────────────────────────────────
def is_subscribed(user):
    if not user['is_subscribed']:
        return False
    if user['subscription_expiry'] and user['subscription_expiry'] > datetime.now():
        return True
    return False

# ─────────────────────────────────────
# ✅ Can User Make a Request?
# ─────────────────────────────────────
def can_user_request(user_id):
    ensure_user_exists(user_id)
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user = cur.fetchone()

            if user.get('is_limit_exempt'):
                # User bypasses limits
                return True

            if is_subscribed(user):
                return True

            # Check today's request count
            cur.execute("""
                SELECT COUNT(*) FROM request_logs
                WHERE user_id = %s AND requested_at::date = CURRENT_DATE
            """, (user_id,))
            count = cur.fetchone()['count']
            return count < FREE_LIMIT_PER_DAY

# ─────────────────────────────────────
# 🧠 Get User Usage (for /usage)
# ─────────────────────────────────────
def get_user_usage(user_id):
    ensure_user_exists(user_id)
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM request_logs
                WHERE user_id = %s AND requested_at::date = CURRENT_DATE
            """, (user_id,))
            count = cur.fetchone()['count']
            return count, FREE_LIMIT_PER_DAY

# ─────────────────────────────────────
# 📝 Log a User Request
# ─────────────────────────────────────
def log_user_request(user_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO request_logs (user_id, requested_at)
                VALUES (%s, NOW())
            """, (user_id,))
