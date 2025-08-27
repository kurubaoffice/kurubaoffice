from fastapi import APIRouter

router = APIRouter()

@router.get("/{symbol}")
def run_backtest(symbol: str):
    """
    Placeholder - will connect to backtest/ziplime_runner.py later
    """
    return {"symbol": symbol, "backtest": "Backtest results will be added soon"}
