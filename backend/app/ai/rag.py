"""Offline retrieval over the extracted text of official NASA publications.

Every chunk in the index is a verbatim extract from a full text published on
NASA Technical Reports Server (see ``nasa_documents.json``).  This module
deliberately contains **no hand-written scientific content**: if a query has no
match above the relevance threshold, nothing is returned and callers must say
the information could not be verified.

Retrieval supports Moon, Mars, human-spaceflight and engineering categories,
preserves per-chunk document provenance (NTRS id, title, URL, publication date,
page) and falls back cleanly when optional ChromaDB/sentence-transformers are
not installed.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

DATA_PATH = Path(__file__).with_name("data") / "nasa_knowledge.json"
MIN_RELEVANCE = 0.25
#: Cap the number of chunks served from a single document per query
MAX_CHUNKS_PER_DOCUMENT = 2

_STOP_WORDS = frozenset(
    "the a an and or of to in on for with by is are was were be been being "
    "from at as it its this that these those but not you your we our they "
    "how what when where who why does did has have can could would should "
    "please tell me about into over under between".split()
)


# ---------------------------------------------------------------------------
# Dataset loading
# ---------------------------------------------------------------------------


def _load_knowledge() -> List[Dict[str, Any]]:
    """Load the extracted NASA-document chunks.

    Returns an empty list when the index is missing or malformed — never a
    fallback to hand-written content.
    """
    try:
        payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return []
    if isinstance(payload, dict):
        chunks = payload.get("chunks") or []
    else:  # legacy list format
        chunks = payload if isinstance(payload, list) else []
    cleaned: List[Dict[str, Any]] = []
    for chunk in chunks:
        if not isinstance(chunk, dict) or not chunk.get("content"):
            continue
        cleaned.append(chunk)
    return cleaned


NASA_KNOWLEDGE = _load_knowledge()


def dataset_hash(documents: Optional[Sequence[Dict[str, Any]]] = None) -> str:
    payload = json.dumps(
        list(NASA_KNOWLEDGE if documents is None else documents),
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def document_inventory() -> List[Dict[str, Any]]:
    """Return one metadata record per indexed publication (for ``/sources``)."""
    documents: Dict[str, Dict[str, Any]] = {}
    for chunk in NASA_KNOWLEDGE:
        key = chunk.get("ntrs_id")
        if not key:
            continue
        entry = documents.setdefault(
            key,
            {
                "ntrs_id": key,
                "title": chunk.get("title"),
                "document_id": chunk.get("document_id"),
                "sti_type": chunk.get("sti_type"),
                "publication_date": chunk.get("publication_date"),
                "distribution": chunk.get("distribution"),
                "url": chunk.get("url"),
                "pdf_url": chunk.get("pdf_url"),
                "category": chunk.get("category"),
                "topics": chunk.get("topics", []),
                "planetary_body": chunk.get("planetary_body"),
                "license": chunk.get("license"),
                "retrieved": chunk.get("retrieved"),
                "chunks": 0,
            },
        )
        entry["chunks"] += 1
    return list(documents.values())


# ---------------------------------------------------------------------------
# Keyword scoring helpers
# ---------------------------------------------------------------------------


def _tokenize(text: str) -> List[str]:
    tokens = re.findall(r"[a-zA-Z]{3,}", (text or "").lower())
    return [token for token in tokens if token not in _STOP_WORDS]


def _score(query_tokens: List[str], chunk: Dict[str, Any]) -> float:
    if not query_tokens:
        return 0.0
    content_tokens = _tokenize(
        chunk.get("title", "")
        + " "
        + chunk.get("content", "")
        + " "
        + " ".join(chunk.get("topics", []))
        + " "
        + str(chunk.get("category", ""))
    )
    if not content_tokens:
        return 0.0

    content_set = set(content_tokens)
    freq: Dict[str, int] = {}
    for token in content_tokens:
        freq[token] = freq.get(token, 0) + 1

    query_set = set(query_tokens)
    overlap = sum(1 for token in query_set if token in content_set)
    # Cap per-token term frequency so single repeated words dominate less
    tf = sum(min(freq.get(token, 0), 3) for token in query_set)

    title_tokens = set(_tokenize(chunk.get("title", "")))
    title_boost = sum(1.0 for token in query_set if token in title_tokens) * 0.6

    return (overlap + 0.1 * tf + title_boost) / max(len(query_set), 1)


def _matches_category(chunk: Dict[str, Any], category: Optional[str | Sequence[str]]) -> bool:
    if not category:
        return True
    allowed = {category} if isinstance(category, str) else set(category)
    chunk_category = chunk.get("category")
    chunk_topics = set(chunk.get("topics", []) or [])
    return chunk_category in allowed or bool(chunk_topics & allowed)


def _chunk_identity(chunk: Dict[str, Any]) -> Tuple[Any, Any]:
    return (chunk.get("ntrs_id"), chunk.get("page"))


def _signature(chunk: Dict[str, Any]) -> str:
    return hashlib.sha256(re.sub(r"\s+", " ", chunk.get("content", "").lower()).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Public search
# ---------------------------------------------------------------------------

try:
    _CHROMA_AVAILABLE = importlib.util.find_spec("chromadb") is not None
except Exception:  # pragma: no cover
    _CHROMA_AVAILABLE = False
chromadb = None

try:
    _ST_AVAILABLE = importlib.util.find_spec("sentence_transformers") is not None
except Exception:  # pragma: no cover
    _ST_AVAILABLE = False
SentenceTransformer = None


class _SentenceTransformerEmbeddingFunction:
    def __init__(self, model_name: str):
        global SentenceTransformer
        if not _ST_AVAILABLE:
            raise RuntimeError("sentence-transformers is unavailable")
        if SentenceTransformer is None:
            from sentence_transformers import SentenceTransformer as _SentenceTransformer  # type: ignore
            SentenceTransformer = _SentenceTransformer
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def __call__(self, input: List[str]) -> List[List[float]]:
        return self.model.encode(input, normalize_embeddings=True).tolist()

    def name(self) -> str:
        return f"sentence-transformers:{self.model_name}"


class NasaRagRetriever:
    """Keyword retrieval with an optional ChromaDB/semantic upgrade path."""

    def __init__(self, persist_directory: str = "./chroma_db", embedding_model: str = "all-MiniLM-L6-v2"):
        self.persist_directory = persist_directory
        self.embedding_model = embedding_model
        self._chroma_client = None
        self._collection = None
        self._embedder = None

    def _try_init_chroma(self) -> bool:
        global chromadb
        if not _CHROMA_AVAILABLE or not _ST_AVAILABLE:
            return False
        try:
            if chromadb is None:
                import chromadb as _chromadb  # type: ignore
                chromadb = _chromadb
            self._embedder = _SentenceTransformerEmbeddingFunction(self.embedding_model)
            self._chroma_client = chromadb.PersistentClient(path=self.persist_directory)
            self._collection = self._chroma_client.get_or_create_collection(
                name="nasa_knowledge",
                embedding_function=self._embedder,
                metadata={"hnsw:space": "cosine", "dataset_hash": dataset_hash()},
            )
            if (self._collection.metadata or {}).get("dataset_hash") != dataset_hash() or self._collection.count() != len(NASA_KNOWLEDGE):
                self._collection.upsert(
                    ids=[chunk["id"] for chunk in NASA_KNOWLEDGE],
                    documents=[chunk["content"] for chunk in NASA_KNOWLEDGE],
                    metadatas=[{k: chunk.get(k) for k in (
                        "title", "source", "url", "pdf_url", "category", "ntrs_id",
                        "document_id", "publication_date", "page", "section", "topics",
                    )} for chunk in NASA_KNOWLEDGE],
                )
                self._collection.modify(metadata={"hnsw:space": "cosine", "dataset_hash": dataset_hash()})
            return True
        except Exception:
            self._chroma_client = None
            self._collection = None
            self._embedder = None
            return False

    def retrieve(self, query: str, top_k: int = 4, category: Optional[str | Sequence[str]] = None) -> List[Dict[str, Any]]:
        query = (query or "").strip()
        if not query:
            return []
        if self._collection is None:
            self._try_init_chroma()

        if self._collection is not None:
            try:
                where = None
                if isinstance(category, str):
                    where = {"category": category}
                elif category:
                    where = {"category": {"$in": list(category)}}
                results = self._collection.query(query_texts=[query], n_results=top_k, where=where)
                docs = results.get("documents", [[]])[0]
                metas = results.get("metadatas", [[]])[0]
                distances = results.get("distances", [[]])[0] if results.get("distances") else []
                retrieved = []
                for idx, content in enumerate(docs):
                    meta = metas[idx] if idx < len(metas) else {}
                    score = 1.0 - float(distances[idx]) if idx < len(distances) else 0.0
                    if score >= MIN_RELEVANCE:
                        topics = meta.get("topics") or []
                        if isinstance(topics, str):
                            topics = [topics]
                        retrieved.append({
                            **meta,
                            "topics": topics,
                            "content": content,
                            "score": round(score, 3),
                        })
                if retrieved:
                    return _deduplicate(_cap_per_document(retrieved, MAX_CHUNKS_PER_DOCUMENT))
            except Exception:
                pass

        tokens = _tokenize(query)
        scored = [(_score(tokens, chunk), chunk) for chunk in NASA_KNOWLEDGE if _matches_category(chunk, category)]
        scored = [(score, chunk) for score, chunk in scored if score >= MIN_RELEVANCE]
        scored.sort(key=lambda pair: (-pair[0], str(pair[1].get("ntrs_id", "")), str(pair[1].get("page", ""))))
        results = [
            {**chunk, "score": round(score, 3)}
            for score, chunk in scored[: top_k * 2]  # extra candidates for deduplication
        ]
        return _deduplicate(_cap_per_document(results, MAX_CHUNKS_PER_DOCUMENT))[:top_k]


def _deduplicate(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    unique = []
    for chunk in chunks:
        fingerprint = _signature(chunk)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        unique.append(chunk)
    return unique


def _cap_per_document(chunks: List[Dict[str, Any]], cap: int) -> List[Dict[str, Any]]:
    counts: Dict[Any, int] = {}
    limited = []
    for chunk in chunks:
        key = chunk.get("ntrs_id") or chunk.get("id")
        count = counts.get(key, 0)
        if count >= cap:
            continue
        counts[key] = count + 1
        limited.append(chunk)
    return limited


_DEFAULT_RETRIEVER = NasaRagRetriever()


def search_nasa_knowledge(
    query: str,
    top_k: int = 4,
    category: Optional[str | Sequence[str]] = None,
) -> List[Dict[str, Any]]:
    """Retrieve NASA passages with full document provenance for the model."""
    return _DEFAULT_RETRIEVER.retrieve(query, top_k=top_k, category=category)
