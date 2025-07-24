from storage.connection import get_connection

def insert_price_data(symbol, df):
    conn = get_connection()
    cursor = conn.cursor()

    for _, row in df.iterrows():
        cursor.execute("""
            INSERT INTO price_data (symbol, date, open, high, low, close, volume)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING;
        """, (
            symbol,
            row['Date'].date(),
            row['Open'],
            row['High'],
            row['Low'],
            row['Close'],
            row['Volume']
        ))

    conn.commit()
    cursor.close()
    conn.close()
