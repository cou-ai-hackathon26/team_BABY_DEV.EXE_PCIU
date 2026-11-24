
import re

from datetime import datetime, timezone, timedelta
from math import ceil

from bson import ObjectId

from flask import (
    Blueprint,
    request,
    jsonify,
    g,
    current_app
)

from middleware.auth_middleware import require_auth

from database import analyses_collection

from routes.dashboard_routes import serialize_analysis


history_bp = Blueprint("history", __name__)


# =====================================
# 1. Get Analysis History
# =====================================

@history_bp.get("/history")
@require_auth
def get_history():

    try:

        user_id = g.user["uid"]

        # Get query parameters

        search = request.args.get(
            "search", ""
        ).strip()

        risk_level = request.args.get(
            "risk_level", "all"
        ).lower()

        date_range = request.args.get(
            "date_range", "all"
        )

        page = request.args.get(
            "page", 1, type=int
        )

        limit = request.args.get(
            "limit", 10, type=int
        )

        # Validate pagination

        page = max(1, min(page, 10000))

        limit = max(1, min(limit, 50))

        if len(search) > 100:

            return jsonify({
                "success": False,
                "message": "Search text is too long"
            }), 400

        if risk_level not in (
            "all", "low", "medium", "high"
        ):

            return jsonify({
                "success": False,
                "message": "Invalid risk filter"
            }), 400

        if date_range not in (
            "all", "7", "30", "90"
        ):

            return jsonify({
                "success": False,
                "message": "Invalid date filter"
            }), 400

        # =============================
        # Build MongoDB query
        # =============================

        query = {
            "user_id": user_id
        }

        # Search filter

        if search:

            safe_search = re.escape(search)

            query["$or"] = [

                {
                    "title": {
                        "$regex": safe_search,
                        "$options": "i"
                    }
                },

                {
                    "text": {
                        "$regex": safe_search,
                        "$options": "i"
                    }
                },

                {
                    "file_name": {
                        "$regex": safe_search,
                        "$options": "i"
                    }
                },

                {
                    "source_url": {
                        "$regex": safe_search,
                        "$options": "i"
                    }
                },

                {
                    "url_title": {
                        "$regex": safe_search,
                        "$options": "i"
                    }
                }

            ]

        # Risk filter

        if risk_level != "all":

            query["risk_level"] = risk_level

        # Date filter

        if date_range != "all":

            start_date = (
                datetime.now(timezone.utc)
                - timedelta(days=int(date_range))
            )

            query["created_at"] = {
                "$gte": start_date
            }

        # =============================
        # Pagination
        # =============================

        total_records = (
            analyses_collection.count_documents(
                query
            )
        )

        total_pages = max(
            1,
            ceil(total_records / limit)
        )

        page = min(page, total_pages)

        skip = (page - 1) * limit

        # =============================
        # Retrieve matching records
        # =============================

        documents = analyses_collection.find(
            query
        ).sort([
            ("created_at", -1),
            ("_id", -1)
        ]).skip(skip).limit(limit)

        history_items = []

        for document in documents:

            item = serialize_analysis(document)

            # History list does not need full text
            # or the complete analysis result

            item.pop("text", None)
            item.pop("result", None)

            history_items.append(item)

        # =============================
        # Return response
        # =============================

        return jsonify({

            "success": True,

            "history": history_items,

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
            "Analysis history retrieval failed"
        )

        return jsonify({

            "success": False,

            "message": "Unable to retrieve analysis history"

        }), 500


# =====================================
# 2. Get Single Analysis
# =====================================

@history_bp.get("/history/<analysis_id>")
@require_auth
def get_single_analysis(analysis_id):

    if not ObjectId.is_valid(analysis_id):

        return jsonify({

            "success": False,

            "message": "Invalid analysis ID"

        }), 400

    try:

        document = analyses_collection.find_one({

            "_id": ObjectId(analysis_id),

            "user_id": g.user["uid"]

        })

        if not document:

            return jsonify({

                "success": False,

                "message": "Analysis not found"

            }), 404

        return jsonify({

            "success": True,

            "analysis": serialize_analysis(document)

        }), 200

    except Exception:

        current_app.logger.exception(
            "Single analysis retrieval failed"
        )

        return jsonify({

            "success": False,

            "message": "Unable to retrieve analysis"

        }), 500


# =====================================
# 3. Delete Analysis
# =====================================

@history_bp.delete("/history/<analysis_id>")
@require_auth
def delete_analysis(analysis_id):

    if not ObjectId.is_valid(analysis_id):

        return jsonify({

            "success": False,

            "message": "Invalid analysis ID"

        }), 400

    try:

        deleted = analyses_collection.delete_one({

            "_id": ObjectId(analysis_id),

            "user_id": g.user["uid"]

        })

        if deleted.deleted_count == 0:

            return jsonify({

                "success": False,

                "message": "Analysis not found"

            }), 404

        return jsonify({

            "success": True,

            "message": "Analysis deleted successfully",

            "analysis_id": analysis_id

        }), 200

    except Exception:

        current_app.logger.exception(
            "Analysis deletion failed"
        )

        return jsonify({

            "success": False,

            "message": "Unable to delete analysis"

        }), 500
