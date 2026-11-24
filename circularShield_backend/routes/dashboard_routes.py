
from flask import (
    Blueprint,
    jsonify,
    g,
    current_app
)

from datetime import timezone

from middleware.auth_middleware import require_auth

from database import (
    analyses_collection,
    users_collection
)


dashboard_bp = Blueprint("dashboard", __name__)


# =====================================
# 1. Serialize Analysis
# =====================================

def serialize_analysis(document):

    text = document.get("text") or ""

    created_at = document.get("created_at")

    if created_at and created_at.tzinfo is None:

        created_at = created_at.replace(
            tzinfo=timezone.utc
        )

    clean_text = " ".join(text.split())

    title = (
        document.get("title")
        or document.get("file_name")
        or document.get("url_title")
        or clean_text[:65]
        or "Job Circular Analysis"
    )

    risk_level = str(
        document.get("risk_level", "unknown")
    ).lower().strip()

    if risk_level not in ("low", "medium", "high"):
        risk_level = "unknown"

    return {

        "analysis_id": str(document["_id"]),

        "title": title,

        "text": text,

        "source_type": document.get(
            "source_type", "text"
        ),

        "source_url": document.get("source_url"),

        "file_name": document.get("file_name"),

        "language": document.get("language", "en"),

        "risk_score": document.get("risk_score"),

        "risk_level": risk_level,

        "created_at": (
            created_at.isoformat()
            if created_at
            else None
        ),

        "result": {

            "language": document.get(
                "language", "en"
            ),

            "prediction": document.get(
                "prediction"
            ),

            "risk_score": document.get(
                "risk_score"
            ),

            "risk_level": risk_level,

            "fraud_indicators": document.get(
                "fraud_indicators", []
            ),

            "indicator_count": document.get(
                "indicator_count", 0
            ),

            "urls": document.get("urls", []),

            "verification_status": document.get(
                "verification_status",
                "not_verified"
            ),

            "explanation": document.get(
                "explanation", ""
            )
        }
    }


# =====================================
# 2. Dashboard API
# =====================================

@dashboard_bp.get("/dashboard")
@require_auth
def get_dashboard():

    try:

        user_id = g.user["uid"]

        # Get authenticated user

        user = users_collection.find_one({
            "uid": user_id
        })

        if not user:

            return jsonify({
                "success": False,
                "message": "User profile not found"
            }), 404


        # Restrict dashboard to normal users

        if user.get("role") != "user":

            return jsonify({
                "success": False,
                "message": "User dashboard access required"
            }), 403


        # =================================
        # 3. Calculate Statistics
        # =================================

        statistics = {

            "total_analyzed": 0,

            "low_risk": 0,

            "medium_risk": 0,

            "high_risk": 0,

            "unknown_risk": 0

        }

        pipeline = [

            {
                "$match": {
                    "user_id": user_id
                }
            },

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

            count = item.get("count", 0)

            statistics["total_analyzed"] += count

            if level == "low":

                statistics["low_risk"] += count

            elif level == "medium":

                statistics["medium_risk"] += count

            elif level == "high":

                statistics["high_risk"] += count

            else:

                statistics["unknown_risk"] += count


        # =================================
        # 4. Recent Analysis History
        # =================================

        recent_documents = list(

            analyses_collection.find({
                "user_id": user_id
            })

            .sort("created_at", -1)

            .limit(5)

        )

        recent_analyses = [

            serialize_analysis(document)

            for document in recent_documents

        ]


        # =================================
        # 5. Recent Risk Alerts
        # =================================

        alert_documents = analyses_collection.find({

            "user_id": user_id,

            "fraud_indicators.0": {
                "$exists": True
            }

        }).sort("created_at", -1).limit(10)


        recent_alerts = []

        seen_indicators = set()


        for document in alert_documents:

            indicators = document.get(
                "fraud_indicators", []
            ) or []

            for indicator in indicators:

                if not isinstance(indicator, dict):
                    continue

                indicator_id = indicator.get(
                    "id", "unknown"
                )

                if indicator_id in seen_indicators:
                    continue

                seen_indicators.add(indicator_id)

                recent_alerts.append({

                    "analysis_id": str(
                        document["_id"]
                    ),

                    "indicator_id": indicator_id,

                    "severity": indicator.get(
                        "severity", "unknown"
                    ),

                    "message": indicator.get(
                        "message",
                        "Potential fraud indicator detected."
                    ),

                    "matched_keywords": indicator.get(
                        "matched_keywords", []
                    )

                })

                if len(recent_alerts) >= 5:
                    break

            if len(recent_alerts) >= 5:
                break


        # =================================
        # 6. Return Dashboard Data
        # =================================

        return jsonify({

            "success": True,

            "user": {

                "name": user.get("name", "User"),

                "email": user.get("email"),

                "role": user.get("role", "user")

            },

            "statistics": statistics,

            "recent_analyses": recent_analyses,

            "recent_alerts": recent_alerts

        }), 200


    except Exception:

        current_app.logger.exception(
            "Dashboard API failed"
        )

        return jsonify({

            "success": False,

            "message": "Unable to retrieve dashboard data. Check the backend server logs."

        }), 500
