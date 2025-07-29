import matplotlib.pyplot as plt

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
    print(f"📊 Sentiment weight chart saved: {out_path}")
