import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from    sklearn.svm import LinearSVC
import os


training_data = [
    ("hi", "greeting"),
    ("hello", "greeting"),
    ("good morning", "greeting"),

    ("thanks", "thanks"),
    ("thank you", "thanks"),

    ("reliance chart", "technical_analysis"),
    ("give me tata motors levels", "technical_analysis"),
    ("show indicators for infosys", "technical_analysis"),

    ("reliance", "stock_query"),
    ("tcs", "stock_query"),
    ("icici bank analysis", "stock_query"),

    ("stoploss?", "stoploss"),
    ("what is sl for reliance", "stoploss"),
    ("give sl", "stoploss"),

    ("target?", "target"),
    ("expected target for hdfc", "target"),

    ("should I hold", "hold_or_sell"),
    ("hold or sell?", "hold_or_sell"),

    ("future outlook", "future_outlook"),
    ("next week view", "future_outlook"),

    ("please help", "unknown"),
    ("idk what to do", "unknown"),
]

texts = [t[0] for t in training_data]
labels = [t[1] for t in training_data]

vectorizer = TfidfVectorizer()
X = vectorizer.fit_transform(texts)

model = LinearSVC()
model.fit(X, labels)

with open("model.pkl", "wb") as f:
    pickle.dump(model, f)

with open("vectorizer.pkl", "wb") as f:
    pickle.dump(vectorizer, f)

print("Intent model trained and saved.")
