import sys
import os
from datetime import datetime
import pandas as pd
import yfinance as yf
from psycopg2 import sql
from dotenv import load_dotenv
from psycopg2 import sql
from psycopg2.extras import execute_values
from datetime import datetime
import numpy as np

# Add project root to path for clean imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from storage.connection import get_connection  # ✅ Handles DB connection + dotenv

# Load environment variables
load_dotenv()

# File paths
DATA_DIR = os.path.join("data", "raw")
os.makedirs(DATA_DIR, exist_ok=True)
OUTPUT_FILE = os.path.join(DATA_DIR, "company_info.csv")


def fetch_stock_list():
    with get_connection() as conn:
        df = pd.read_sql("SELECT symbol FROM stocks WHERE symbol IN ('INFY', 'TCS', 'RELIANCE')", conn)
        print("List pulled as per rule.")
        return df['symbol'].tolist()


def fetch_company_details(symbol):
    try:
        ticker = yf.Ticker(symbol + ".NS")
        info = ticker.info
        return {
            "symbol": symbol,
            "name": info.get("longName") or info.get("shortName"),
            "sector": info.get("sector"),
            "market_cap": round(info.get("marketCap", 0) / 1e7, 2),  # In crores
            "pe_ratio": info.get("trailingPE"),
            "roe": info.get("returnOnEquity") * 100 if info.get("returnOnEquity") else None,
            "eps": info.get("trailingEps"),
            "promoter_holding": None,  # Placeholder
            "institutional_holding": None,  # Placeholder
            "last_updated": datetime.now()
        }
    except Exception as e:
        print(f"[ERROR] {symbol}: {e}")
        return None


from psycopg2.extras import execute_values
from psycopg2 import sql, DatabaseError
from datetime import datetime
import pandas as pd

def insert_into_db(df):
    from psycopg2.extras import execute_values

    # Ensure last_updated is a datetime object
    df['last_updated'] = pd.to_datetime(df['last_updated'])

    with get_connection() as conn:
        cursor = conn.cursor()
        insert_query = sql.SQL("""
            INSERT INTO company_info (
                symbol, name, sector, market_cap, pe_ratio, roe, eps,
                promoter_holding, institutional_holding, last_updated
            )
            VALUES %s
            ON CONFLICT (symbol) DO UPDATE SET
                name = EXCLUDED.name,
                sector = EXCLUDED.sector,
                market_cap = EXCLUDED.market_cap,
                pe_ratio = EXCLUDED.pe_ratio,
                roe = EXCLUDED.roe,
                eps = EXCLUDED.eps,
                promoter_holding = EXCLUDED.promoter_holding,
                institutional_holding = EXCLUDED.institutional_holding,
                last_updated = EXCLUDED.last_updated
        """)

        # Explicitly convert to list of tuples (preserving datetime type)
        values = [tuple(row) for row in df.itertuples(index=False, name=None)]

        print(f"[DB] Preparing to insert {len(values)} records...")
        print("[DB] Sample values (first record):", values[0])

        execute_values(cursor, insert_query, values)
        conn.commit()
        print(f"[DB] Inserted/Updated {len(values)} records into company_info")



def run():
    print("[START] Fetching company info...")
    symbols = fetch_stock_list()
    print(f"[INFO] Total symbols: {len(symbols)}")

    all_data = []
    for i, symbol in enumerate(symbols, start=1):
        print(f"[INFO] symbols: {symbols}")
        try:
            data = fetch_company_details(symbol)
            if data:
                all_data.append(data)
        except Exception as e:
            print(f"[ERROR] {symbol}: {e}")

        if i % 500 == 0:
            print(f"[PROGRESS] Processed {i}/{len(symbols)}")

    df = pd.DataFrame(all_data)
    df.to_csv("data/raw/company_info.csv", index=False)
    print(f"[CSV] Saved company info to data\\raw\\company_info.csv")

    insert_into_db(df)


if __name__ == "__main__":
    run()
