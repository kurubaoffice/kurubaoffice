from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def get_market_summary():
    """
    Placeholder - later can return NIFTY + BankNIFTY summary
    """
    return {"nifty": "Summary will be here", "banknifty": "Summary will be here"}
