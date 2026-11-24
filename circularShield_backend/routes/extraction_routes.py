
from flask import (
    Blueprint,
    request,
    jsonify,
    current_app
)

from pathlib import Path
from uuid import uuid4

from PIL import UnidentifiedImageError
from werkzeug.exceptions import RequestEntityTooLarge

from middleware.auth_middleware import require_auth
from services.extraction_service import extract_text
from config import Config


extraction_bp = Blueprint("extraction", __name__)

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg"
}


@extraction_bp.post("/extract")
@require_auth
def extract_circular():

    if "file" not in request.files:

        return jsonify({
            "success": False,
            "message": "No file provided"
        }), 400

    file = request.files["file"]

    language = request.form.get(
        "language",
        "en"
    )

    if language not in ("en", "bn"):

        return jsonify({
            "success": False,
            "message": "Unsupported language"
        }), 400

    if not file.filename:

        return jsonify({
            "success": False,
            "message": "No file selected"
        }), 400

    extension = Path(
        file.filename
    ).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:

        return jsonify({
            "success": False,
            "message": "Unsupported file format"
        }), 400

    Config.UPLOAD_FOLDER.mkdir(
        parents=True,
        exist_ok=True
    )

    # Generate a safe and unique filename
    unique_filename = f"{uuid4().hex}{extension}"

    file_path = (
        Config.UPLOAD_FOLDER / unique_filename
    )

    try:

        file.save(str(file_path))

        if file_path.stat().st_size > Config.MAX_FILE_SIZE:

            return jsonify({
                "success": False,
                "message": "Maximum file size is 10 MB"
            }), 413

        # Basic file signature validation
        with open(file_path, "rb") as uploaded:

            header = uploaded.read(1024)

        if extension == ".pdf":
            valid = b"%PDF-" in header

        elif extension == ".png":
            valid = header.startswith(
                b"\x89PNG\r\n\x1a\n"
            )

        else:
            valid = header.startswith(b"\xff\xd8\xff")

        if not valid:

            return jsonify({
                "success": False,
                "message": "Invalid file content"
            }), 400

        result = extract_text(
            file_path,
            language
        )

        return jsonify({
            **result,
            "message": "Text extracted successfully",
            "filename": file.filename
        }), 200

    except RequestEntityTooLarge:

        return jsonify({
            "success": False,
            "message": "File is too large"
        }), 413

    except (ValueError, UnidentifiedImageError):

        return jsonify({
            "success": False,
            "message": "Invalid file or unreadable text"
        }), 400

    except Exception:

        current_app.logger.exception(
            "File extraction failed"
        )

        return jsonify({
            "success": False,
            "message": "File extraction failed"
        }), 500

    finally:

        # Remove temporary uploaded file
        file_path.unlink(missing_ok=True)
