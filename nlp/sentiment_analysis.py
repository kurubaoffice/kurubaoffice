# nlp/sentiment_analysis.py
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Custom finance lexicon
FINANCE_LEXICON = {
    "bullish": 2.0,
    "bearish": -2.0,
    "breakout": 1.5,
    "rally": 1.5,
    "crash": -2.5,
    "dump": -2.0,
    "surge": 1.5,
    "plunge": -2.5,
    "resistance": -0.2,
    "support": 0.2
}

# Initialize analyzer
analyzer = SentimentIntensityAnalyzer()

# Add finance-specific words
analyzer.lexicon.update(FINANCE_LEXICON)


def get_sentiment_label(text: str) -> dict:
    """
    Returns sentiment analysis result for a given text.
    Output: {
        "label": "positive" | "negative" | "neutral",
        "score": compound_score
    }
    """
    if not text.strip():
        return {"label": "neutral", "score": 0.0}

    scores = analyzer.polarity_scores(text)
    compound = scores['compound']

    if compound >= 0.05:
        label = "positive"
    elif compound <= -0.05:
        label = "negative"
    else:
        label = "neutral"

    return {"label": label, "score": round(compound, 3)}
