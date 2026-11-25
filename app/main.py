import logging
from fastapi import FastAPI
from pathlib import Path

from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    Query,
    UploadFile,
    File,
    status,
)
from fastapi.security import OAuth2PasswordBearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
from pydantic import BaseModel, Field
from pydantic import EmailStr
from sqlalchemy import text, bindparam
from sqlalchemy.orm import Session
from pgvector.sqlalchemy import Vector
from sentence_transformers import SentenceTransformer
from sqlalchemy.exc import IntegrityError
from app.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)

from app.database import SessionLocal, engine
from app.models import Document, DocumentChunk, User
from app.pdf_utils import extract_text_from_pdf
from app.chunking import split_text_into_chunks
from app.llm import generate_answer

logger = logging.getLogger(__name__)
app = FastAPI(
    title="Enterprise Knowledge Base RAG API",
    description=(
        "An API for searching company documents and answering "
        "questions using AI."
    ),
    version="1.0.0",
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSIONS = 384

# Load the embedding model once when the application starts.
embedding_model = SentenceTransformer(MODEL_NAME)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class DocumentCreate(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str | None = Field(default=None, max_length=100)


class DocumentStatusUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=50)


class QueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


@app.post("/auth/register", status_code=201)
def register_user(user_data: UserRegister):
    db = SessionLocal()

    try:
        existing_user = (
            db.query(User)
            .filter(User.email == user_data.email)
            .first()
        )

        if existing_user:
            raise HTTPException(
                status_code=409,
                detail="Email is already registered",
            )

        new_user = User(
            email=str(user_data.email).lower(),
            password_hash=hash_password(user_data.password),
            role="user",
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return {
            "id": new_user.id,
            "email": new_user.email,
            "role": new_user.role,
        }

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Email is already registered",
        )

    finally:
        db.close()


@app.post("/auth/login")
def login_user(user_data: UserLogin):
    db = SessionLocal()

    try:
        user = (
            db.query(User)
            .filter(User.email == str(user_data.email).lower())
            .first()
        )

        if not user or not verify_password(
            user_data.password,
            user.password_hash,
        ):
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=403,
                detail="User account is inactive",
            )

        access_token = create_access_token(user.id)

        return {
            "access_token": access_token,
            "token_type": "bearer",
        }

    finally:
        db.close()


def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        user_id = int(payload.get("sub"))

        if user_id is None:
            raise credentials_exception

    except Exception:
        raise credentials_exception

    db = SessionLocal()

    try:
        user = db.query(User).filter(User.id == user_id).first()

        if user is None:
            raise credentials_exception

        if not user.is_active:
            raise HTTPException(
                status_code=403,
                detail="User account is inactive",
            )

        return user

    finally:
        db.close()


@app.get("/auth/me")
def read_current_user(
    current_user: User = Depends(get_current_user),
):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
    }




@app.get("/")
def home():
    return {
        "message": "Enterprise Knowledge Base RAG API is running!"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}



def semantic_search(
    question: str,
    limit: int = 3,
    max_distance: float = 0.70,
):

    question_embedding = embedding_model.encode(question).tolist()


    search_query = text("""
        WITH ranked_chunks AS (
            SELECT
                dc.id AS chunk_id,
                dc.document_id,
                d.filename,
                dc.chunk_text,
                dc.embedding <=> :question_embedding AS distance,
                ROW_NUMBER() OVER (
                    PARTITION BY dc.chunk_text
                    ORDER BY
                        dc.embedding <=> :question_embedding,
                        dc.id DESC
                ) AS duplicate_rank
            FROM document_chunks AS dc
            JOIN documents AS d ON d.id = dc.document_id
            WHERE
                dc.embedding <=> :question_embedding
                < :max_distance
        )
        SELECT
            chunk_id,
            document_id,
            filename,
            chunk_text,
            distance
        FROM ranked_chunks
        WHERE duplicate_rank = 1
        ORDER BY distance
        LIMIT :result_limit
    """).bindparams(
        bindparam(
            "question_embedding",
            type_=Vector(EMBEDDING_DIMENSIONS),
        )
    )

    # Execute the search against PostgreSQL.
    with engine.connect() as connection:
        results = connection.execute(
            search_query,
            {
                "question_embedding": question_embedding,
                "max_distance": max_distance,
                "result_limit": limit,
            },
        ).fetchall()

    return results



@app.post("/query")
def query_knowledge_base(
    request: QueryRequest,
    current_user: User = Depends(get_current_user),
):

    try:
        results = semantic_search(request.question, limit=3)
    except Exception as exc:
        logger.exception("Knowledge-base search failed")

        raise HTTPException(
            status_code=500,
            detail="Knowledge-base search failed.",
        ) from exc


    if not results:
        return {
            "question": request.question,
            "answer": (
                "I could not find any indexed document passages "
                "to answer your question."
            ),
            "sources": [],
        }

    context = "\n\n".join(
        (
            f"Source: {result.filename} "
            f"(document ID: {result.document_id}, "
            f"chunk ID: {result.chunk_id})\n"
            f"{result.chunk_text}"
        )
        for result in results
    )


    try:
        answer = generate_answer(
            question=request.question,
            context=context,
        )
    except Exception as exc:
        logger.exception("Gemini answer generation failed")

        raise HTTPException(
            status_code=502,
            detail=(
                "AI answer generation failed. Check server logs "
                "for the underlying error."
            ),
        ) from exc
    return {
        "question": request.question,
        "answer": answer,
        "sources": [
            {
                "document_id": result.document_id,
                "filename": result.filename,
                "chunk_id": result.chunk_id,
                "text": result.chunk_text,
            }
            for result in results
        ],
    }


