import numpy as np
import pandas as pd
from sqlalchemy import create_engine
import matplotlib.pyplot as plt
import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

# --- CONFIG ---
load_dotenv()

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = quote_plus(os.getenv("DB_PASSWORD"))
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

DB_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

SYMBOL = "EPACK"
DAYS = 100  # Historical days to use for stats
FUTURE_DAYS = 30  # Days to forecast
SIMULATIONS = 1000  # Monte Carlo runs

# --- FUNCTION TO SIMULATE GEOMETRIC BROWNIAN MOTION ---
def simulate_gbm(S0, mu, sigma, days):
    dt = 1
    prices = [S0]
    for _ in range(days):
        # Random shock
        shock = np.random.normal(loc=mu * dt, scale=sigma * np.sqrt(dt))
        price = prices[-1] * np.exp(shock)
        prices.append(price)
    return prices

# --- LOAD DATA ---
engine = create_engine(DB_URL)

query = """
SELECT date, close
FROM price_data
WHERE symbol = %s
ORDER BY date DESC
LIMIT %s
"""

df = pd.read_sql(query, engine, params=(SYMBOL, DAYS))
df = df.sort_values("date")  # chronological order
df["return"] = df["close"].pct_change()
df.dropna(inplace=True)

# --- STATISTICS ---
mu = df["return"].mean()
sigma = df["return"].std()
S0 = df["close"].iloc[-1]

print(f"📈 {SYMBOL} | μ: {mu:.6f}, σ: {sigma:.6f}, S₀: {S0:.2f}")

# --- MONTE CARLO SIMULATION ---
simulations = []

for i in range(SIMULATIONS):
    prices = simulate_gbm(S0, mu, sigma, FUTURE_DAYS)
    simulations.append(pd.Series(prices, name=f"Sim_{i}"))

simulation_df = pd.concat(simulations, axis=1)

# --- PLOT RESULTS ---
plt.figure(figsize=(12, 6))
plt.plot(simulation_df, color='lightblue', alpha=0.1)
plt.title(f"Monte Carlo Simulation ({SIMULATIONS} runs) for {SYMBOL}")
plt.xlabel("Days")
plt.ylabel("Price")
plt.grid(True)
plt.tight_layout()
plt.show()

# --- ANALYSIS & SUMMARY ---
end_prices = simulation_df.iloc[-1]
expected_price = end_prices.mean()
lower_bound = end_prices.quantile(0.05)
upper_bound = end_prices.quantile(0.95)
prob_up = (end_prices > S0).mean() * 100

summary = f"""
Monte Carlo Projection for {SYMBOL}:

- Starting price (S₀): ₹{S0:.2f}
- Expected price after {FUTURE_DAYS} days: ₹{expected_price:.2f}
- 90% confidence interval: ₹{lower_bound:.2f} - ₹{upper_bound:.2f}
- Probability price increases: {prob_up:.2f}%
"""

print(summary)
