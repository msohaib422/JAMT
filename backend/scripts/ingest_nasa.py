"""Idempotently ingest the bundled NASA dataset into ChromaDB."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ai.rag import NASA_KNOWLEDGE, _CHROMA_AVAILABLE, dataset_hash  # noqa: E402


def main() -> None:
    if not _CHROMA_AVAILABLE:
        print("ChromaDB is not installed. Knowledge remains available via the keyword fallback.")
        return

    import chromadb
    from app.ai.rag import _SentenceTransformerEmbeddingFunction

    persist_dir = os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_db")
    embedder = _SentenceTransformerEmbeddingFunction(os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"))
    client = chromadb.PersistentClient(path=persist_dir)
    collection = client.get_or_create_collection(
        name="nasa_knowledge",
        embedding_function=embedder,
        metadata={"hnsw:space": "cosine", "dataset_hash": dataset_hash()},
    )
    ids = [doc["id"] for doc in NASA_KNOWLEDGE]
    existing = set(collection.get(ids=ids, include=[]).get("ids", []))
    collection.upsert(
        ids=ids,
        documents=[doc["content"] for doc in NASA_KNOWLEDGE],
        metadatas=[{k: doc[k] for k in ("title", "source", "url", "category")} for doc in NASA_KNOWLEDGE],
    )
    collection.modify(metadata={"hnsw:space": "cosine", "dataset_hash": dataset_hash()})
    print(f"Added {len(set(ids) - existing)} documents; updated {len(existing)} documents in {persist_dir}")


if __name__ == "__main__":
    main()
