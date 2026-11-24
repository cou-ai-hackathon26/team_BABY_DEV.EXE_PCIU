
import re

from math import ceil

from datetime import datetime, timezone

from flask import (
    Blueprint,
    request,
    jsonify,
    g,
    current_app
)

from firebase_admin import auth

from database import (
    users_collection,
    analyses_collection
)

from middleware.auth_middleware import require_admin


admin_user_bp = Blueprint(
    "admin_user",
    __name__
)


ALLOWED_ROLES = ("admin", "user")

ALLOWED_STATUSES = ("active", "suspended")


# =====================================
# 1. Serialize User
# =====================================

def serialize_user(user, analyses_count=0):

    created_at = user.get("created_at")

    if isinstance(created_at, datetime):

        if created_at.tzinfo is None:
            created_at = created_at.replace(
                tzinfo=timezone.utc
            )

        created_at = created_at.isoformat()

    return {
        "uid": user.get("uid"),
        "name": user.get("name", ""),
        "email": user.get("email", ""),
        "role": user.get("role", "user"),
        "status": user.get("status", "active"),
        "created_at": created_at,
        "analyses_count": analyses_count
    }


# =====================================
# 2. Common Error Response
# =====================================

def error_response(message, status_code):

    return jsonify({
        "success": False,
        "message": message
    }), status_code


# =====================================
# 3. Get User Statistics
# =====================================

def get_user_statistics():

    return {
        "total_users": users_collection.count_documents({}),

        "active_accounts": users_collection.count_documents({
            "$or": [
                {"status": "active"},
                {"status": {"$exists": False}}
            ]
        }),

        "admin_accounts": users_collection.count_documents({
            "role": "admin"
        }),

        "suspended_accounts": users_collection.count_documents({
            "status": "suspended"
        })
    }


# =====================================
# 4. Get All Users
# =====================================

@admin_user_bp.get("/admin/users")
@require_admin
def get_all_users():

    try:

        search = request.args.get(
            "search", ""
        ).strip()[:100]

        role = request.args.get(
            "role", "all"
        ).lower()

        status = request.args.get(
            "status", "all"
        ).lower()

        page = request.args.get(
            "page", 1, type=int
        )

        limit = request.args.get(
            "limit", 10, type=int
        )

        page = max(1, min(page, 10000))

        limit = max(1, min(limit, 50))


        # Validate filters

        if role not in ("all", *ALLOWED_ROLES):

            return error_response(
                "Invalid role filter.", 400
            )

        if status not in ("all", *ALLOWED_STATUSES):

            return error_response(
                "Invalid status filter.", 400
            )


        # Build MongoDB query

        conditions = []

        if search:

            pattern = re.escape(search)

            conditions.append({
                "$or": [
                    {
                        "name": {
                            "$regex": pattern,
                            "$options": "i"
                        }
                    },
                    {
                        "email": {
                            "$regex": pattern,
                            "$options": "i"
                        }
                    },
                    {
                        "uid": {
                            "$regex": pattern,
                            "$options": "i"
                        }
                    }
                ]
            })


        if role != "all":

            conditions.append({
                "role": role
            })


        if status == "active":

            conditions.append({
                "$or": [
                    {"status": "active"},
                    {"status": {"$exists": False}}
                ]
            })

        elif status == "suspended":

            conditions.append({
                "status": "suspended"
            })


        query = (
            {"$and": conditions}
            if conditions
            else {}
        )


        # Pagination

        total_records = (
            users_collection.count_documents(query)
        )

        total_pages = max(
            1,
            ceil(total_records / limit)
        )

        page = min(page, total_pages)

        skip = (page - 1) * limit


        # Retrieve users

        users = list(

            users_collection.find(query)

            .sort([
                ("created_at", -1),
                ("_id", -1)
            ])

            .skip(skip)

            .limit(limit)
        )


        # Get analyses count for current page users

        user_ids = [
            user["uid"]
            for user in users
            if user.get("uid")
        ]

        analysis_counts = {}

        if user_ids:

            pipeline = [
                {
                    "$match": {
                        "user_id": {
                            "$in": user_ids
                        }
                    }
                },
                {
                    "$group": {
                        "_id": "$user_id",
                        "count": {
                            "$sum": 1
                        }
                    }
                }
            ]

            for item in analyses_collection.aggregate(
                pipeline
            ):

                analysis_counts[item["_id"]] = (
                    item["count"]
                )


        # Serialize users

        serialized_users = [

            serialize_user(
                user,
                analysis_counts.get(
                    user.get("uid"), 0
                )
            )

            for user in users
        ]


        return jsonify({

            "success": True,

            "statistics": get_user_statistics(),

            "users": serialized_users,

            "pagination": {
                "page": page,
                "limit": limit,
                "total_records": total_records,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1
            }

        }), 200


    except Exception:

        current_app.logger.exception(
            "Unable to retrieve admin user list"
        )

        return error_response(
            "Unable to retrieve users.", 500
        )


