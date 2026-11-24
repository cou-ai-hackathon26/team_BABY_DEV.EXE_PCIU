
import pickle
import sklearn
import unicodedata
from pathlib import Path

MODEL_PATH = (
    Path(__file__).resolve().parent
    / "models"
    / "best_circularshield_model.pkl"
)

print("Scikit-learn version:", sklearn.__version__)

with open(MODEL_PATH, "rb") as file:
    model = pickle.load(file)

print("Model loaded successfully!")
print("Model type:", type(model))
print("Model classes:", model.classes_)

samples = [
    (
        "English - Suspicious",
        "Guaranteed job. Pay 500 taka registration fee."
    ),
    (
        "English - Normal",
        "Qualified candidates are invited to submit their CV."
    ),
    (
        "Bangla - Suspicious",
        "চাকরি পেতে ৫০০ টাকা রেজিস্ট্রেশন ফি প্রদান করুন।"
    ),
    (
        "Bangla - Normal",
        "যোগ্য প্রার্থীদের জীবনবৃত্তান্তসহ আবেদন করতে হবে।"
    )
]

for language, text in samples:

    text = unicodedata.normalize("NFKC", text)
    text = " ".join(text.split())

    prediction = model.predict([text])[0]
    probabilities = model.predict_proba([text])[0]

    print("\n-----------------------------")
    print("Sample:", language)
    print("Text:", text)
    print("Prediction:", prediction)

    for label, probability in zip(
        model.classes_, probabilities
    ):
        print(f"Class {label}: {probability * 100:.2f}%")
