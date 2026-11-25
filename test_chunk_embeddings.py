
from sqlalchemy import create_engine, text
from sentence_transformers import SentenceTransformer
from app.chunking import split_text_into_chunks

DATABASE_URL = "postgresql+psycopg://localhost:5432/enterprise_kb"

engine = create_engine(DATABASE_URL)

with engine.connect() as connection:
    result = connection.execute(
        text("""
            SELECT id, filename, extracted_text
            FROM documents
            WHERE extracted_text IS NOT NULL
              AND extracted_text <> ''
            ORDER BY id DESC
            LIMIT 1
        """)
    )
    document = result.fetchone()

if document is None:
    raise RuntimeError(
        "No document with extracted text was found in the database."
    )

document_id, filename, extracted_text = document

print(f"Document ID: {document_id}")
print(f"Filename: {filename}")
print(f"Extracted text length: {len(extracted_text)}")

chunks = split_text_into_chunks(
    extracted_text,
    chunk_size=500,
    overlap=100,
)

print(f"Total chunks: {len(chunks)}")

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

embeddings = model.encode(chunks)

print(f"Embedding matrix shape: {embeddings.shape}")
print(f"Dimensions per chunk: {embeddings.shape[1]}")
print("Embeddings generated successfully!")
