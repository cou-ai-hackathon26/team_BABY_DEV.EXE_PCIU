
from functools import wraps

from flask import (
    request,
    jsonify,
    g,
    current_app
)

from firebase_admin import auth

from database import users_collection


# =====================================
# 1. Authentication Middleware
# =====================================

def require_auth(function):

    @wraps(function)
    def decorated(*args, **kwargs):

        authorization = request.headers.get(
            "Authorization", ""
        )

        parts = authorization.split()

        if (
            len(parts) != 2
            or parts[0].lower() != "bearer"
        ):

            return jsonify({
                "success": False,
                "message": "Missing authentication token."
            }), 401

        token = parts[1]

        try:

            decoded_token = auth.verify_id_token(
                token,
                check_revoked=True
            )

        except (
            auth.InvalidIdTokenError,
            auth.ExpiredIdTokenError,
            auth.RevokedIdTokenError,
            auth.UserDisabledError
        ):

            return jsonify({
                "success": False,
                "message": (
                    "Invalid, expired or disabled session."
                )
            }), 401

        except Exception:

            current_app.logger.exception(
                "Firebase authentication failed"
            )

            return jsonify({
                "success": False,
                "message": (
                    "Authentication service unavailable."
                )
            }), 503

        uid = decoded_token["uid"]

        try:

            profile = users_collection.find_one({
                "uid": uid
            })

        except Exception:

            current_app.logger.exception(
                "Unable to retrieve user profile"
            )

            return jsonify({
                "success": False,
                "message": "Database service unavailable."
            }), 503


        # Block suspended users

        if profile and profile.get(
            "status", "active"
        ) == "suspended":

            return jsonify({
                "success": False,
                "message": (
                    "Your account has been suspended. "
                    "Please contact the administrator."
                )
            }), 403


        # Store authenticated user information

        g.user = {
            "uid": uid,
            "email": decoded_token.get("email"),
            "name": decoded_token.get("name"),
            "role": (
                profile.get("role")
                if profile
                else None
            ),
            "status": (
                profile.get("status", "active")
                if profile
                else None
            )
        }

        g.user_profile = profile

        return function(*args, **kwargs)

    return decorated


# =====================================
# 2. Administrator Middleware
# =====================================

def require_admin(function):

    @wraps(function)
    @require_auth
    def decorated(*args, **kwargs):

        profile = g.user_profile

        if (
            not profile
            or profile.get("role") != "admin"
            or profile.get(
                "status", "active"
            ) != "active"
        ):

            return jsonify({
                "success": False,
                "message": "Admin access required."
            }), 403

        return function(*args, **kwargs)

    return decorated
