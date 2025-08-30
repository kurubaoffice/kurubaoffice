from fastapi import FastAPI
import pandas as pd

app = FastAPI()

@app.get("/stocks")
def get_stock_list():
    # Load your master NSE companies file
    df = pd.read_csv("data/raw/listed_companies.csv")
    df.columns = df.columns.str.strip().str.lower()  # normalize
    return df[["symbol", "name"]].to_dict(orient="records")

