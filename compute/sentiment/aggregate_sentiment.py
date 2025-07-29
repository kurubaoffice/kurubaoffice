def aggregate_sentiment(indicator_outputs: dict) -> dict:
    bullish_score = bearish_score = neutral_score = 0.0
    total_weight = 0.0
    details = {}

    for name, output in indicator_outputs.items():
        weight = float(output.get("weight", 1.0))
        total_weight += weight

        if output.get("bullish"):
            bullish_score += weight
            sentiment = "bullish"
        elif output.get("bearish"):
            bearish_score += weight
            sentiment = "bearish"
        elif output.get("neutral"):
            neutral_score += weight
            sentiment = "neutral"
        else:
            sentiment = "unknown"

        details[name] = {
            "sentiment": sentiment,
            "weight": weight
        }

    # Final sentiment decision based on weighted scores
    def percent(score): return round((score / total_weight) * 100, 1) if total_weight else 0

    if total_weight == 0:
        final_sentiment = "No Data"
    elif bullish_score >= 0.75 * total_weight:
        final_sentiment = "Strong Bullish"
    elif bearish_score >= 0.75 * total_weight:
        final_sentiment = "Strong Bearish"
    elif bullish_score > bearish_score:
        final_sentiment = "Weak Bullish"
    elif bearish_score > bullish_score:
        final_sentiment = "Weak Bearish"
    else:
        final_sentiment = "Neutral"

    return {
        "final_sentiment": final_sentiment,
        "bullish_score": round(bullish_score, 2),
        "bearish_score": round(bearish_score, 2),
        "neutral_score": round(neutral_score, 2),
        "bullish_percent": percent(bullish_score),
        "bearish_percent": percent(bearish_score),
        "neutral_percent": percent(neutral_score),
        "total_weight": round(total_weight, 2),
        "indicator_breakdown": details
    }


# Optional test
if __name__ == "__main__":
    sample = {
        "rsi": {"bullish": True, "weight": 1.2},
        "macd": {"bearish": True, "weight": 1.0},
        "supertrend": {"bullish": True, "weight": 0.8},
        "adx": {"neutral": True, "weight": 0.5},
    }
    result = aggregate_sentiment(sample)
    print("🧠 Composite Sentiment (Weighted):")
    from pprint import pprint
    pprint(result)
