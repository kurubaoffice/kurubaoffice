import yfinance as yf
from storage.db_reader import get_active_symbols
from storage.db_writer import insert_price_data

def fetch_and_store_price(symbol, start='2024-01-01', end=None):
    df = yf.download(symbol, start=start, end=end)
    df.reset_index(inplace=True)
    insert_price_data(symbol, df)
    print(f"{symbol} stored ✅")

def run_all():
    symbols = get_active_symbols()
    for symbol in symbols:
        try:
            fetch_and_store_price(symbol)
        except Exception as e:
            print(f"⚠️ Error for {symbol}: {e}")

if __name__ == '__main__':
    run_all()
