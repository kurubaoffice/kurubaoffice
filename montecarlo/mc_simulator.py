import numpy as np
import matplotlib.pyplot as plt


def monte_carlo_stock_price(S0, mu, sigma, T=1, steps=252, simulations=1000):
    """
    Simulate future stock prices using Monte Carlo and Geometric Brownian Motion.

    Args:
        S0 (float): Starting stock price
        mu (float): Expected annual return (drift)
        sigma (float): Annual volatility
        T (float): Time horizon in years (default 1 year)
        steps (int): Number of time steps
        simulations (int): Number of simulations to run

    Returns:
        np.ndarray: A (simulations x steps+1) array of simulated price paths
    """


    dt = T / steps
    price_paths = np.zeros((simulations, steps + 1))
    price_paths[:, 0] = S0

    for t in range(1, steps + 1):
        z = np.random.standard_normal(simulations)
        price_paths[:, t] = price_paths[:, t - 1] * np.exp((mu - 0.5 * sigma ** 2) * dt + sigma * np.sqrt(dt) * z)

    return price_paths


def plot_simulation(price_paths, symbol="STOCK"):
    """
    Plot Monte Carlo simulated paths.
    """
    plt.figure(figsize=(10, 6))
    for path in price_paths[:50]:  # plot only 50 paths to avoid clutter
        plt.plot(path, linewidth=0.5)
    plt.title(f"Monte Carlo Simulation for {symbol}")
    plt.xlabel("Days")
    plt.ylabel("Price")
    plt.grid(True)
    plt.tight_layout()
    plt.show()
