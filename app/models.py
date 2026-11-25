
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    func,
)

from pgvector.sqlalchemy import Vector

from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=True)
    status = Column(String(50), nullable=False, default="pending")

    extracted_text = Column(String, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)

    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    chunk_text = Column(String, nullable=False)

    embedding = Column(Vector(384), nullable=False)
