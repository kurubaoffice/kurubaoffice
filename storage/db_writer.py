# storage/db_writer.py

from storage.connection import get_connection
import pandas as pd

def get_latest_date_for_symbol(symbol):
    """Return the latest date for which data is available in price_data."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT MAX(date) FROM price_data WHERE symbol = %s
    """, (symbol,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result[0]  # Could be None if no data exists

def insert_price_data(symbol, df):
    conn = get_connection()
    cursor = conn.cursor()

    # Clean column names
    df.columns = [
        (col[0] if isinstance(col, tuple) else col).split('_')[0].strip().lower()
        for col in df.columns
    ]
    print("[DEBUG] Cleaned df.columns:", df.columns.tolist())

    for idx, row in df.iterrows():
        try:
            cursor.execute("""
                INSERT INTO price_data (symbol, date, open, high, low, close, volume)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING;
            """, (
                symbol,
                row['date'].date(),  # Convert to date if datetime64
                row['open'],
                row['high'],
                row['low'],
                row['close'],
                row['volume']
            ))
        except Exception as e:
            print(f"[ERROR] Failed to insert for {symbol} on row {idx}: {e}")

    conn.commit()
    cursor.close()
    conn.close()
