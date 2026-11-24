
from datetime import datetime, timezone

from flask import (
    Blueprint,
    request,
    jsonify,
    g,
    current_app
)

from database import users_collection

from middleware.auth_middleware import (
    require_auth,
    require_admin
)


user_bp = Blueprint("user", __name__)


# =====================================
# Serialize User
# =====================================

def serialize_user(user):

    created_at = user.get("created_at")

    if isinstance(created_at, datetime):

        if created_at.tzinfo is None:
            created_at = created_at.replace(
                tzinfo=timezone.utc
            )

        created_at = created_at.isoformat()

    return {
        "uid": user.get("uid"),
        "name": user.get("name"),
        "email": user.get("email"),
        "role": user.get("role", "user"),
        "status": user.get("status", "active"),
        "created_at": created_at
    }


# =====================================
# 1. Register User Profile
# =====================================

@user_bp.post("/users")
@require_auth
def register_user():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):

        return jsonify({
            "success": False,
            "message": "Invalid request body."
        }), 400

    name = data.get("name", "")

    if not isinstance(name, str):

        return jsonify({
            "success": False,
            "message": "Invalid name."
        }), 400

    name = name.strip()

    if not name or len(name) > 100:

        return jsonify({
            "success": False,
            "message": "Please provide a valid name."
        }), 400

    uid = g.user["uid"]

    email = g.user.get("email")

    if not email:

        return jsonify({
            "success": False,
            "message": "An email address is required."
        }), 400

    try:

        result = users_collection.update_one(

            {"uid": uid},

            {
                "$setOnInsert": {
                    "uid": uid,
                    "name": name,
                    "email": email,
                    "role": "user",
                    "status": "active",
                    "created_at": datetime.now(
                        timezone.utc
                    )
                }
            },

            upsert=True
        )

        user = users_collection.find_one({
            "uid": uid
        })

        return jsonify({
            "success": True,
            "message": "User profile retrieved.",
            "user": serialize_user(user)
        }), 201 if result.upserted_id else 200

    except Exception:

        current_app.logger.exception(
            "User registration failed"
        )

        return jsonify({
            "success": False,
            "message": "Unable to save user profile."
        }), 500


# =====================================
# 2. Get Current User Profile
# =====================================

@user_bp.get("/users/me")
@require_auth
def get_current_user():

    user = g.user_profile

    if not user:

        return jsonify({
            "success": False,
            "message": "User profile not found."
        }), 404

    return jsonify({
        "success": True,
        "user": serialize_user(user)
    }), 200


# =====================================
# 3. Check Admin Access
# =====================================

@user_bp.get("/admin/check")
@require_admin
def check_admin():

    return jsonify({
        "success": True,
        "uid": g.user["uid"],
        "role": "admin",
        "message": "Admin access granted."
    }), 200
