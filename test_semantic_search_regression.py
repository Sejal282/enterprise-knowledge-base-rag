
import app.main as main



class FakeVector(list):
    def tolist(self):
        return list(self)


class FakeEmbeddingModel:
    def __init__(self):
        self.question = None

    def encode(self, question):
        self.question = question
        return FakeVector([0.25] * 384)



class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, rows):
        self.rows = rows
        self.query = None
        self.params = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, query, params):
        self.query = str(query)
        self.params = params
        return FakeResult(self.rows)


class FakeEngine:
    def __init__(self, rows):
        self.connection = FakeConnection(rows)

    def connect(self):
        return self.connection


def test_semantic_search_uses_question_embedding_and_search_parameters(
    monkeypatch,
):
    fake_model = FakeEmbeddingModel()

    expected_rows = [
        ("chunk 1",),
        ("chunk 2",),
    ]

    fake_engine = FakeEngine(expected_rows)

    monkeypatch.setattr(main, "embedding_model", fake_model)
    monkeypatch.setattr(main, "engine", fake_engine)

    results = main.semantic_search(
        "What are the security requirements?",
        limit=2,
        max_distance=0.55,
    )

    assert results == expected_rows
    assert fake_model.question == "What are the security requirements?"

    params = fake_engine.connection.params

    assert params["result_limit"] == 2
    assert params["max_distance"] == 0.55
    assert len(params["question_embedding"]) == 384


def test_semantic_search_query_filters_and_deduplicates_chunks(
    monkeypatch,
):
    fake_model = FakeEmbeddingModel()
    fake_engine = FakeEngine([])

    monkeypatch.setattr(main, "embedding_model", fake_model)
    monkeypatch.setattr(main, "engine", fake_engine)

    main.semantic_search("Find information about company security")

    query = fake_engine.connection.query

    assert "dc.embedding <=> :question_embedding" in query
    assert "< :max_distance" in query
    assert "PARTITION BY dc.chunk_text" in query
    assert "duplicate_rank = 1" in query
    assert "LIMIT :result_limit" in query


def test_semantic_search_returns_empty_list_when_no_chunks_match(
    monkeypatch,
):
    fake_model = FakeEmbeddingModel()
    fake_engine = FakeEngine([])

    monkeypatch.setattr(main, "embedding_model", fake_model)
    monkeypatch.setattr(main, "engine", fake_engine)

    results = main.semantic_search(
        "Question with no matching passages"
    )

    assert results == []
