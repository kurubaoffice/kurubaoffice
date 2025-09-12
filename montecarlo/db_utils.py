import os
import numpy as np
import pandas as pd
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()

DB_CONFIG = {
    'dbname': os.getenv("DB_NAME"),
    'user': os.getenv("DB_USER"),
    'password': os.getenv("DB_PASSWORD"),
    'host': os.getenv("DB_HOST", "localhost"),
    'port': int(os.getenv("DB_PORT", 5432))
}


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)


def get_mu_sigma_from_db(symbol: str, days: int = 252):
    query = """
    SELECT date, close
    FROM price_data
    WHERE symbol = %s
    ORDER BY date
    LIMIT %s;
    """

    with get_db_connection() as conn:
        df = pd.read_sql(query, conn, params=(symbol.upper(), days + 1))
        print(df.head(10))

    df = df.dropna()  # Clean up any unexpected nulls

    # ✅ Ensure date is datetime and sorted oldest → latest
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    # ✅ Ensure numeric (should be already, but just in case)
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna(subset=["close"])  # Drop rows with invalid closes

    # ✅ Calculate daily returns
    df["return"] = df["close"].pct_change(fill_method=None)
    df = df.dropna(subset=["return"])  # Drop first row with NaN return

    # ✅ Final sanity check
    if df["return"].empty or df["close"].empty:
        raise ValueError(f"No valid return data found for {symbol}")

    mu = df["return"].mean() * 252  # Annualized return
    sigma = df["return"].std() * np.sqrt(252)  # Annualized volatility
    S0 = df["close"].iloc[-1]  # Latest closing price

    print(f"📈 {symbol.upper()} | mu: {mu:.4f}, sigma: {sigma:.4f}, S0: {S0:.2f}")
    return mu, sigma, S0


