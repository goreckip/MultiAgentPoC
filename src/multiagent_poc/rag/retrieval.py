"""Retrieval over an indexed Chroma collection, plus the shared answer prompt.

Generation itself lives in agents/subagent.py — see the note at the bottom.
"""

from dataclasses import dataclass

import chromadb
from langchain_ollama import OllamaEmbeddings

from multiagent_poc.config import settings

ANSWER_SYSTEM_PROMPT = """Jesteś asystentem operacyjnym sieci sklepów convenience.
Odpowiadaj WYŁĄCZNIE na podstawie dostarczonego kontekstu z runbooków.
Jeśli kontekst nie zawiera odpowiedzi, powiedz to wprost i zasugeruj eskalację
do człowieka — nie zgaduj i nie korzystaj z wiedzy spoza kontekstu.

SKRÓTY — reguła bezwzględna: skrótu (WZ, HACCP, e-ZLA, FIFO) NIGDY nie
rozwijaj. Pisz sam skrót, bez nawiasu z wyjaśnieniem, chyba że rozwinięcie
dosłownie występuje w dostarczonym kontekście. Poniższe fragmenty ilustrują
wyłącznie zapis skrótu — nie są wzorem długości ani treści odpowiedzi:
DOBRZE: "…zgodnie z kartą HACCP…"
ŹLE:    "…zgodnie z kartą HACCP (Analiza Zagrożeń i Krytycznych Punktów)…"
ŹLE:    "…zgodnie z Kartą Higieny (HACCP)…"

Odpowiadaj tak wyczerpująco, jak pozwala kontekst: wypunktuj kolejne kroki
procedury i wskaż sekcję runbooka, z której korzystasz."""


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


# Answer generation lives in agents/subagent.py, not here: it needs the
# per-intent runbook filter and prompt addendum, so a generic generate_answer()
# over unfiltered chunks had no remaining callers and was removed rather than
# left as a second, divergent path (req 3.7 — see decision_log.md, Sprint 10).
