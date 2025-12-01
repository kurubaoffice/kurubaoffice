from compute.options.rr_engine import process_option_rr_telegram

def analyze_fno_stock(symbol: str, expiry: str = None, rr: float = 2.0):
    """
    New FnO analysis wrapper (Telegram friendly).
    Uses updated RR Engine with strict filtering + minimal clean output.
    """
    try:
        # If expiry is not given, engine will auto-select nearest
        result = process_option_rr_telegram(
            msg=symbol,
            expiry=expiry,
            desired_rr=rr,
            minimal_output=True
        )
        return result
    except Exception as e:
        return {"error": str(e)}
