from fastapi.testclient import TestClient

from app import main


def test_query_returns_no_answer_when_search_finds_no_passages(monkeypatch):
    # Simulate semantic search finding no relevant document passages.
    monkeypatch.setattr(main, "semantic_search", lambda question, limit=3: [])

    client = TestClient(main.app)

    response = client.post(
        "/query",
        json={"question": "What is the company's annual revenue?"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["question"] == "What is the company's annual revenue?"
    assert data["answer"] == (
        "I could not find any indexed document passages "
        "to answer your question."
    )
    assert data["sources"] == []


def test_query_returns_answer_and_sources_when_passages_are_found(monkeypatch):
    # Simulate semantic search returning one relevant passage.
    fake_result = type(
        "SearchResult",
        (),
        {
            "filename": "sample_text_based_handbook.pdf",
            "document_id": 6,
            "chunk_id": 18,
            "chunk_text": "Employees must use secure networks.",
        },
    )()

    monkeypatch.setattr(
        main,
        "semantic_search",
        lambda question, limit=3: [fake_result],
    )

    # Simulate Gemini generating an answer from the retrieved passage.
    monkeypatch.setattr(
        main,
        "generate_answer",
        lambda question, context: "Employees must use secure networks.",
    )

    client = TestClient(main.app)

    response = client.post(
        "/query",
        json={"question": "What are the information security requirements?"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["answer"] == "Employees must use secure networks."
    assert len(data["sources"]) == 1
    assert data["sources"][0]["document_id"] == 6
    assert data["sources"][0]["filename"] == "sample_text_based_handbook.pdf"
    assert data["sources"][0]["chunk_id"] == 18
    assert data["sources"][0]["text"] == "Employees must use secure networks."


def test_query_returns_500_when_search_fails(monkeypatch):
    # Simulate an unexpected database or search error.
    def failing_search(question, limit=3):
        raise RuntimeError("Simulated search failure")

    monkeypatch.setattr(main, "semantic_search", failing_search)

    # Gemini should not be called if search fails.
    def unexpected_answer_call(question, context):
        raise AssertionError("Gemini should not be called")

    monkeypatch.setattr(main, "generate_answer", unexpected_answer_call)

    client = TestClient(main.app)

    response = client.post(
        "/query",
        json={"question": "What are the information security requirements?"},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Knowledge-base search failed."


def test_query_returns_502_when_gemini_fails(monkeypatch):
    # Simulate semantic search finding one relevant passage.
    fake_result = type(
        "SearchResult",
        (),
        {
            "filename": "sample_text_based_handbook.pdf",
            "document_id": 6,
            "chunk_id": 18,
            "chunk_text": "Employees must use secure networks.",
        },
    )()

    monkeypatch.setattr(
        main,
        "semantic_search",
        lambda question, limit=3: [fake_result],
    )

    # Simulate Gemini failing.
    def failing_answer(question, context):
        raise RuntimeError("Simulated Gemini failure")

    monkeypatch.setattr(main, "generate_answer", failing_answer)

    client = TestClient(main.app)

    response = client.post(
        "/query",
        json={"question": "What are the information security requirements?"},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == (
        "AI answer generation failed. Check server logs "
        "for the underlying error."
    )
