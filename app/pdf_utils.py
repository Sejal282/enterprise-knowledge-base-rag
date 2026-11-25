
import pymupdf
from pathlib import Path


def extract_text_from_pdf(file_path: str | Path) -> str:
    """
    Extract selectable text from a PDF file.
    """
    extracted_pages = []

    with pymupdf.open(file_path) as pdf:
        for page in pdf:
            page_text = page.get_text().strip()
            if page_text:
                extracted_pages.append(page_text)

    return "\n\n".join(extracted_pages)
