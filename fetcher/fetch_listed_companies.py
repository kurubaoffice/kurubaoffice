import os
import pandas as pd
import requests
from io import StringIO
from storage.connection import get_connection

# Set absolute base path to project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data", "raw")

def fetch_and_save_companies(url, output_filename, filter_series="EQ"):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.nseindia.com"
    }

    print(f"[INFO] Fetching data from: {url}")
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"[ERROR] Failed to fetch data from {url} - Status Code: {response.status_code}")
        return None

    df = pd.read_csv(StringIO(response.text))

    # Normalize column names
    df.columns = [col.strip().upper().replace(" ", "_") for col in df.columns]

    # Filter by series
    if filter_series and "SERIES" in df.columns:
        df = df[df["SERIES"] == filter_series]

    # Rename columns
    if "NAME_OF_COMPANY" in df.columns:
        df = df.rename(columns={"NAME_OF_COMPANY": "name"})
    elif "NAME__OF__COMPANY" in df.columns:
        df = df.rename(columns={"NAME__OF__COMPANY": "name"})

    df = df.rename(columns={"SYMBOL": "symbol"})

    # Clean up and sort
    df = df[["symbol", "name"]].dropna().drop_duplicates().sort_values(by="symbol")

    # Save to correct data/raw/ folder
    os.makedirs(DATA_DIR, exist_ok=True)
    output_path = os.path.join(DATA_DIR, output_filename)
    df.to_csv(output_path, index=False)

    print(f"[INFO] Saved {len(df)} companies to {output_path}")

    return df


def insert_stocks_into_db(df):
    conn = get_connection()
    cursor = conn.cursor()

    insert_query = """
    INSERT INTO stocks (symbol, name)
    VALUES (%s, %s)
    ON CONFLICT (symbol) DO UPDATE SET name = EXCLUDED.name;
    """

    data_to_insert = df.to_records(index=False).tolist()
    cursor.executemany(insert_query, data_to_insert)

    conn.commit()
    cursor.close()
    conn.close()
    print(f"[INFO] Inserted/Updated {len(data_to_insert)} stocks into DB.")


def run():
    print("[START] Fetching all listed companies...")

    # Main Board
    main_url = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
    main_df = fetch_and_save_companies(main_url, "listed_companies.csv")

    # SME Board
    sme_url = "https://nsearchives.nseindia.com/emerge/corporates/content/SME_EQUITY_L.csv"
    sme_df = fetch_and_save_companies(sme_url, "listed_sme_companies.csv", filter_series=None)

    # Merge and insert
    combined_df = pd.concat([main_df, sme_df]).drop_duplicates().reset_index(drop=True)
    print(f"[INFO] Total unique stocks to insert: {len(combined_df)}")
    insert_stocks_into_db(combined_df)

    print("[DONE] Stock list loaded into DB.")


if __name__ == "__main__":
    run()
