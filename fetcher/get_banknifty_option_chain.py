from utils.nse_session import get_nse_session

def get_banknifty_option_chain():
    session = get_nse_session()
    url = "https://www.nseindia.com/api/option-chain-indices?symbol=BANKNIFTY"

    response = session.get(url)
    data = response.json()

    expiries = data["records"]["expiryDates"]
    option_chain = data["records"]["data"]

    return expiries, option_chain
