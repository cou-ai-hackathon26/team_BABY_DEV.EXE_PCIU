
from flask import (
    Blueprint,
    request,
    jsonify,
    current_app
)

from middleware.auth_middleware import require_auth

from services.url_service import (
    extract_text_from_url,
    URLExtractionError
)


url_bp = Blueprint(
    "url",
    __name__
)


# =====================================
# Extract Text from URL API
# =====================================

@url_bp.post("/extract-url")
@require_auth
def extract_url():

    data = request.get_json(
        silent=True
    )

    if not isinstance(data, dict):

        return jsonify({

            "success": False,

            "message": "Invalid JSON request."

        }), 400


    url = data.get("url", "")

    language = data.get(
        "language",
        "en"
    )


    # Validate URL

    if (
        not isinstance(url, str)
        or not url.strip()
    ):

        return jsonify({

            "success": False,

            "message": "Please provide a valid URL."

        }), 400


    # Validate language

    if language not in ("en", "bn"):

        return jsonify({

            "success": False,

            "message": "Unsupported language."

        }), 400


    try:

        result = extract_text_from_url(
            url.strip(),
            language
        )

        return jsonify(result), 200


    except URLExtractionError as error:

        return jsonify({

            "success": False,

            "message": str(error)

        }), 422


    except Exception:

        current_app.logger.exception(
            "URL extraction failed"
        )

        return jsonify({

            "success": False,

            "message": (
                "An unexpected error occurred "
                "during URL extraction."
            )

        }), 500
