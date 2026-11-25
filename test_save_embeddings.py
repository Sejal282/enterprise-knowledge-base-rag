
from sqlalchemy import create_engine, text
from sentence_transformers import SentenceTransformer
from pgvector.sqlalchemy import Vector

from app.chunking import split_text_into_chunks


DATABASE_URL = "postgresql+psycopg://localhost:5432/enterprise_kb"
DOCUMENT_ID = 7

engine = create_engine(DATABASE_URL)


def save_document_embeddings():
    with engine.connect() as connection:
        result = connection.execute(
            text("""
                SELECT id, filename, extracted_text
                FROM documents
                WHERE id = :document_id
            """),
            {"document_id": DOCUMENT_ID},
        )
        document = result.fetchone()

    if document is None:
        raise RuntimeError(
            f"Document ID {DOCUMENT_ID} was not found."
        )

    document_id, filename, extracted_text = document

    if not extracted_text or not extracted_text.strip():
        raise RuntimeError("The document has no extracted text.")

    print(f"Document: {filename}")
    print(f"Document ID: {document_id}")

    chunks = split_text_into_chunks(
        extracted_text,
        chunk_size=500,
        overlap=100,
    )

    if not chunks:
        raise RuntimeError("No chunks were generated.")

    print(f"Chunks generated: {len(chunks)}")
    print("Loading embedding model...")

    model = SentenceTransformer(
        "sentence-transformers/all-MiniLM-L6-v2"
    )

    embeddings = model.encode(chunks)

    with engine.begin() as connection:
        # Make this script safe to rerun for this document.
        connection.execute(
            text("""
                DELETE FROM document_chunks
                WHERE document_id = :document_id
            """),
            {"document_id": document_id},
        )

        for chunk, embedding in zip(chunks, embeddings):
            connection.execute(
                text("""
                    INSERT INTO document_chunks
                        (document_id, chunk_text, embedding)
                    VALUES
                        (:document_id, :chunk_text, :embedding)
                """).bindparams(
                    # Tell SQLAlchemy that this parameter is a vector.
                    __import__(
                        "sqlalchemy"
                    ).bindparam(
                        "embedding",
                        type_=Vector(384),
                    )
                ),
                {
                    "document_id": document_id,
                    "chunk_text": chunk,
                    "embedding": embedding.tolist(),
                },
            )

    with engine.connect() as connection:
        count = connection.execute(
            text("""
                SELECT COUNT(*)
                FROM document_chunks
                WHERE document_id = :document_id
            """),
            {"document_id": document_id},
        ).scalar_one()

    print(f"Chunks saved in PostgreSQL: {count}")
    print("Embeddings saved successfully!")


if __name__ == "__main__":
    save_document_embeddings()
    engine.dispose()
