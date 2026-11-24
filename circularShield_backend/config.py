
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")


class Config:

    # Application configuration
    APP_NAME = os.getenv("APP_NAME", "CircularShield")
    PORT = int(os.getenv("PORT", 5000))
    DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"

    # Frontend configuration
    CLIENT_URL = os.getenv(
        "CLIENT_URL", "http://localhost:5173"
    )

    # MongoDB configuration
    MONGODB_URI = os.getenv("MONGODB_URI")
    DATABASE_NAME = os.getenv(
        "DATABASE_NAME", "circularShield"
    )

    # Firebase configuration
    FIREBASE_CREDENTIALS = BASE_DIR / os.getenv(
        "FIREBASE_CREDENTIALS",
        "credentials/firebase-admin.json"
    )

    # Machine learning configuration
    MODEL_PATH = BASE_DIR / os.getenv(
        "MODEL_PATH",
        "models/best_circularshield_model.pkl"
    )

    # Tesseract OCR configuration
    TESSERACT_CMD = os.getenv(
        "TESSERACT_CMD",
        "C:/Program Files/Tesseract-OCR/tesseract.exe"
    )

    OCR_LANGUAGES = os.getenv(
        "OCR_LANGUAGES", "ben+eng"
    )

    # File upload configuration
    MAX_FILE_SIZE = int(
        os.getenv("MAX_FILE_SIZE", 10485760)
    )

    MAX_CONTENT_LENGTH = MAX_FILE_SIZE + 1024 * 1024

    UPLOAD_FOLDER = BASE_DIR / os.getenv(
        "UPLOAD_FOLDER", "uploads"
    )
