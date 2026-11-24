
import pickle
import unicodedata
from functools import lru_cache
from config import Config


# Load model only once
@lru_cache(maxsize=1)
def load_model():

    if not Config.MODEL_PATH.is_file():
        raise FileNotFoundError(
            "Trained model file not found"
        )

    with open(Config.MODEL_PATH, "rb") as file:
        model = pickle.load(file)

    print("Bilingual Linear SVC model loaded!")

    return model


# Text preprocessing
def preprocess_text(text):

    if not isinstance(text, str):
        raise ValueError("Text must be a string")

    text = unicodedata.normalize("NFKC", text)

    text = " ".join(text.split())

    if not text:
        raise ValueError("Circular text is empty")

    return text


# Predict circular
def predict_circular(text):

    text = preprocess_text(text)

    model = load_model()

    prediction = model.predict([text])[0]

    probabilities = model.predict_proba([text])[0]

    class_probabilities = {
        int(label): float(probability)
        for label, probability in zip(
            model.classes_, probabilities
        )
    }

    real_probability = class_probabilities[0]
    fake_probability = class_probabilities[1]

    return {
        "prediction": int(prediction),

        "label": (
            "fake" if int(prediction) == 1
            else "real"
        ),

        "real_probability": round(
            real_probability * 100, 2
        ),

        "fake_probability": round(
            fake_probability * 100, 2
        ),

        "confidence": round(
            class_probabilities[int(prediction)] * 100,
            2
        ),

        "model": "Bilingual Linear SVC"
    }