@app.post(
    "/documents/upload",
    status_code=status.HTTP_201_CREATED,
)
def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Validate the uploaded file.
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed.",
        )

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="The uploaded file must have a .pdf extension.",
        )

    saved_file_path = None

    try:
        # Read the uploaded PDF into memory.
        file_bytes = file.file.read()

        if not file_bytes:
            raise HTTPException(
                status_code=400,
                detail="The uploaded PDF is empty.",
            )

        # Calculate a SHA-256 fingerprint of the PDF contents.
        file_hash = hashlib.sha256(file_bytes).hexdigest()

        # Ensure the upload directory exists.
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

        # Check existing PDFs for identical file contents.
        for existing_file in UPLOAD_DIR.glob("*.pdf"):
            try:
                existing_hash = hashlib.sha256(
                    existing_file.read_bytes()
                ).hexdigest()
            except OSError:
                # Skip a file that cannot be read.
                continue

            if existing_hash == file_hash:
                existing_document = (
                    db.query(Document)
                    .filter(Document.filename == existing_file.name)
                    .first()
                )

                if existing_document:
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            "This PDF has already been uploaded. "
                            f"Existing document ID: "
                            f"{existing_document.id}."
                        ),
                    )

        # Use part of the content hash in the filename.
        # This prevents different PDFs with the same original name
        # from overwriting each other.
        original_name = Path(file.filename).name
        file_stem = Path(original_name).stem
        unique_filename = f"{file_stem}_{file_hash[:12]}.pdf"
        file_path = UPLOAD_DIR / unique_filename

        # Do not overwrite an existing file.
        if file_path.exists():
            raise HTTPException(
                status_code=409,
                detail=(
                    "A file with this generated filename already exists. "
                    "Please check the uploads directory and database."
                ),
            )

        file_path.write_bytes(file_bytes)
        saved_file_path = file_path

        # Extract selectable text from the PDF.
        extracted_text = extract_text_from_pdf(file_path)

        # Create the document record in PostgreSQL.
        document = Document(
            filename=file_path.name,
            content_type=file.content_type,
            status="pending",
            extracted_text=extracted_text,
        )

        db.add(document)
        db.flush()

        # Split the extracted text into chunks.
        chunks = split_text_into_chunks(extracted_text)
        chunks_created = 0

        if chunks:
            # Generate embeddings for every chunk.
            embeddings = embedding_model.encode(chunks)

            # Store each chunk and its embedding.
            for chunk_text, embedding in zip(chunks, embeddings):
                db.add(
                    DocumentChunk(
                        document_id=document.id,
                        chunk_text=chunk_text,
                        embedding=embedding.tolist(),
                    )
                )

            chunks_created = len(chunks)
            document.status = "completed"

        else:
            document.status = "needs_ocr"


        # Commit document and chunk records.
        db.commit()
        db.refresh(document)

        return {
            "id": document.id,
            "filename": document.filename,
            "status": document.status,
            "text_extracted": bool(extracted_text.strip()),
            "extracted_text_length": len(extracted_text),
            "chunks_created": chunks_created,
            "message": (
                "PDF uploaded, extracted, and indexed successfully."
                if chunks_created
                else (
                    "PDF uploaded, but no selectable text was found. "
                    "OCR may be required."
                )
            ),
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as exc:
        db.rollback()

        # Remove the saved file if database/indexing work failed.
        if saved_file_path is not None:
            try:
                saved_file_path.unlink(missing_ok=True)
            except OSError:
                pass

        raise HTTPException(
            status_code=500,
            detail="PDF upload and indexing failed.",
        ) from exc

    finally:
        file.file.close()


@app.get("/documents")
def list_documents(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    status_filter: str | None = Query(
        default=None,
        alias="status",
        pattern="^(pending|completed|needs_ocr)$",
    ),
    db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    query = db.query(Document)

    if status_filter is not None:
        query = query.filter(Document.status == status_filter)

    documents = (
        query
        .order_by(Document.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [
        {
            "id": document.id,
            "filename": document.filename,
            "content_type": document.content_type,
            "status": document.status,
            "created_at": document.created_at,
        }
        for document in documents
    ]


@app.get("/documents/{document_id}")
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = (
        db.query(Document)
        .filter(Document.id == document_id)
        .first()
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    return {
        "id": document.id,
        "filename": document.filename,
        "content_type": document.content_type,
        "status": document.status,
        "created_at": document.created_at,
    }


@app.patch("/documents/{document_id}")
def update_document_status(
    document_id: int,
    request: DocumentStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = (
        db.query(Document)
        .filter(Document.id == document_id)
        .first()
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    document.status = request.status
    db.commit()
    db.refresh(document)

    return {
        "id": document.id,
        "filename": document.filename,
        "status": document.status,
        "message": "Document status updated successfully.",
    }
