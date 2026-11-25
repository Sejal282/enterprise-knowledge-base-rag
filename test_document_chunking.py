
from app.database import SessionLocal
from app.models import Document
from app.chunking import split_text_into_chunks

db = SessionLocal()

try:
    document = (
        db.query(Document)
        .filter(Document.extracted_text.isnot(None))
        .order_by(Document.id.desc())
        .first()
    )

    if document is None or not document.extracted_text.strip():
        print("No document with extracted text was found.")
    else:
        chunks = split_text_into_chunks(
            text=document.extracted_text,
            chunk_size=500,
            overlap=100,
        )

        print("Document ID:", document.id)
        print("Filename:", document.filename)
        print("Original text length:", len(document.extracted_text))
        print("Total chunks:", len(chunks))

        for index, chunk in enumerate(chunks, start=1):
            print(f"\n--- Chunk {index} ({len(chunk)} characters) ---")
            print(chunk)

finally:
    db.close()
