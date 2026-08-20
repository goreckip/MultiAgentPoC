"""Document-drafting agent (architecture layer 4, second agent role).

Distinct from agents/subagent.py: that one answers a procedural question,
this one produces a ready-to-file document (zgłoszenie, karta zdarzenia,
wniosek...) for the same category. Deliberately reuses the chunks a
subagent.answer() call already retrieved instead of querying Chroma again —
same runbook context grounds both the answer and the draft.

Only 7 of 8 process intents have a template (see rag_eval_set-style ground
truth reasoning in decision_log.md for the category analysis) — `higiena` is
excluded on purpose, it's a compliance-logging category, not a
correspondence one. `inne` never reaches this agent at all.
"""

from dataclasses import dataclass

from langchain_ollama import ChatOllama

from multiagent_poc.config import settings
from multiagent_poc.intents import Intent
from multiagent_poc.observability.langfuse_client import get_callback_handler, observe
from multiagent_poc.rag.retrieval import RetrievedChunk

DRAFT_SYSTEM_PROMPT = """Jesteś asystentem przygotowującym gotowe dokumenty/zgłoszenia dla \
pracowników sieci sklepów convenience, na podstawie procedur wewnętrznych i pytania pracownika.

Przygotuj treść dokumentu typu "{doc_type}", zawierającego pola: {fields}.

Zasady:
- Jeśli którejś informacji potrzebnej do pola brakuje w pytaniu pracownika, NIE zgaduj —
  wstaw w tym miejscu placeholder w formacie [uzupełnij: nazwa_pola].
- Opieraj się wyłącznie na dostarczonym kontekście proceduralnym i treści pytania.
- Odpowiedz WYŁĄCZNIE treścią dokumentu, gotową do wklejenia do systemu wewnętrznego —
  bez dodatkowego komentarza, bez "Oto dokument:" na początku."""


@dataclass
class DocumentSpec:
    doc_type: str
    required_fields: list[str]
    requires_human_review: bool


DOCUMENT_TEMPLATES: dict[Intent, DocumentSpec] = {
    Intent.DOSTAWY: DocumentSpec(
        doc_type="Zgłoszenie rozbieżności dostawy",
        required_fields=["numer_zamowienia_lub_dostawy", "dostawca", "opis_rozbieznosci", "data_dostawy"],
        requires_human_review=False,
    ),
    Intent.REKLAMACJE: DocumentSpec(
        doc_type="Zgłoszenie reklamacji",
        required_fields=["produkt", "data_zakupu", "opis_wady", "forma_zwrotu"],
        requires_human_review=False,
    ),
    Intent.PLATNOSCI: DocumentSpec(
        doc_type="Pisemne wyjaśnienie rozbieżności kasowej",
        required_fields=["kwota_rozbieznosci", "data_zmiany", "wyjasnienie"],
        requires_human_review=False,
    ),
    Intent.BHP: DocumentSpec(
        doc_type="Karta zdarzenia BHP",
        required_fields=["data_godzina_zdarzenia", "opis_zdarzenia", "udzielona_pomoc", "swiadkowie"],
        requires_human_review=True,
    ),
    Intent.HR: DocumentSpec(
        doc_type="Wniosek/pismo kadrowe",
        required_fields=["typ_wniosku", "okres", "uzasadnienie"],
        requires_human_review=True,
    ),
    Intent.AWARIE_TECHNICZNE: DocumentSpec(
        doc_type="Zgłoszenie serwisowe",
        required_fields=["urzadzenie", "numer_seryjny", "opis_awarii"],
        requires_human_review=False,
    ),
    Intent.SKARGI_KLIENTA: DocumentSpec(
        doc_type="Rejestr incydentu",
        required_fields=["opis_zdarzenia", "uczestnicy", "sposob_rozwiazania"],
        requires_human_review=False,
    ),
    # Intent.HIGIENA and Intent.INNE deliberately absent — see module docstring.
}


@dataclass
class DraftedDocument:
    doc_type: str
    text: str
    requires_review: bool


@observe(name="draft_document")
def draft_document(question: str, intent: Intent, chunks: list[RetrievedChunk]) -> DraftedDocument | None:
    """Returns None when the intent has no document template — callers should
    treat that as "no draft available for this category", not an error.
    """
    spec = DOCUMENT_TEMPLATES.get(intent)
    if spec is None:
        return None

    context = "\n\n---\n\n".join(f"[{c.source} | {c.heading_path}]\n{c.text}" for c in chunks)
    system_prompt = DRAFT_SYSTEM_PROMPT.format(doc_type=spec.doc_type, fields=", ".join(spec.required_fields))
    llm = ChatOllama(model=settings.ollama_model, base_url=settings.ollama_base_url)
    response = llm.invoke(
        [("system", system_prompt), ("human", f"Kontekst proceduralny:\n{context}\n\nPytanie pracownika: {question}")],
        config={"callbacks": [get_callback_handler()]},
    )

    return DraftedDocument(doc_type=spec.doc_type, text=response.content, requires_review=spec.requires_human_review)
