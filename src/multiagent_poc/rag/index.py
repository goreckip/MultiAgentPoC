"""Index runbooks into Chroma using either chunking strategy.

Two separate collections (one per strategy) so Sprint 2's retrieval comparison
can query both side by side without re-indexing.
"""

from pathlib import Path

import chromadb

from multiagent_poc.config import settings
from multiagent_poc.intents import INTENT_RUNBOOK_MAP, RUNBOOKS_DIR
from multiagent_poc.llm import embedding_model
from multiagent_poc.rag.chunking import Chunk, fixed_size_chunks, section_chunks

COLLECTION_FIXED = "runbooks_fixed_size"
COLLECTION_SECTION = "runbooks_section"


def _load_runbook_texts() -> list[tuple[str, str]]:
    """Returns (filename, text) for every runbook that has a document (skips `inne`)."""
    texts = []
    for filename in set(INTENT_RUNBOOK_MAP.values()):
        if filename is None:
            continue
        path: Path = RUNBOOKS_DIR / filename
        texts.append((filename, path.read_text(encoding="utf-8")))
    return texts


def _chunks_to_records(chunks: list[Chunk]) -> tuple[list[str], list[str], list[dict]]:
    ids = [f"{c.source}:{i}" for i, c in enumerate(chunks)]
    documents = [c.text for c in chunks]
    metadatas = [{"source": c.source, "strategy": c.strategy, "heading_path": c.heading_path or ""} for c in chunks]
    return ids, documents, metadatas


def build_index(client: chromadb.ClientAPI | None = None) -> chromadb.ClientAPI:
    client = client or chromadb.PersistentClient(path=settings.chroma_persist_dir)
    embeddings = embedding_model()

    fixed_collection = client.get_or_create_collection(COLLECTION_FIXED)
    section_collection = client.get_or_create_collection(COLLECTION_SECTION)

    for filename, text in _load_runbook_texts():
        fixed = fixed_size_chunks(text, source=filename)
        section = section_chunks(text, source=filename)

        ids, docs, metas = _chunks_to_records(fixed)
        fixed_collection.upsert(ids=ids, documents=docs, metadatas=metas, embeddings=embeddings.embed_documents(docs))

        ids, docs, metas = _chunks_to_records(section)
        section_collection.upsert(ids=ids, documents=docs, metadatas=metas, embeddings=embeddings.embed_documents(docs))

    return client


if __name__ == "__main__":
    build_index()
    print("Indexed runbooks into both collections:", COLLECTION_FIXED, "and", COLLECTION_SECTION)
