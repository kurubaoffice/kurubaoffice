def insert_price_data(df):
    from storage.connection import get_connection
    conn = get_connection()
    cur = conn.cursor()

    records = [
        (
            row["Symbol"], row["Date"], row["Open"], row["High"], row["Low"],
            row["Close"], row["Adj Close"], row["Volume"]
        )
        for idx, row in df.iterrows()
    ]

    insert_query = """
        INSERT INTO price_data (
            symbol, date, open, high, low, close, adj_close, volume
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (symbol, date) DO UPDATE SET
            open = EXCLUDED.open,
            high = EXCLUDED.high,
            low = EXCLUDED.low,
            close = EXCLUDED.close,
            adj_close = EXCLUDED.adj_close,
            volume = EXCLUDED.volume;
    """

    cur.executemany(insert_query, records)
    conn.commit()
    cur.close()
    conn.close()


def get_latest_date_for_symbol(symbol):
    from storage.connection import get_connection
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT MAX(date) FROM price_data WHERE symbol = %s", (symbol,))
    result = cur.fetchone()[0]
    cur.close()
    conn.close()
    return result
