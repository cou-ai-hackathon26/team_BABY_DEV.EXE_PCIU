
import pymupdf
import pytesseract

from PIL import Image, ImageOps
from pathlib import Path
from config import Config


# Configure Tesseract executable
pytesseract.pytesseract.tesseract_cmd = (
    Config.TESSERACT_CMD
)

# File processing limits
MAX_PDF_PAGES = 10
MAX_IMAGE_PIXELS = 20_000_000

SUPPORTED_IMAGE_TYPES = {
    ".png",
    ".jpg",
    ".jpeg"
}

# Language mapping
LANGUAGE_MAP = {
    "bn": "ben+eng",
    "en": "eng"
}


# Get OCR language
def get_ocr_language(language=None):

    if language is None:
        return Config.OCR_LANGUAGES

    if language not in LANGUAGE_MAP:
        raise ValueError("Unsupported language")

    return LANGUAGE_MAP[language]


# Validate file
def validate_file(file_path):

    file_path = Path(file_path)

    if not file_path.is_file():
        raise FileNotFoundError("File not found")

    if file_path.stat().st_size > Config.MAX_FILE_SIZE:
        raise ValueError("Maximum file size is 10 MB")

    return file_path


# Extract text from image
def extract_image_text(file_path, language=None):

    file_path = validate_file(file_path)

    if file_path.suffix.lower() not in SUPPORTED_IMAGE_TYPES:
        raise ValueError("Unsupported image format")

    ocr_language = get_ocr_language(language)

    with Image.open(file_path) as image:

        if image.width * image.height > MAX_IMAGE_PIXELS:
            raise ValueError("Image dimensions are too large")

        # Correct image orientation
        image = ImageOps.exif_transpose(image)

        # Convert image to grayscale
        image = image.convert("L")

        # Extract text
        text = pytesseract.image_to_string(
            image,
            lang=ocr_language,
            config="--oem 1 --psm 3",
            timeout=30
        )

    return text.strip()


# Extract text from PDF
def extract_pdf_text(file_path, language=None):

    file_path = validate_file(file_path)

    if file_path.suffix.lower() != ".pdf":
        raise ValueError("Unsupported PDF format")

    ocr_language = get_ocr_language(language)

    extracted_pages = []

    with pymupdf.open(file_path) as document:

        if document.needs_pass:
            raise ValueError("Password-protected PDF")

        if len(document) > MAX_PDF_PAGES:
            raise ValueError("Maximum 10 PDF pages allowed")

        for page in document:

            # Extract embedded text
            text = page.get_text(
                sort=True
            ).strip()

            # OCR fallback for scanned pages
            if not text:

                dpi = 200
                scale = dpi / 72

                width = int(page.rect.width * scale) + 2
                height = int(page.rect.height * scale) + 2

                if width * height > MAX_IMAGE_PIXELS:
                    raise ValueError("PDF page is too large")

                pixmap = page.get_pixmap(
                    dpi=dpi,
                    colorspace=pymupdf.csRGB,
                    alpha=False
                )

                image = Image.frombytes(
                    "RGB",
                    (pixmap.width, pixmap.height),
                    pixmap.samples
                )

                text = pytesseract.image_to_string(
                    image,
                    lang=ocr_language,
                    config="--oem 1 --psm 3",
                    timeout=30
                )

            extracted_pages.append(text.strip())

    return "\n\n".join(extracted_pages).strip()


# Automatically select extraction method
def extract_text(file_path, language=None):

    file_path = validate_file(file_path)

    extension = file_path.suffix.lower()

    if extension == ".pdf":

        text = extract_pdf_text(
            file_path,
            language
        )

        source_type = "pdf"

    elif extension in SUPPORTED_IMAGE_TYPES:

        text = extract_image_text(
            file_path,
            language
        )

        source_type = "image"

    else:

        raise ValueError("Unsupported file type")

    if not text.strip():
        raise ValueError("No readable text found")

    return {
        "success": True,
        "source_type": source_type,
        "language": language or "mixed",
        "text": text,
        "character_count": len(text),
        "word_count": len(text.split())
    }
