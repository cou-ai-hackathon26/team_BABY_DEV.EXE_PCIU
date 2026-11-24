
from pathlib import Path

from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import RequestEntityTooLarge

from config import Config

from database import (
    check_database_connection,
    initialize_indexes
)

from firebase_config import initialize_firebase


# ==========================================
# Import All API Blueprints
# ==========================================

from routes.analysis_routes import analysis_bp
from routes.extraction_routes import extraction_bp
from routes.user_routes import user_bp
from routes.url_routes import url_bp
from routes.dashboard_routes import dashboard_bp
from routes.history_routes import history_bp
from routes.admin_dashboard_routes import admin_dashboard_bp
from routes.admin_user_routes import admin_user_bp


# ==========================================
# 1. Initialize Flask Application
# ==========================================

app = Flask(__name__)

app.config.from_object(Config)


# ==========================================
# 2. Configure CORS
# ==========================================

allowed_origins = list(set([
    Config.CLIENT_URL.rstrip("/"),
    "http://localhost:5173",
    "http://127.0.0.1:5173"
]))

CORS(
    app,
    resources={
        r"/api/.*": {
            "origins": allowed_origins,

            "methods": [
                "GET",
                "POST",
                "PUT",
                "PATCH",
                "DELETE",
                "OPTIONS"
            ],

            "allow_headers": [
                "Content-Type",
                "Authorization",
                "Accept"
            ]
        }
    }
)


# ==========================================
# 3. Initialize Firebase Admin SDK
# ==========================================

initialize_firebase()


# ==========================================
# 4. Initialize MongoDB Indexes
# ==========================================

initialize_indexes()


# ==========================================
# 5. Create Upload Directory
# ==========================================

Config.UPLOAD_FOLDER.mkdir(
    parents=True,
    exist_ok=True
)


# ==========================================
# 6. Register All API Blueprints
# ==========================================

# Circular Analysis
app.register_blueprint(
    analysis_bp,
    url_prefix="/api"
)

# PDF and Image Extraction
app.register_blueprint(
    extraction_bp,
    url_prefix="/api"
)

# User Registration and Authentication
app.register_blueprint(
    user_bp,
    url_prefix="/api"
)

# URL Text Extraction
app.register_blueprint(
    url_bp,
    url_prefix="/api"
)

# User Dashboard
app.register_blueprint(
    dashboard_bp,
    url_prefix="/api"
)

# Analysis History
app.register_blueprint(
    history_bp,
    url_prefix="/api"
)

# Admin Dashboard
app.register_blueprint(
    admin_dashboard_bp,
    url_prefix="/api"
)

# Admin User Management
app.register_blueprint(
    admin_user_bp,
    url_prefix="/api"
)


# ==========================================
# 7. Home API
# ==========================================

@app.get("/")
def home():

    return jsonify({
        "success": True,
        "message": "Welcome to CircularShield Backend",
        "application": Config.APP_NAME,
        "version": "1.0.0"
    }), 200


# ==========================================
# 8. Health Check API
# ==========================================

@app.get("/api/health")
def health():

    database_connected = check_database_connection()

    model_available = Path(
        Config.MODEL_PATH
    ).is_file()

    ocr_available = Path(
        Config.TESSERACT_CMD
    ).is_file()

    return jsonify({

        "success": database_connected,

        "application": Config.APP_NAME,

        "version": "1.0.0",

        "status": (
            "running"
            if database_connected
            else "degraded"
        ),

        "database": (
            "connected"
            if database_connected
            else "disconnected"
        ),

        "model_file_available": model_available,

        "ocr_executable_available": ocr_available,

        "registered_modules": {
            "circular_analysis": True,
            "file_extraction": True,
            "url_extraction": True,
            "user_management": True,
            "user_dashboard": True,
            "analysis_history": True,
            "admin_dashboard": True,
            "admin_user_management": True
        }

    }), 200 if database_connected else 503


# ==========================================
# 9. Bad Request Error Handler
# ==========================================

@app.errorhandler(400)
def handle_bad_request(error):

    return jsonify({
        "success": False,
        "message": "Invalid request."
    }), 400


# ==========================================
# 10. Unauthorized Error Handler
# ==========================================

@app.errorhandler(401)
def handle_unauthorized(error):

    return jsonify({
        "success": False,
        "message": "Authentication required."
    }), 401


# ==========================================
# 11. Forbidden Error Handler
# ==========================================

@app.errorhandler(403)
def handle_forbidden(error):

    return jsonify({
        "success": False,
        "message": "You do not have permission to access this resource."
    }), 403


# ==========================================
# 12. Not Found Error Handler
# ==========================================

@app.errorhandler(404)
def handle_not_found(error):

    return jsonify({
        "success": False,
        "message": "API endpoint not found."
    }), 404


# ==========================================
# 13. Method Not Allowed Error Handler
# ==========================================

@app.errorhandler(405)
def handle_method_not_allowed(error):

    return jsonify({
        "success": False,
        "message": "HTTP method not allowed."
    }), 405


# ==========================================
# 14. Maximum File Size Error Handler
# ==========================================

@app.errorhandler(RequestEntityTooLarge)
def handle_large_file(error):

    return jsonify({
        "success": False,
        "message": "Maximum upload size exceeded."
    }), 413


# ==========================================
# 15. Internal Server Error Handler
# ==========================================

@app.errorhandler(500)
def handle_server_error(error):

    app.logger.error(
        "Internal server error: %s",
        error
    )

    return jsonify({
        "success": False,
        "message": "Internal server error. Please try again."
    }), 500


# ==========================================
# 16. Start Flask Development Server
# ==========================================

if __name__ == "__main__":

    database_connected = check_database_connection()

    model_available = Path(
        Config.MODEL_PATH
    ).is_file()

    ocr_available = Path(
        Config.TESSERACT_CMD
    ).is_file()

    print("\n==========================================")
    print("         CircularShield Backend")
    print("==========================================")

    print(f"Application : {Config.APP_NAME}")

    print(
        f"Server      : http://127.0.0.1:{Config.PORT}"
    )

    print(f"Debug Mode  : {Config.DEBUG}")

    print(
        "MongoDB     : "
        + (
            "Connected"
            if database_connected
            else "Disconnected"
        )
    )

    print(
        "ML Model    : "
        + (
            "Available"
            if model_available
            else "Not Found"
        )
    )

    print(
        "Tesseract   : "
        + (
            "Available"
            if ocr_available
            else "Not Found"
        )
    )

    print(f"CORS Origins: {allowed_origins}")

    print("\nRegistered API Routes:")
    print("------------------------------------------")

    for rule in sorted(
        app.url_map.iter_rules(),
        key=lambda item: item.rule
    ):

        methods = ", ".join(
            sorted(
                rule.methods - {"HEAD", "OPTIONS"}
            )
        )

        print(f"{methods:18} {rule.rule}")

    print("==========================================\n")

    app.run(
        host="127.0.0.1",
        port=Config.PORT,
        debug=Config.DEBUG,
        use_reloader=False
    )
