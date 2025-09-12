import psycopg2
import pandas as pd

# Connect to your database
conn = psycopg2.connect(
    host="localhost",
    port="5432",
    dbname="tidder_db",
    user="tidder_user",
    password="Kony@123"
)

symbol = '5PAISA'
days = 10

query = """
SELECT date, close
FROM price_data
WHERE symbol = %s
ORDER BY date
LIMIT %s;
"""

df = pd.read_sql(query, conn, params=(symbol, days))
print(df.head())

conn.close()
