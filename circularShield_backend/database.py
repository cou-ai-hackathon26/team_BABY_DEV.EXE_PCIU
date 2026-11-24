
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from config import Config

if not Config.MONGODB_URI:
    raise RuntimeError("MONGODB_URI is missing from .env")

# Initialize MongoDB client
client = MongoClient(
    Config.MONGODB_URI,
    serverSelectionTimeoutMS=5000
)

# Select database
db = client[Config.DATABASE_NAME]

# Database collections
users_collection = db["users"]

analyses_collection = db["analyses"]

organizations_collection = db["organizations"]

reports_collection = db["scam_reports"]

alerts_collection = db["scam_alerts"]

scam_reports_collection = db["scam_reports"]

organizations_collection = db["organizations"]


# Test database connection
def check_database_connection():

    try:
        client.admin.command("ping")

        print("MongoDB connected successfully!")
        print("Database:", db.name)

        return True

    except PyMongoError as error:

        print("MongoDB connection failed!")
        print("Error type:", type(error).__name__)

        return False


def initialize_indexes():

    # Unique Firebase user UID
    users_collection.create_index(
        "uid",
        unique=True
    )

    # User analysis history
    analyses_collection.create_index([
        ("user_id", 1),
        ("created_at", -1)
    ])

    # User risk statistics
    analyses_collection.create_index([
        ("user_id", 1),
        ("risk_level", 1)
    ])