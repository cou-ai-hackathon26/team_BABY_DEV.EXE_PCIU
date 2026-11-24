
from datetime import datetime, timezone

from bson import ObjectId

from flask import (
    Blueprint,
    jsonify,
    request,
    g,
    current_app
)

from middleware.auth_middleware import require_admin

from database import (
    users_collection,
    analyses_collection,
    scam_reports_collection,
    organizations_collection
)


admin_dashboard_bp = Blueprint(
    "admin_dashboard",
    __name__
)


# =====================================
# 1. Format Date
# =====================================

def format_date(value):

    if not isinstance(value, datetime):
        return None

    if value.tzinfo is None:

        value = value.replace(
            tzinfo=timezone.utc
        )

    return value.isoformat()


# =====================================
# 2. Serialize Scam Report
# =====================================

def serialize_report(document):

    evidence = document.get("evidence") or []

    return {

        "id": str(document["_id"]),

        "title": (
            document.get("title")
            or document.get("subject")
            or "Scam Report"
        ),

        "description": document.get(
            "description", ""
        ),

        "status": document.get(
            "status", "pending"
        ),

        "evidence_count": (
            len(evidence)
            if isinstance(evidence, list)
            else 0
        ),

        "created_at": format_date(
            document.get("created_at")
        )

    }


# =====================================
# 3. Serialize Organization
# =====================================

def serialize_organization(document):

    return {

        "id": str(document["_id"]),

        "name": document.get(
            "name", "Unknown Organization"
        ),

        "website": document.get(
            "website", ""
        ),

        "email": document.get(
            "email", ""
        ),

        "status": document.get(
            "status", "pending"
        ),

        "created_at": format_date(
            document.get("created_at")
        )

    }


# =====================================
# 4. Admin Dashboard API
# =====================================

@admin_dashboard_bp.get("/admin/dashboard")
@require_admin
def get_admin_dashboard():

    try:

        # =============================
        # Platform Statistics
        # =============================

        total_users = users_collection.count_documents({
            "role": "user"
        })

        total_admins = users_collection.count_documents({
            "role": "admin"
        })

        total_analyses = (
            analyses_collection.count_documents({})
        )

        pending_reports = (
            scam_reports_collection.count_documents({
                "status": "pending"
            })
        )

        pending_organizations = (
            organizations_collection.count_documents({
                "status": "pending"
            })
        )

        verified_organizations = (
            organizations_collection.count_documents({
                "status": "verified"
            })
        )


        # =============================
        # Detection Statistics
        # =============================

        detection_statistics = {

            "low_risk": 0,

            "medium_risk": 0,

            "high_risk": 0,

            "unknown_risk": 0

        }

        pipeline = [

            {
                "$group": {

                    "_id": "$risk_level",

                    "count": {
                        "$sum": 1
                    }

                }
            }

        ]

        risk_counts = analyses_collection.aggregate(
            pipeline
        )

        for item in risk_counts:

            level = str(
                item.get("_id") or "unknown"
            ).lower().strip()

            key = f"{level}_risk"

            if key not in detection_statistics:
                key = "unknown_risk"

            detection_statistics[key] += item.get(
                "count", 0
            )


        # =============================
        # Pending Scam Reports
        # =============================

        report_documents = (
            scam_reports_collection.find({
                "status": "pending"
            })
            .sort("created_at", -1)
            .limit(5)
        )

        recent_reports = [

            serialize_report(document)

            for document in report_documents

        ]


        # =============================
        # Pending Organizations
        # =============================

        organization_documents = (
            organizations_collection.find({
                "status": "pending"
            })
            .sort("created_at", -1)
            .limit(5)
        )

        recent_organizations = [

            serialize_organization(document)

            for document in organization_documents

        ]


        # =============================
        # Return Dashboard Response
        # =============================

        return jsonify({

            "success": True,

            "statistics": {

                "total_users": total_users,

                "total_admins": total_admins,

                "total_analyses": total_analyses,

                "pending_reports": pending_reports,

                "pending_organizations":
                    pending_organizations,

                "verified_organizations":
                    verified_organizations

            },

            "detection_statistics":
                detection_statistics,

            "recent_reports":
                recent_reports,

            "recent_organizations":
                recent_organizations

        }), 200


    except Exception:

        current_app.logger.exception(
            "Admin dashboard retrieval failed"
        )

        return jsonify({

            "success": False,

            "message": "Unable to load admin dashboard"

        }), 500


# =====================================
# 5. Approve or Reject Scam Report
# =====================================

@admin_dashboard_bp.patch(
    "/admin/reports/<report_id>/status"
)
@require_admin
def update_report_status(report_id):

    if not ObjectId.is_valid(report_id):

        return jsonify({

            "success": False,

            "message": "Invalid report ID"

        }), 400


    data = request.get_json(silent=True)

    if not isinstance(data, dict):

        return jsonify({

            "success": False,

            "message": "Invalid JSON request"

        }), 400


    status = data.get("status")

    if status not in ("approved", "rejected"):

        return jsonify({

            "success": False,

            "message": "Invalid report status"

        }), 400


    try:

        updated = scam_reports_collection.update_one(

            {

                "_id": ObjectId(report_id),

                "status": "pending"

            },

            {

                "$set": {

                    "status": status,

                    "reviewed_by": g.user["uid"],

                    "reviewed_at": datetime.now(
                        timezone.utc
                    )

                }

            }

        )

        if updated.matched_count == 0:

            return jsonify({

                "success": False,

                "message":
                    "Pending report not found or already reviewed"

            }), 404


        return jsonify({

            "success": True,

            "message": f"Report {status} successfully",

            "report_id": report_id,

            "status": status

        }), 200


    except Exception:

        current_app.logger.exception(
            "Report status update failed"
        )

        return jsonify({

            "success": False,

            "message": "Unable to update report status"

        }), 500


# =====================================
# 6. Verify or Reject Organization
# =====================================

@admin_dashboard_bp.patch(
    "/admin/organizations/<organization_id>/status"
)
@require_admin
def update_organization_status(organization_id):

    if not ObjectId.is_valid(organization_id):

        return jsonify({

            "success": False,

            "message": "Invalid organization ID"

        }), 400


    data = request.get_json(silent=True)

    if not isinstance(data, dict):

        return jsonify({

            "success": False,

            "message": "Invalid JSON request"

        }), 400


    status = data.get("status")

    if status not in ("verified", "rejected"):

        return jsonify({

            "success": False,

            "message": "Invalid organization status"

        }), 400


    try:

        updated = organizations_collection.update_one(

            {

                "_id": ObjectId(organization_id),

                "status": "pending"

            },

            {

                "$set": {

                    "status": status,

                    "reviewed_by": g.user["uid"],

                    "reviewed_at": datetime.now(
                        timezone.utc
                    )

                }

            }

        )

        if updated.matched_count == 0:

            return jsonify({

                "success": False,

                "message":
                    "Pending organization not found or already reviewed"

            }), 404


        return jsonify({

            "success": True,

            "message": f"Organization {status} successfully",

            "organization_id": organization_id,

            "status": status

        }), 200


    except Exception:

        current_app.logger.exception(
            "Organization status update failed"
        )

        return jsonify({

            "success": False,

            "message": "Unable to update organization status"

        }), 500
