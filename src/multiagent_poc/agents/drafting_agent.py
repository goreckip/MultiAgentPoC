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


from multiagent_poc.agents.abbreviations import strip_invented_expansions
from multiagent_poc.intents import Intent
from multiagent_poc.llm import chat_model
from multiagent_poc.observability.langfuse_client import get_callback_handler, observe
from multiagent_poc.rag.retrieval import RetrievedChunk

DRAFT_SYSTEM_PROMPT = """Jesteś asystentem przygotowującym gotowe dokumenty/zgłoszenia dla \
pracowników sieci sklepów convenience, na podstawie procedur wewnętrznych i pytania pracownika.

Przygotuj treść dokumentu typu "{doc_type}", zawierającego pola: {fields}.

Zasady:
- Najpierw poszukaj wartości każdego pola w treści pytania ORAZ w załączonym dokumencie
  (jeśli został dołączony). Numery zamówień, nazwy dostawców i daty często występują
  wyłącznie w załączniku — przepisz je stamtąd dosłownie.
- Placeholder [uzupełnij: nazwa_pola] wstawiaj TYLKO wtedy, gdy danej informacji nie ma
  ani w pytaniu, ani w załączniku. Nigdy nie zgaduj wartości.
- Nie wstawiaj placeholdera obok pola, które już wypełniłeś — każde pole ma mieć albo
  wartość, albo placeholder, nigdy jedno i drugie.
- SKRÓTY — reguła bezwzględna: skrótu (WZ, HACCP, e-ZLA, FIFO) NIGDY nie rozwijaj.
  Pisz sam skrót, bez nawiasu z wyjaśnieniem, chyba że rozwinięcie dosłownie występuje
  w dostarczonym tekście. Poniższe fragmenty ilustrują wyłącznie zapis skrótu:
  DOBRZE: "…zgodnie z kartą HACCP…"
  ŹLE:    "…zgodnie z kartą HACCP (Analiza Zagrożeń i Krytycznych Punktów)…"
  ŹLE:    "…zgodnie z Kartą Higieny (HACCP)…"
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
def draft_document(
    question: str,
    intent: Intent,
    chunks: list[RetrievedChunk],
    attachment_text: str | None = None,
) -> DraftedDocument | None:
    """Returns None when the intent has no document template — callers should
    treat that as "no draft available for this category", not an error.

    `attachment_text` (req 5.8) lets the agent fill fields from a document the
    employee attached — an order PDF carrying the order number the question
    itself never mentioned — instead of emitting a placeholder for it.
    """
    spec = DOCUMENT_TEMPLATES.get(intent)
    if spec is None:
        return None

    context = "\n\n---\n\n".join(f"[{c.source} | {c.heading_path}]\n{c.text}" for c in chunks)
    system_prompt = DRAFT_SYSTEM_PROMPT.format(doc_type=spec.doc_type, fields=", ".join(spec.required_fields))

    human_parts = [f"Kontekst proceduralny:\n{context}"]
    if attachment_text:
        human_parts.append(
            "Dokument załączony przez pracownika — użyj go jako źródła danych do pól "
            f"(np. numeru zamówienia, dostawcy, dat):\n{attachment_text}"
        )
    human_parts.append(f"Pytanie pracownika: {question}")

    llm = chat_model()
    response = llm.invoke(
        [("system", system_prompt), ("human", "\n\n".join(human_parts))],
        config={"callbacks": [get_callback_handler()]},
    )

    # Same deterministic guard as the answering agent — an invented expansion
    # is worse in a filed document than in a chat reply.
    clean_text = strip_invented_expansions(response.content, f"{context}\n{attachment_text or ''}")

    return DraftedDocument(doc_type=spec.doc_type, text=clean_text, requires_review=spec.requires_human_review)
