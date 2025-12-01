import pickle
import os

# Base directory where THIS file lives
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Always load models relative to this folder
MODEL_PATH = os.path.join(BASE_DIR, "model.pkl")
VEC_PATH = os.path.join(BASE_DIR, "vectorizer.pkl")

# Optional: ensure directory exists (useful for training script)
os.makedirs(BASE_DIR, exist_ok=True)

# Load model + vectorizer
with open(MODEL_PATH, "rb") as f:
    MODEL = pickle.load(f)

with open(VEC_PATH, "rb") as f:
    VEC = pickle.load(f)

def predict_intent(text: str) -> str:
    x = VEC.transform([text])
    pred = MODEL.predict(x)[0]
    return pred
