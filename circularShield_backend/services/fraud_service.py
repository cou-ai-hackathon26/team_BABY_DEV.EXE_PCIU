
import re

from services.model_service import preprocess_text


FRAUD_RULES = [
    {
        "id": "advance_payment",
        "severity": "high",
        "keywords": [
            "registration fee",
            "advance payment",
            "processing fee",
            "security deposit",
            "রেজিস্ট্রেশন ফি",
            "অগ্রিম টাকা",
            "প্রসেসিং ফি",
            "জামানত"
        ],
        "message_en": "Possible advance payment request.",
        "message_bn": "অগ্রিম টাকা প্রদানের সম্ভাব্য অনুরোধ।"
    },
    {
        "id": "guaranteed_job",
        "severity": "high",
        "keywords": [
            "guaranteed job",
            "100% job guarantee",
            "confirmed job",
            "নিশ্চিত চাকরি",
            "চাকরির নিশ্চয়তা"
        ],
        "message_en": "Unusual job guarantee detected.",
        "message_bn": "অস্বাভাবিক চাকরির নিশ্চয়তা পাওয়া গেছে।"
    },
    {
        "id": "urgent_application",
        "severity": "medium",
        "keywords": [
            "apply immediately",
            "limited seats",
            "hurry up",
            "এখনই আবেদন করুন",
            "সীমিত আসন",
            "দ্রুত আবেদন"
        ],
        "message_en": "Possible urgency or pressure tactic.",
        "message_bn": "দ্রুত সিদ্ধান্ত নেওয়ার সম্ভাব্য চাপ।"
    },
    {
        "id": "personal_payment",
        "severity": "high",
        "keywords": [
            "send money",
            "personal bkash",
            "personal nagad",
            "টাকা পাঠান",
            "বিকাশে টাকা পাঠান",
            "নগদে টাকা পাঠান"
        ],
        "message_en": "Possible direct payment request.",
        "message_bn": "সরাসরি টাকা পাঠানোর সম্ভাব্য অনুরোধ।"
    },
    {
        "id": "unrealistic_income",
        "severity": "medium",
        "keywords": [
            "easy money",
            "earn without working",
            "instant income",
            "সহজে টাকা আয়",
            "কাজ ছাড়াই আয়"
        ],
        "message_en": "Potentially unrealistic income offer.",
        "message_bn": "অবাস্তব আয়ের সম্ভাব্য প্রস্তাব।"
    }
]


def detect_fraud_indicators(text, language="en"):

    text = preprocess_text(text).casefold()

    indicators = []

    for rule in FRAUD_RULES:

        matched_keywords = [
            keyword
            for keyword in rule["keywords"]
            if preprocess_text(keyword).casefold() in text
        ]

        if matched_keywords:

            indicators.append({
                "id": rule["id"],
                "severity": rule["severity"],
                "matched_keywords": matched_keywords,
                "message": (
                    rule["message_bn"]
                    if language == "bn"
                    else rule["message_en"]
                )
            })

    return indicators


def extract_urls(text):

    pattern = r'https?://[^\s<>"]+'

    urls = re.findall(pattern, text)

    urls = [
        url.rstrip(".,;!?)")
        for url in urls
    ]

    return list(dict.fromkeys(urls))
