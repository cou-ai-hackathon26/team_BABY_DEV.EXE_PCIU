
import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

print("Tesseract version:")
print(pytesseract.get_tesseract_version())

print("\nAvailable languages:")
print(pytesseract.get_languages(config=""))

image = Image.open("sample_circular.jpeg")

text = pytesseract.image_to_string(
    image,
    lang="ben+eng",
    config="--oem 1 --psm 3"
)

print("\nExtracted text:")
print(text)

with open(
    "ocr_output.txt",
    "w",
    encoding="utf-8"
) as file:
    file.write(text)

print("\nOCR output saved successfully!")
