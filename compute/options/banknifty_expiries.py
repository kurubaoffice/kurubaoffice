from fetcher.get_banknifty_option_chain import get_banknifty_option_chain

def get_banknifty_expiry_list():
    expiries, _ = get_banknifty_option_chain()
    return expiries
