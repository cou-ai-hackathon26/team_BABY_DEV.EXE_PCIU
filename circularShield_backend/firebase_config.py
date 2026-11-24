
import firebase_admin
from firebase_admin import credentials
from config import Config


def initialize_firebase():

    try:
        return firebase_admin.get_app()

    except ValueError:

        if not Config.FIREBASE_CREDENTIALS.is_file():
            raise FileNotFoundError(
                "Firebase credentials file not found"
            )

        credential = credentials.Certificate(
            str(Config.FIREBASE_CREDENTIALS)
        )

        app = firebase_admin.initialize_app(
            credential
        )

        print("Firebase Admin initialized successfully!")

        return app
