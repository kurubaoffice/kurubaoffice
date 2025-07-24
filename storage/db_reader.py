from storage.connection import get_connection

def get_active_symbols():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT symbol FROM stocks;")
    symbols = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return symbols
