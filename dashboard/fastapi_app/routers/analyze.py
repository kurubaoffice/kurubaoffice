from fastapi import APIRouter
from compute.apply_indicators import apply_indicators
from reporting.format_report import format_stock_summary
import os
import pandas as pd
from fastapi import APIRouter
from compute.apply_indicators import apply_indicators
from reporting.format_report import format_stock_summary


router = APIRouter()

DATA_PATH = "data/processed/stocks"

@router.get("/{symbol}")
def analyze_stock(symbol: str):
    """
    Run analysis on a given stock symbol and return summary.
    """
    try:
        file_path = os.path.join(DATA_PATH, f"{symbol.upper()}.csv")
        if not os.path.exists(file_path):
            return {"error": f"No data found for {symbol}"}

        # Load stock data
        df = pd.read_csv(file_path)

        # Apply indicators (your existing pipeline)
        df_indicators = apply_indicators(df)

        # Generate summary report
        report = format_stock_summary(symbol, df_indicators)

        return {
            "symbol": symbol.upper(),
            "report": report,
            "last_date": str(df["Date"].iloc[-1]) if "Date" in df.columns else None
        }

    except Exception as e:
        return {"error": str(e)}