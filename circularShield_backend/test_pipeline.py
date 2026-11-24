
import json
from pathlib import Path

from services.extraction_service import extract_text
from services.model_service import predict_circular


# Input configuration
FILE_PATH = "sample_circular.jpeg"
LANGUAGE = "bn"


# Step 1: Extract text
extraction = extract_text(
    FILE_PATH,
    LANGUAGE
)

text = extraction["text"]

print("Text extraction successful!")
print("Source:", extraction["source_type"])
print("Language:", extraction["language"])
print("Characters:", extraction["character_count"])
print("Words:", extraction["word_count"])


# Step 2: Save extracted text
Path("pipeline_extracted_text.txt").write_text(
    text,
    encoding="utf-8"
)


# Step 3: ML prediction
prediction = predict_circular(text)


# Step 4: Display result
print("\n--- ML Prediction Result ---")

print(
    json.dumps(
        prediction,
        indent=4,
        ensure_ascii=False
    )
)


# Step 5: Save prediction result
Path("pipeline_result.json").write_text(
    json.dumps(
        prediction,
        indent=4,
        ensure_ascii=False
    ),
    encoding="utf-8"
)

print("\nPipeline completed successfully!")
