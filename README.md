# Enterprise Knowledge Base RAG API

A Python backend API that allows users to upload PDF documents, search their content using semantic search, and ask questions using a Retrieval-Augmented Generation (RAG) pipeline.

## Features

- Upload PDF documents
- Extract text from PDF files
- Split document text into chunks
- Generate text embeddings using Sentence Transformers
- Store document chunks and embeddings in PostgreSQL with pgvector
- Perform semantic search using cosine distance
- Generate answers using the Gemini API
- Return relevant source passages with answers
- List, retrieve, and update document information
- Validate API requests and handle errors
- Automated regression tests for query and semantic-search behavior

## Technology Stack

- Python
- FastAPI
- PostgreSQL
- SQLAlchemy
- pgvector
- Sentence Transformers
- Google Gemini API
- PyMuPDF
- Pydantic
- Pytest

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Root endpoint |
| GET | `/health` | Health check |
| POST | `/documents/upload` | Upload a PDF document |
| POST | `/query` | Ask a question about indexed documents |
| GET | `/documents` | List documents |
| GET | `/documents/{document_id}` | Retrieve a document |
| PATCH | `/documents/{document_id}` | Update document information |

Interactive API documentation is available at `/docs` when the application is running.

## Requirements

- Python 3.12
- PostgreSQL
- pgvector PostgreSQL extension
- Gemini API key

## Installation and Setup

### 1. Clone the repository

```bash
git clone <your-github-repository-url>
cd enterprise-knowledge-base-rag
```

### 2. Create and activate a virtual environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Configure PostgreSQL

Create a PostgreSQL database named:

```text
enterprise_kb
```

Enable the pgvector extension in that database:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

The application currently uses this local database connection:

```text
postgresql+psycopg://localhost:5432/enterprise_kb
```

If your PostgreSQL configuration differs, update `DATABASE_URL` in `app/database.py`.

### 5. Configure the Gemini API key

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=YOUR_KEY
```

Do not commit your `.env` file or expose your API key publicly.

### 6. Create database tables

```bash
python create_tables.py
```

## Run the Application

Start the FastAPI development server:

```bash
python -m uvicorn app.main:app --reload
```

Open the interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

## Run Tests

Run the automated test suite:

```bash
python -m pytest -v
```

## Project Structure

```text
enterprise-knowledge-base-rag/
├── app/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── llm.py
│   ├── pdf_utils.py
│   └── chunking.py
├── uploads/
├── create_tables.py
├── requirements.txt
├── README.md
└── test_*.py
```

## Notes

- The application uses a local PostgreSQL database.
- PDF upload currently accepts PDF files only.
- Answers are generated from retrieved document passages.
- If no relevant indexed passages are found, the API returns a safe no-answer response.
