"""Nearest-neighbor intent classifier built on the exemplar phrases in
exemplars.py, embedded with the same Ollama embedding model used for RAG.

Classification = k-NN vote: embed the question, find the k closest exemplar
phrases in the intent_exemplars Chroma collection, and take a majority vote.
Confidence is the winning intent's vote share (e.g. 4/5 neighbors agreeing on
"dostawy" -> confidence 0.8) — deliberately simple and interpretable, so the
confidence_threshold in config.py has an intuitive meaning.
"""

from collections import Counter
from dataclasses import dataclass

import chromadb
from langchain_ollama import OllamaEmbeddings

from multiagent_poc.classification.exemplars import INTENT_EXEMPLARS
from multiagent_poc.config import settings
from multiagent_poc.intents import Intent

COLLECTION_EXEMPLARS = "intent_exemplars"


@dataclass
class IntentClassification:
    intent: Intent
    confidence: float
    vote_counts: dict[str, int]


def _embeddings() -> OllamaEmbeddings:
    return OllamaEmbeddings(model=settings.ollama_embed_model, base_url=settings.ollama_base_url)


def build_exemplar_index(client: chromadb.ClientAPI | None = None) -> chromadb.ClientAPI:
    client = client or chromadb.PersistentClient(path=settings.chroma_persist_dir)
    embeddings = _embeddings()
    # hnsw:space=cosine: default (l2, on raw un-normalized vectors) barely
    # separated short exemplar phrases in practice — see decision_log.md.
    existing = {c.name for c in client.list_collections()}
    if COLLECTION_EXEMPLARS in existing:
        client.delete_collection(COLLECTION_EXEMPLARS)
    collection = client.get_or_create_collection(COLLECTION_EXEMPLARS, metadata={"hnsw:space": "cosine"})

    ids, docs, metas = [], [], []
    for intent, phrases in INTENT_EXEMPLARS.items():
        for i, phrase in enumerate(phrases):
            ids.append(f"{intent.value}:{i}")
            docs.append(phrase)
            metas.append({"intent": intent.value})

    collection.upsert(ids=ids, documents=docs, metadatas=metas, embeddings=embeddings.embed_documents(docs))
    return client


def classify(
    question: str,
    client: chromadb.ClientAPI | None = None,
    k: int = 3,
) -> IntentClassification:
    client = client or chromadb.PersistentClient(path=settings.chroma_persist_dir)
    embeddings = _embeddings()
    collection = client.get_collection(COLLECTION_EXEMPLARS)

    result = collection.query(query_embeddings=[embeddings.embed_query(question)], n_results=k)
    neighbor_intents = [meta["intent"] for meta in result["metadatas"][0]]

    votes = Counter(neighbor_intents)
    winning_intent, winning_count = votes.most_common(1)[0]
    confidence = winning_count / len(neighbor_intents)

    return IntentClassification(
        intent=Intent(winning_intent),
        confidence=confidence,
        vote_counts=dict(votes),
    )


if __name__ == "__main__":
    build_exemplar_index()
    print("Indexed intent exemplars into collection:", COLLECTION_EXEMPLARS)