# =====================================
# 5. Create New User
# =====================================

@admin_user_bp.post("/admin/users")
@require_admin
def create_new_user():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):

        return error_response(
            "Invalid request body.", 400
        )

    name = data.get("name", "")

    email = data.get("email", "")

    password = data.get("password", "")

    role = data.get("role", "user")


    # Validate input types

    if not all(
        isinstance(value, str)
        for value in [name, email, password, role]
    ):

        return error_response(
            "Invalid user information.", 400
        )

    name = name.strip()

    email = email.strip().lower()

    role = role.strip().lower()


    # Validate name

    if not name or len(name) > 100:

        return error_response(
            "Please provide a valid name.", 400
        )


    # Validate email

    if (
        len(email) > 254
        or not re.fullmatch(
            r"[^@\s]+@[^@\s]+\.[^@\s]+",
            email
        )
    ):

        return error_response(
            "Please provide a valid email address.", 400
        )


    # Validate password

    if not 8 <= len(password) <= 128:

        return error_response(
            "Password must contain 8 to 128 characters.",
            400
        )


    # Validate role

    if role not in ALLOWED_ROLES:

        return error_response(
            "Unsupported user role.", 400
        )


    firebase_user = None

    try:

        existing_user = users_collection.find_one({
            "email": email
        })

        if existing_user:

            return error_response(
                "This email address is already registered.",
                409
            )


        # Create Firebase account

        firebase_user = auth.create_user(
            email=email,
            password=password,
            display_name=name,
            email_verified=False,
            disabled=False
        )


        # Create MongoDB profile

        user_document = {
            "uid": firebase_user.uid,
            "name": name,
            "email": email,
            "role": role,
            "status": "active",
            "created_at": datetime.now(
                timezone.utc
            ),
            "created_by": g.user["uid"]
        }

        users_collection.insert_one(
            user_document
        )


        return jsonify({
            "success": True,
            "message": "New user created successfully.",
            "user": serialize_user(user_document)
        }), 201


    except auth.EmailAlreadyExistsError:

        return error_response(
            "This email is already registered in Firebase.",
            409
        )


    except Exception:

        current_app.logger.exception(
            "Admin user creation failed"
        )


        # Attempt to roll back Firebase account
        # if MongoDB profile creation failed.

        if firebase_user:

            try:

                saved_profile = users_collection.find_one({
                    "uid": firebase_user.uid
                })

                if not saved_profile:

                    auth.delete_user(
                        firebase_user.uid
                    )

            except Exception:

                current_app.logger.exception(
                    "User creation requires reconciliation"
                )


        return error_response(
            "Unable to create the user. Check backend logs.",
            500
        )


# =====================================
# 6. Update User Role
# =====================================

