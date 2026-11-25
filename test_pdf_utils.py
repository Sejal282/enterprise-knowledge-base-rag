
from app.pdf_utils import extract_text_from_pdf
from pathlib import Path

pdf_path = Path("uploads/happiest.pdf")

print("Testing PDF:", pdf_path)

if not pdf_path.exists():
    print("ERROR: PDF file not found.")
else:
    text = extract_text_from_pdf(pdf_path)

    if text:
        print("Text extraction successful!")
        print("Extracted text:")
        print(text[:2000])
    else:
        print("No selectable text found in this PDF.")
        print("This may be a scanned PDF; OCR is not enabled yet.")
