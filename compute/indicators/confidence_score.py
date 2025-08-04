def compute_confidence_score(signals: dict) -> float:
    """
    Compute confidence score (0–100%) from signal dict using weighted bullish/bearish scoring.
    """
    if not isinstance(signals, dict) or not signals:
        return 0.0

    weights = {
        "MACD": 1.2,
        "RSI": 1.0,
        "Supertrend": 1.5,
        "EMA": 1.0,
        "ADX": 0.8,
        "Stochastic": 0.7,
        "Momentum": 0.6
    }

    positive_signals = {"Bullish", "Buy", "Strong Buy"}
    negative_signals = {"Bearish", "Sell", "Strong Sell"}

    score = 0.0
    total_weight = 0.0

    for key, val in signals.items():
        weight = weights.get(key, 1.0)  # Default to 1 if not listed
        total_weight += weight
        if val in positive_signals:
            score += weight
        elif val in negative_signals:
            score -= weight

    if total_weight == 0:
        return 50.0  # Neutral

    normalized_score = max(min(score / total_weight, 1.0), -1.0)
    confidence = round((normalized_score + 1) * 50, 2)

    return confidence
