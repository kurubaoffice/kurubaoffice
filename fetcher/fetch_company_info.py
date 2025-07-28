import sys
import os
from datetime import datetime
import pandas as pd
import yfinance as yf
from psycopg2 import sql
from dotenv import load_dotenv
from psycopg2.extras import execute_values
import numpy as np

# Project Root (always global, e.g., Tidder2.0/)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(PROJECT_ROOT)

# Load environment variables
load_dotenv()

# Global Data Folder
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
os.makedirs(DATA_DIR, exist_ok=True)
OUTPUT_FILE = os.path.join(DATA_DIR, "company_info.csv")
SKIPPED_FILE = os.path.join(DATA_DIR, "skipped_symbols.txt")

from storage.connection import get_connection


def fetch_stock_list():
    with get_connection() as conn:
        df = pd.read_sql("SELECT symbol FROM stocks", conn)
        print("✅ Pulled stock list from DB.")
        print(f"ℹ️ Total symbols fetched: {len(df)}")
        return df['symbol'].tolist()


def fetch_company_details(symbol):
    try:
        ticker = yf.Ticker(symbol + ".NS")
        info = ticker.info
        if not info or 'longName' not in info:
            return None
        return {
            "symbol": symbol,
            "name": info.get("longName") or info.get("shortName"),
            "sector": info.get("sector"),
            "market_cap": round(info.get("marketCap", 0) / 1e7, 2),  # in Crores
            "pe_ratio": info.get("trailingPE"),
            "roe": info.get("returnOnEquity") * 100 if info.get("returnOnEquity") else None,
            "eps": info.get("trailingEps"),
            "promoter_holding": None,  # To be filled later
            "institutional_holding": None,
            "last_updated": datetime.now()
        }
    except Exception as e:
        print(f"[ERROR] {symbol}: {e}")
        return None


def insert_into_db(df):
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

        values = [tuple(row) for row in df.itertuples(index=False, name=None)]

        print(f"[DB] Preparing to insert {len(values)} records...")
        if values:
            print("[DEBUG] First record preview:", values[0])

        execute_values(cursor, insert_query, values)
        conn.commit()
        print(f"[DB] Inserted/Updated {len(values)} records into company_info")


def run():
    print("[START] Fetching company info...")
    symbols = fetch_stock_list()

    all_data = []
    skipped = []

    for i, symbol in enumerate(symbols, start=1):
        print(f"[INFO] Processing: {symbol}")
        data = fetch_company_details(symbol)
        if data:
            all_data.append(data)
        else:
            skipped.append(symbol)

        if i % 100 == 0 or i == len(symbols):
            print(f"[PROGRESS] {i}/{len(symbols)} processed")

    df = pd.DataFrame(all_data)

    df.to_csv(OUTPUT_FILE, index=False)
    print(f"[CSV] Saved company info to {OUTPUT_FILE}")

    if skipped:
        with open(SKIPPED_FILE, "w") as f:
            f.write("\n".join(skipped))
        print(f"[SKIPPED] {len(skipped)} symbols skipped. Logged to {SKIPPED_FILE}")

    if not df.empty:
        insert_into_db(df)
    else:
        print("[DB] No valid data to insert.")


if __name__ == "__main__":
    run()