@admin_user_bp.patch("/admin/users/<uid>/role")
@require_admin
def update_user_role(uid):

    data = request.get_json(silent=True)

    if not isinstance(data, dict):

        return error_response(
            "Invalid request body.", 400
        )

    role = data.get("role")

    if role not in ALLOWED_ROLES:

        return error_response(
            "Unsupported user role.", 400
        )


    # Prevent self-role modification

    if uid == g.user["uid"]:

        return error_response(
            "You cannot change your own role.", 403
        )


    try:

        user = users_collection.find_one({
            "uid": uid
        })

        if not user:

            return error_response(
                "User not found.", 404
            )


        # Protect existing administrator accounts.
        # Admin demotion must be handled by the
        # trusted system owner outside this API.

        if user.get("role") == "admin":

            return error_response(
                "Existing administrator accounts are protected.",
                403
            )


        if user.get("status", "active") != "active":

            return error_response(
                "Activate the account before changing its role.",
                409
            )


        result = users_collection.update_one(

            {
                "uid": uid,
                "role": "user",
                "status": {"$ne": "suspended"}
            },

            {
                "$set": {
                    "role": role,
                    "updated_at": datetime.now(
                        timezone.utc
                    ),
                    "updated_by": g.user["uid"]
                }
            }
        )

        if result.matched_count == 0:

            return error_response(
                "The account has changed. Refresh and try again.",
                409
            )


        return jsonify({
            "success": True,
            "message": "User role updated successfully.",
            "uid": uid,
            "role": role
        }), 200


    except Exception:

        current_app.logger.exception(
            "User role update failed"
        )

        return error_response(
            "Unable to update user role.", 500
        )


# =====================================
# 7. Suspend or Activate User
# =====================================

@admin_user_bp.patch("/admin/users/<uid>/status")
@require_admin
def update_user_status(uid):

    data = request.get_json(silent=True)

    if not isinstance(data, dict):

        return error_response(
            "Invalid request body.", 400
        )

    status = data.get("status")

    if status not in ALLOWED_STATUSES:

        return error_response(
            "Unsupported account status.", 400
        )


    # Prevent self-suspension

    if uid == g.user["uid"]:

        return error_response(
            "You cannot change your own account status.",
            403
        )


    try:

        user = users_collection.find_one({
            "uid": uid
        })

        if not user:

            return error_response(
                "User not found.", 404
            )


        # Protect administrator accounts

        if user.get("role") == "admin":

            return error_response(
                "Administrator accounts are protected.",
                403
            )


        # Confirm Firebase account exists

        auth.get_user(uid)


        update_data = {
            "status": status,
            "updated_at": datetime.now(
                timezone.utc
            ),
            "updated_by": g.user["uid"]
        }


        # =================================
        # Suspend Account
        # =================================

        if status == "suspended":

            # Block backend access first.

            result = users_collection.update_one(

                {
                    "uid": uid,
                    "role": "user"
                },

                {
                    "$set": update_data
                }
            )

            if result.matched_count == 0:

                return error_response(
                    "Account changed. Refresh and try again.",
                    409
                )


            # Disable Firebase authentication.

            auth.update_user(
                uid,
                disabled=True
            )


            # Revoke existing refresh tokens.

            auth.revoke_refresh_tokens(uid)


        # =================================
        # Activate Account
        # =================================

        else:

            # Enable Firebase first.
            # MongoDB still blocks access until
            # the account status is updated.

            auth.update_user(
                uid,
                disabled=False
            )

            result = users_collection.update_one(

                {
                    "uid": uid,
                    "role": "user"
                },

                {
                    "$set": update_data
                }
            )

            if result.matched_count == 0:

                return error_response(
                    "Account changed. Refresh and try again.",
                    409
                )


        message = (
            "User suspended successfully."
            if status == "suspended"
            else "User activated successfully."
        )


        return jsonify({
            "success": True,
            "message": message,
            "uid": uid,
            "status": status
        }), 200


    except auth.UserNotFoundError:

        return error_response(
            "Firebase account not found.", 404
        )


    except Exception:

        current_app.logger.exception(
            "User status update failed"
        )

        return error_response(
            "Account update could not be completed. "
            "Refresh the page and retry the intended status.",
            500
        )
