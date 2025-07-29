# composite_sentiment.py
import json
import os
import matplotlib.pyplot as plt
from config.indicator_weights import INDICATOR_WEIGHTS
from compute import sentiment


def compute_composite_sentiment(indicator_outputs: dict, symbol: str) -> dict:
    total_weight = 0
    sentiment_scores = {"bullish": 0, "bearish": 0, "neutral": 0}

    # Compute weighted sentiment
    for name, data in indicator_outputs.items():
        weight = INDICATOR_WEIGHTS.get(name.lower(), 1.0)
        data["weight"] = weight  # Attach back to original data

        if data.get("bullish"):
            sentiment_scores["bullish"] += weight
        elif data.get("bearish"):
            sentiment_scores["bearish"] += weight
        else:
            sentiment_scores["neutral"] += weight

        total_weight += weight

    # Normalize percentages
    bullish_pct = round(100 * sentiment_scores["bullish"] / total_weight, 2)
    bearish_pct = round(100 * sentiment_scores["bearish"] / total_weight, 2)
    neutral_pct = round(100 * sentiment_scores["neutral"] / total_weight, 2)

    # Determine final sentiment
    if bullish_pct >= 60:
        final_signal = "Strong Bullish"
    elif bearish_pct >= 60:
        final_signal = "Strong Bearish"
    elif bullish_pct > bearish_pct:
        final_signal = "Mild Bullish"
    elif bearish_pct > bullish_pct:
        final_signal = "Mild Bearish"
    else:
        final_signal = "Neutral"

    # Plot
    plot_sentiment_weights(indicator_outputs, symbol)

    return {
        "symbol": symbol,
        "final_signal": final_signal,
        "bullish_pct": bullish_pct,
        "bearish_pct": bearish_pct,
        "neutral_pct": neutral_pct,
        "sentiment_weights": indicator_outputs
    }

def plot_sentiment_weights(indicator_outputs: dict, symbol: str):
    labels, weights, colors = [], [], []

    for name, data in indicator_outputs.items():
        weight = float(data.get("weight", 1.0))
        labels.append(name.upper())
        weights.append(weight)

        if data.get("bullish"): colors.append("green")
        elif data.get("bearish"): colors.append("red")
        elif data.get("neutral"): colors.append("gray")
        else: colors.append("blue")

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(labels, weights, color=colors)
    ax.set_title(f"Indicator Sentiment Weights – {symbol}")
    ax.set_ylabel("Weight")
    plt.xticks(rotation=45)
    plt.tight_layout()

    out_path = f"data/processed/sentiment/{symbol.lower().split('.')[0]}_sentiment_weights.png"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    plt.savefig(out_path)
    plt.close()
    print(f"📊 Sentiment weight chart saved: {out_path}")


if __name__ == "__main__":
    test_symbol = "RELIANCE.NS"
    sentiment = sentiment.composite_sentiment(test_symbol)

    print("\n🧠 Composite Sentiment Output:")
    print(json.dumps(sentiment, indent=4))

