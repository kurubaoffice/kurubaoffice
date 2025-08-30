from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import os

app = FastAPI()

# Allow frontend (5173) to access backend (8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # you can also use ["*"] for all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
RAW_COMPANY_LIST = os.path.join(BASE_DIR, "data", "raw", "listed_companies.csv")

@app.get("/stocks")
def get_stock_list():
    df = pd.read_csv(RAW_COMPANY_LIST)
    df.columns = df.columns.str.strip().str.lower()
    return df[["symbol", "name"]].to_dict(orient="records")

@app.get("/stock/{symbol}")
def get_stock(symbol: str):
    return {"symbol": symbol, "price": 123.45, "history": []}
