from utils.nse_session import get_nse_session

def get_banknifty_price():
    session = get_nse_session()
    url = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20BANK"
    response = session.get(url).json()

    last_price = response["data"][0]["last"]
    return float(last_price)
