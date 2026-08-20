"""Per-category subagents (architecture layer 4).

Each subagent is the same retrieval+generation code (rag/retrieval.py) but
scoped two ways that generic RAG wasn't in Week 2:
1. Retrieval is filtered to *only* that intent's own runbook (Chroma `where`
   filter on the section collection), not the whole corpus — a "dostawy"
   question should never accidentally retrieve a BHP chunk just because it
   scored a decent embedding distance.
2. A short intent-specific system-prompt addendum nudges tone/emphasis
   toward what that runbook actually cares about (e.g. BHP => urgency,
   reklamacje => respect "czego NIE robimy" sections literally).
"""

from dataclasses import dataclass

import chromadb
from langchain_ollama import ChatOllama, OllamaEmbeddings

from multiagent_poc.config import settings
from multiagent_poc.intents import INTENT_RUNBOOK_MAP, Intent
from multiagent_poc.observability.langfuse_client import get_callback_handler, observe
from multiagent_poc.rag.index import COLLECTION_SECTION
from multiagent_poc.rag.retrieval import ANSWER_SYSTEM_PROMPT, RetrievedChunk

AGENT_PROMPT_ADDENDUM: dict[Intent, str] = {
    Intent.DOSTAWY: "Zwróć uwagę na progi eskalacji (wartość rozbieżności, powtarzalność problemu z dostawcą).",
    Intent.REKLAMACJE: 'Jeśli runbook zawiera sekcję "czego NIE robimy", potraktuj ją jako twardy zakaz, nie sugestię.',
    Intent.PLATNOSCI: "Bądź precyzyjny co do progów kwotowych — nie zaokrąglaj ani nie uogólniaj widełek.",
    Intent.BHP: "To może dotyczyć bezpieczeństwa ludzi — jeśli sytuacja brzmi poważnie, podkreśl pilność zgłoszenia.",
    Intent.HR: "Sprawy pracownicze bywają wrażliwe — utrzymuj neutralny, rzeczowy ton.",
    Intent.HIGIENA: "Odpowiadaj w duchu zgodności z HACCP — konkretne progi i czynności, nie ogólniki.",
    Intent.AWARIE_TECHNICZNE: "Odpowiedz w krokach możliwych do wykonania od razu przez pracownika na miejscu.",
    Intent.SKARGI_KLIENTA: "Sugeruj ton deeskalacyjny wobec klienta, zgodny z procedurą.",
}


@dataclass
class AgentAnswer:
    text: str
    sources: list[str]
    chunks: list[RetrievedChunk]


def _embeddings() -> OllamaEmbeddings:
    return OllamaEmbeddings(model=settings.ollama_embed_model, base_url=settings.ollama_base_url)


def _retrieve_for_intent(question: str, intent: Intent, client: chromadb.ClientAPI, k: int = 4) -> list[RetrievedChunk]:
    runbook_filename = INTENT_RUNBOOK_MAP[intent]
    collection = client.get_collection(COLLECTION_SECTION)
    result = collection.query(
        query_embeddings=[_embeddings().embed_query(question)],
        n_results=k,
        where={"source": runbook_filename},
    )
    chunks = []
    for doc, meta, dist in zip(result["documents"][0], result["metadatas"][0], result["distances"][0]):
        chunks.append(RetrievedChunk(text=doc, source=meta["source"], heading_path=meta.get("heading_path", ""), distance=dist))
    return chunks


@observe(name="subagent_answer")
def answer(question: str, intent: Intent, client: chromadb.ClientAPI | None = None) -> AgentAnswer:
    if intent == Intent.INNE:
        raise ValueError("Intent.INNE has no subagent/runbook — should have been escalated by the gate")

    client = client or chromadb.PersistentClient(path=settings.chroma_persist_dir)
    chunks = _retrieve_for_intent(question, intent, client)

    context = "\n\n---\n\n".join(f"[{c.source} | {c.heading_path}]\n{c.text}" for c in chunks)
    system_prompt = f"{ANSWER_SYSTEM_PROMPT}\n\n{AGENT_PROMPT_ADDENDUM[intent]}"
    llm = ChatOllama(model=settings.ollama_model, base_url=settings.ollama_base_url)
    response = llm.invoke(
        [("system", system_prompt), ("human", f"Kontekst:\n{context}\n\nPytanie: {question}")],
        config={"callbacks": [get_callback_handler()]},
    )

    return AgentAnswer(text=response.content, sources=sorted({c.source for c in chunks}), chunks=chunks)
