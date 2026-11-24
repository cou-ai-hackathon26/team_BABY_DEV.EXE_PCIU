
from datetime import datetime, timezone

from urllib.parse import urlsplit

from flask import (
    Blueprint,
    request,
    jsonify,
    g,
    current_app
)

from middleware.auth_middleware import require_auth

from services.risk_service import analyze_risk

from database import analyses_collection


analysis_bp = Blueprint(
    "analysis",
    __name__
)


MIN_TEXT_LENGTH = 20

MAX_TEXT_LENGTH = 50000

ALLOWED_LANGUAGES = ("en", "bn")

ALLOWED_SOURCE_TYPES = (
    "text",
    "pdf",
    "image",
    "url"
)


# =====================================
# 1. Validate Optional Metadata
# =====================================

def clean_metadata(value, max_length):

    if not isinstance(value, str):
        return None

    value = value.strip()

    if not value:
        return None

    return value[:max_length]


# =====================================
# 2. Validate Source URL Metadata
# =====================================

def is_valid_source_url(value):

    if not isinstance(value, str):
        return False

    if len(value) > 2048:
        return False

    try:

        parsed = urlsplit(value)

        return (
            parsed.scheme in ("http", "https")
            and bool(parsed.hostname)
            and not parsed.username
            and not parsed.password
        )

    except ValueError:
        return False


# =====================================
# 3. Analyze Circular API
# =====================================

@analysis_bp.post("/analyze")
@require_auth
def analyze_circular():

    data = request.get_json(
        silent=True
    )


    # Validate request body

    if not isinstance(data, dict):

        return jsonify({

            "success": False,

            "message": "Invalid JSON request."

        }), 400


    text = data.get("text", "")

    language = data.get(
        "language",
        "en"
    )

    source_type = data.get(
        "source_type",
        "text"
    )


    # Validate text

    if not isinstance(text, str):

        return jsonify({

            "success": False,

            "message": "Circular text must be a string."

        }), 400


    text = text.strip()


    if len(text) < MIN_TEXT_LENGTH:

        return jsonify({

            "success": False,

            "message": (
                "Please provide at least "
                "20 characters of circular text."
            )

        }), 400


    if len(text) > MAX_TEXT_LENGTH:

        return jsonify({

            "success": False,

            "message": (
                "Circular text must not exceed "
                "50,000 characters."
            )

        }), 400


    # Validate language

    if language not in ALLOWED_LANGUAGES:

        return jsonify({

            "success": False,

            "message": "Unsupported language."

        }), 400


    # Validate source type

    if source_type not in ALLOWED_SOURCE_TYPES:

        return jsonify({

            "success": False,

            "message": "Unsupported source type."

        }), 400


    # =================================
    # 4. Read Source Metadata
    # =================================

    source_url = None

    file_name = None

    url_title = None


    if source_type == "url":

        source_url = data.get(
            "source_url"
        )

        if isinstance(source_url, str):
            source_url = source_url.strip()

        if not is_valid_source_url(source_url):

            return jsonify({

                "success": False,

                "message": (
                    "A valid source URL is required "
                    "for URL-based analysis."
                )

            }), 400


        url_title = clean_metadata(
            data.get("url_title"),
            300
        )


    elif source_type in ("pdf", "image"):

        file_name = clean_metadata(
            data.get("file_name"),
            255
        )


    # =================================
    # 5. Run ML and Fraud Analysis
    # =================================

    try:

        result = analyze_risk(
            text,
            language
        )

        if not isinstance(result, dict):

            raise ValueError(
                "Invalid analysis result."
            )


        # Generate analysis title

        title = (
            url_title
            or file_name
            or " ".join(text.split())[:65]
            or "Job Circular Analysis"
        )


        # =================================
        # 6. Save Analysis to MongoDB
        # =================================

        analysis_document = {

            **result,

            "user_id": g.user["uid"],

            "title": title,

            "text": text,

            "language": language,

            "source_type": source_type,

            "source_url": source_url,

            "file_name": file_name,

            "url_title": url_title,

            "created_at": datetime.now(
                timezone.utc
            )

        }


        inserted = analyses_collection.insert_one(
            analysis_document
        )


        # =================================
        # 7. Return Analysis Result
        # =================================

        return jsonify({

            "success": True,

            "message": (
                "Circular analyzed successfully."
            ),

            "analysis_id": str(
                inserted.inserted_id
            ),

            "source_type": source_type,

            "source_url": source_url,

            "file_name": file_name,

            "url_title": url_title,

            "result": result

        }), 201


    except Exception:

        current_app.logger.exception(
            "Circular analysis failed"
        )

        return jsonify({

            "success": False,

            "message": (
                "Unable to analyze the circular. "
                "Please check the backend server logs."
            )

        }), 500
