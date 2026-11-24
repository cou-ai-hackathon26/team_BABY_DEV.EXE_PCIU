
from services.model_service import predict_circular

from services.fraud_service import (
    detect_fraud_indicators,
    extract_urls
)


def analyze_risk(text, language="en"):

    if language not in ("en", "bn"):
        raise ValueError("Unsupported language")

    prediction = predict_circular(text)

    indicators = detect_fraud_indicators(
        text,
        language
    )

    urls = extract_urls(text)

    risk_score = prediction["fake_probability"]

    if risk_score >= 70:

        risk_level = "high"

        explanation_en = (
            "High estimated scam risk. "
            "Verify the employer before applying."
        )

        explanation_bn = (
            "প্রতারণার সম্ভাব্য ঝুঁকি বেশি। "
            "আবেদনের আগে প্রতিষ্ঠান যাচাই করুন।"
        )

    elif risk_score >= 40:

        risk_level = "medium"

        explanation_en = (
            "This circular requires further verification."
        )

        explanation_bn = (
            "এই নিয়োগ বিজ্ঞপ্তিটি আরও যাচাই করা প্রয়োজন।"
        )

    else:

        risk_level = "low"

        explanation_en = (
            "Low estimated scam risk. "
            "Authenticity is not confirmed."
        )

        explanation_bn = (
            "প্রতারণার সম্ভাব্য ঝুঁকি কম। "
            "তবে বিজ্ঞপ্তিটির সত্যতা নিশ্চিত নয়।"
        )

    return {
        "language": language,
        "prediction": prediction,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "fraud_indicators": indicators,
        "indicator_count": len(indicators),
        "urls": urls,
        "verification_status": "not_verified",
        "explanation": (
            explanation_bn
            if language == "bn"
            else explanation_en
        )
    }
