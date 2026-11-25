
from sqlalchemy import create_engine, text, bindparam
from pgvector.sqlalchemy import Vector
from sentence_transformers import SentenceTransformer

DATABASE_URL = "postgresql+psycopg://localhost:5432/enterprise_kb"

engine = create_engine(DATABASE_URL)

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def semantic_search(question: str, limit: int = 3):
    model = SentenceTransformer(MODEL_NAME)

    question_embedding = model.encode(question).tolist()

    query = text("""
        SELECT
            id,
            document_id,
            chunk_text,
            embedding <=> :question_embedding AS distance
        FROM document_chunks
        ORDER BY embedding <=> :question_embedding
        LIMIT :result_limit
    """).bindparams(
        bindparam(
            "question_embedding",
            type_=Vector(384),
        )
    )

    with engine.connect() as connection:
        results = connection.execute(
            query,
            {
                "question_embedding": question_embedding,
                "result_limit": limit,
            },
        ).fetchall()

    return results


if __name__ == "__main__":
    question = "How much annual leave do employees get?"

    print(f"Question: {question}\n")

    results = semantic_search(question)

    if not results:
        print("No chunks found.")
    else:
        for rank, result in enumerate(results, start=1):
            print(f"Result {rank}")
            print(f"Document ID: {result.document_id}")
            print(f"Distance: {result.distance:.4f}")
            print(f"Text: {result.chunk_text[:500]}")
            print("-" * 50)

    engine.dispose()
