import json

from app.ai import rag


SUGGESTED_QUESTIONS = [
    "Our oxygen is decreasing. What should I do?",
    "How do I handle a solar radiation storm?",
    "What are the backup power procedures?",
    "Evaluate my mission status.",
]


def test_suggested_questions_have_relevant_retrieval(monkeypatch):
    monkeypatch.setattr(rag, "_CHROMA_AVAILABLE", False)
    rag._DEFAULT_RETRIEVER._collection = None
    for question in SUGGESTED_QUESTIONS:
        results = rag.search_nasa_knowledge(question)
        assert results
        assert results[0]["content"]


def test_keyword_fallback_when_chroma_is_unavailable(monkeypatch):
    monkeypatch.setattr(rag, "_CHROMA_AVAILABLE", False)
    retriever = rag.NasaRagRetriever()
    results = retriever.retrieve("solar radiation storm", top_k=2, category="radiation")
    assert results
    assert all(item["category"] == "radiation" for item in results)


def test_nasa_dataset_is_valid():
    data = json.loads(rag.DATA_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert data["documents_indexed"] >= 14
    chunks = data["chunks"]
    assert chunks, "knowledge base must not be empty"
    ids = [item["id"] for item in chunks]
    assert len(ids) == len(set(ids))
    for item in chunks:
        for key in ("ntrs_id", "title", "source", "document_id", "distribution", "url", "topics", "category", "content"):
            assert item.get(key) is not None or key == "document_id", f"{item.get('id')} missing {key}"
        assert item["url"].startswith("https://ntrs.nasa.gov/citations/")
        assert item["distribution"] == "PUBLIC"
        assert item["content"].strip()
    # every chunk must be traceable to a document indexed in the manifest
    manifest = json.loads(rag.DATA_PATH.with_name("nasa_documents.json").read_text(encoding="utf-8"))
    indexed = {doc["ntrs_id"] for doc in manifest["documents"]}
    assert {item["ntrs_id"] for item in chunks} <= indexed
