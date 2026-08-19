# Architektura i stan projektu

Ten dokument opisuje, co faktycznie istnieje w repo dzisiaj, jak się to spina, i
odsyła do reszty dokumentacji. Pełne uzasadnienia decyzji — patrz
[`decision_log.md`](decision_log.md). Diagram docelowego przepływu — patrz
[`sequence_diagram.md`](sequence_diagram.md). Checklisty wymagań — patrz
[`requirements.md`](requirements.md).

## Kontekst

Asystent operacyjny dla sklepów sieci convenience (kontekst zbliżony do
franczyzy typu Żabka). Pracownik/franczyzobiorca zadaje pytanie proceduralne,
system klasyfikuje intencję, sprawdza pewność klasyfikacji, i albo odpowiada
na bazie wewnętrznych runbooków (RAG), albo eskaluje do człowieka (HITL).
Pełne tło biznesowe i motywacja projektu (portfolio pod rozmowy AI PM,
inspiracja projektem Procurement z PwC) — patrz główny [`README.md`](../README.md).

## Warstwy architektury (docelowo)

1. Klasyfikacja intencji (9 kategorii: 8 procesowych + `inne`)
2. Confidence gate (próg pewności → auto-odpowiedź vs. eskalacja)
3. RAG nad runbookami (Chroma + Ollama)
4. Subagenci per kategoria procesu, koordynowani przez agenta-router (LangGraph)
5. Walidacja danych wejściowych (dane wrażliwe, format numeru zamówienia, uprawnienia)
6. Human-in-the-loop (kolejka zatwierdzeń dla eskalacji, `interrupt()` w LangGraph)
7. Observability (Langfuse Cloud, free tier)

## Co istnieje dzisiaj (2026-08-19, po Tygodniu 2)

### Zaimplementowane i przetestowane

| Moduł | Plik | Co robi |
|---|---|---|
| Katalog intencji | [`src/multiagent_poc/intents.py`](../src/multiagent_poc/intents.py) | `Enum` z 9 intencjami, mapowanie intencja → plik runbooka. Jedno źródło prawdy dla klasyfikatora, routera i indeksacji. |
| Konfiguracja | [`src/multiagent_poc/config.py`](../src/multiagent_poc/config.py) | Ustawienia Ollamy (osobne modele: generacja `llama3.1:8b`, embeddingi `nomic-embed-text`), Chroma, próg pewności, Langfuse Cloud. |
| Chunking | [`src/multiagent_poc/rag/chunking.py`](../src/multiagent_poc/rag/chunking.py) | Dwie strategie: `fixed_size_chunks` i `section_chunks` (po nagłówkach `##`/`###`, z zachowaniem ścieżki nagłówków). |
| Indeksacja | [`src/multiagent_poc/rag/index.py`](../src/multiagent_poc/rag/index.py) | Indeksuje runbooki do dwóch kolekcji Chroma (po jednej na strategię chunkingu). |
| Retrieval + generacja | [`src/multiagent_poc/rag/retrieval.py`](../src/multiagent_poc/rag/retrieval.py) | Zapytanie do Chroma + generacja odpowiedzi przez Ollama (`ChatOllama`), z promptem systemowym wymuszającym odpowiadanie tylko na bazie kontekstu. |
| Runbooki (RAG source) | [`docs/runbooks/`](runbooks/) | 8 mockowych procedur + README z celowymi pułapkami testowymi (zazębiające się kategorie, progi kwotowe, sekcje "czego NIE robimy"). |
| Pytania testowe | [`docs/test_questions.md`](test_questions.md) | 20 pytań pod klasyfikator/confidence gate/walidację, w tym dwuznaczne i spoza katalogu. |
| Testy jednostkowe | [`tests/`](../tests/) | `test_intents.py` (katalog intencji ↔ pliki runbooków), `test_chunking.py` (porównanie strukturalne dwóch strategii, bez potrzeby embeddingów). |
| Eksperyment porównawczy | [`scripts/compare_chunking.py`](../scripts/compare_chunking.py) | Realne porównanie retrievalu (żywe embeddingi) na pytaniu o pomyłkę dostawcy — wynik: `section_chunks` wygrywa, patrz decision log. |

**Zweryfikowane działanie:** `pytest` (4/4 testy), realna indeksacja do Chroma i
realny retrieval przez Ollama (`llama3.1:8b` + `nomic-embed-text`) — patrz wpis
"Tydzień 2 — dokończenie" w `decision_log.md`.

### Zaplanowane, jeszcze puste

| Moduł | Plik | Odpowiada za warstwę |
|---|---|---|
| Subagenci | `src/multiagent_poc/agents/` | 4 |
| Graf/routing | `src/multiagent_poc/graph/` | 2, 4 |
| Walidacja | `src/multiagent_poc/validation/` | 5 |
| HITL | `src/multiagent_poc/hitl/` | 6 |

Klasyfikator intencji, confidence gate, Streamlit UI i integracja Langfuse
jeszcze nie mają nawet szkieletu plików — patrz `requirements.md` po status.

## Stack

LangGraph + LangChain, Ollama (lokalnie: `llama3.1:8b` do generacji,
`nomic-embed-text` do embeddingów), Chroma (lokalna, persystentna), Langfuse
Cloud (free tier, zaplanowane), Streamlit (UI, zaplanowane).

## Środowisko dev

Python postawiony jako dystrybucja "embeddable" (`.python/`, gitignored) —
standardowy instalator MSI nie działał w tym środowisku (usługa Windows
Installer nie miała dostępu do plików tymczasowych). Szczegóły i obejście w
`decision_log.md` (Tydzień 2). Uruchamianie kodu: `.python/python.exe -m ...`
zamiast `python -m ...`, dopóki `.python/Scripts` nie jest dodane do PATH.
