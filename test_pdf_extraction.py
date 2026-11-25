

import pymupdf
from pathlib import Path

print("Starting PDF extraction test...")

UPLOAD_DIR = Path("uploads")
pdf_files = list(UPLOAD_DIR.glob("*.pdf"))

print("PDF files found:", len(pdf_files))

if not pdf_files:
    print("No PDF files found in uploads.")
else:
    pdf_path = pdf_files[0]

    with pymupdf.open(pdf_path) as pdf:
        page_count = len(pdf)
        extracted_text = "\n".join(
            page.get_text() for page in pdf
        )

    print("PDF filename:", pdf_path.name)
    print("Number of pages:", page_count)
    print("Extracted text:")
    print(extracted_text[:2000])

    if not extracted_text.strip():
        print("No selectable text found. This PDF may be scanned.")
