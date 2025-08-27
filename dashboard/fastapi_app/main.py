from fastapi import FastAPI
from .routers import analyze, summary, backtest


app = FastAPI(
    title="Tidder 2.0 Backend",
    description="FastAPI backend for stock analysis, reporting and backtesting",
    version="0.1.0"
)

# Routers
app.include_router(analyze.router, prefix="/analyze", tags=["Analyze"])
app.include_router(summary.router, prefix="/summary", tags=["Summary"])
app.include_router(backtest.router, prefix="/backtest", tags=["Backtest"])

@app.get("/")
def root():
    return {"message": "Welcome to Tidder 2.0 FastAPI backend"}
