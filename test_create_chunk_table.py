
from sqlalchemy import inspect

from app.database import engine, Base
from app.models import Document, DocumentChunk


def create_chunk_table():
    print("Checking database models...")

    # Create tables that are defined in the models but do not yet exist.
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    tables = inspector.get_table_names()

    print("\nTables found in the database:")
    for table in tables:
        print(f"- {table}")

    if "document_chunks" not in tables:
        raise RuntimeError("document_chunks table was not created.")

    print("\ndocument_chunks columns:")
    for column in inspector.get_columns("document_chunks"):
        print(f"- {column['name']}: {column['type']}")

    print("\nSUCCESS: document_chunks table is ready.")


if __name__ == "__main__":
    create_chunk_table()
