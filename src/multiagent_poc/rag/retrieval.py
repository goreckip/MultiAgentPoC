"""Retrieval + naive generation over an indexed Chroma collection."""

from dataclasses import dataclass

import chromadb
from langchain_ollama import ChatOllama, OllamaEmbeddings

from multiagent_poc.config import settings

ANSWER_SYSTEM_PROMPT = """Jesteś asystentem operacyjnym sieci sklepów convenience.
Odpowiadaj WYŁĄCZNIE na podstawie dostarczonego kontekstu z runbooków.
Jeśli kontekst nie zawiera odpowiedzi, powiedz to wprost i zasugeruj eskalację
do człowieka — nie zgaduj i nie korzystaj z wiedzy spoza kontekstu."""


@dataclass
class RetrievedChunk:
    text: str
    source: str
    heading_path: str
    distance: float


def retrieve(
    query: str,
    collection_name: str,
    client: chromadb.ClientAPI | None = None,
    k: int = 4,
) -> list[RetrievedChunk]:
    client = client or chromadb.PersistentClient(path=settings.chroma_persist_dir)
    embeddings = OllamaEmbeddings(model=settings.ollama_embed_model, base_url=settings.ollama_base_url)
    collection = client.get_collection(collection_name)

    result = collection.query(query_embeddings=[embeddings.embed_query(query)], n_results=k)

    chunks = []
    for doc, meta, dist in zip(result["documents"][0], result["metadatas"][0], result["distances"][0]):
        chunks.append(
            RetrievedChunk(text=doc, source=meta["source"], heading_path=meta.get("heading_path", ""), distance=dist)
        )
    return chunks


def generate_answer(query: str, chunks: list[RetrievedChunk]) -> str:
    context = "\n\n---\n\n".join(f"[{c.source} | {c.heading_path}]\n{c.text}" for c in chunks)
    llm = ChatOllama(model=settings.ollama_model, base_url=settings.ollama_base_url)
    messages = [
        ("system", ANSWER_SYSTEM_PROMPT),
        ("human", f"Kontekst:\n{context}\n\nPytanie: {query}"),
    ]
    response = llm.invoke(messages)
    return response.content
