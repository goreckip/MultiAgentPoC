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

1. Klasyfikacja intencji (9 kategorii: 8 procesowych + `inne`) — ✅
2. Confidence gate (próg pewności → auto-odpowiedź vs. eskalacja) — ✅
3. RAG nad runbookami (Chroma + Ollama) — ✅
4. Subagenci per kategoria procesu, koordynowani przez agenta-router (LangGraph) — ✅
5. Walidacja danych wejściowych (dane wrażliwe, format numeru zamówienia, uprawnienia, załącznik PDF + skan AV) — ✅
6. Human-in-the-loop (`interrupt()` w LangGraph) — 🚧 mechanizm działa, brak trwałej kolejki dla wielu jednoczesnych eskalacji
7. Observability (Langfuse Cloud, free tier) — ✅

## Co istnieje dzisiaj (2026-08-20, po Tygodniu 5 część 2)

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
| Eksperyment porównawczy (chunking) | [`scripts/compare_chunking.py`](../scripts/compare_chunking.py) | Realne porównanie retrievalu (żywe embeddingi) na pytaniu o pomyłkę dostawcy — wynik: `section_chunks` wygrywa, patrz decision log. |
| Katalog przykładów intencji | [`src/multiagent_poc/classification/exemplars.py`](../src/multiagent_poc/classification/exemplars.py) | 6 przykładowych fraz na każdą z 8 intencji procesowych (celowo inne niż w `test_questions.md`, żeby uniknąć data leakage). |
| Klasyfikator intencji | [`src/multiagent_poc/classification/classifier.py`](../src/multiagent_poc/classification/classifier.py) | k-NN (k=3) nad embeddingami przykładów w Chroma (`intent_exemplars`); confidence = odsetek zgodnych głosów wśród sąsiadów. |
| Confidence gate | [`src/multiagent_poc/classification/gate.py`](../src/multiagent_poc/classification/gate.py) | Powyżej progu (`config.confidence_threshold`) → auto-routing na wykrytą intencję; poniżej → efektywna intencja `inne` + eskalacja. |
| Zbiór ewaluacyjny | [`src/multiagent_poc/classification/eval_set.py`](../src/multiagent_poc/classification/eval_set.py) | Strukturalna kopia `docs/test_questions.md` do automatycznych testów klasyfikatora. |
| Eksperyment porównawczy (klasyfikator) | [`scripts/evaluate_classifier.py`](../scripts/evaluate_classifier.py) | Uruchamia klasyfikator + gate na całym zbiorze ewaluacyjnym, raportuje trafność i każdą pomyłkę. |
| Skan antywirusowy załącznika | [`src/multiagent_poc/validation/attachment_scan.py`](../src/multiagent_poc/validation/attachment_scan.py) | Wywołuje lokalny `clamscan.exe` (ClamAV), blokujące i bezwarunkowe przed jakimkolwiek parsowaniem. |
| Parser PDF | [`src/multiagent_poc/validation/attachment.py`](../src/multiagent_poc/validation/attachment.py) | Ekstrakcja tekstu (pypdf), tylko warstwa tekstowa, bez OCR. |
| Pipeline klasyfikacja+załącznik | [`src/multiagent_poc/classification/pipeline.py`](../src/multiagent_poc/classification/pipeline.py) | Spina klasyfikator + gate + opcjonalny załącznik: reklasyfikacja z treścią PDF tylko gdy pytanie samo w sobie miało zbyt niską pewność. Zastępczo za graf LangGraph do czasu Tygodnia 4/2. |
| Demo end-to-end (na żywo) | [`scripts/demo_attachment_pipeline.py`](../scripts/demo_attachment_pipeline.py) | Pokazuje realny przypadek, gdzie załącznik podnosi pewność klasyfikacji powyżej progu. |
| Walidacja danych wejściowych | [`src/multiagent_poc/validation/input_validation.py`](../src/multiagent_poc/validation/input_validation.py) | PESEL (regex + suma kontrolna), prompt injection, prośby o dane osób trzecich → twardy odrzut; zły format numeru zamówienia → flaga, nie blokada. |
| Subagenci per kategoria | [`src/multiagent_poc/agents/subagent.py`](../src/multiagent_poc/agents/subagent.py) | Retrieval+generacja z Tygodnia 2, ale filtrowane do runbooka danej intencji + krótki dopisek do promptu per kategoria. |
| Graf LangGraph (routing + HITL) | [`src/multiagent_poc/graph/pipeline_graph.py`](../src/multiagent_poc/graph/pipeline_graph.py) | Spina walidację+klasyfikację+gate+załącznik (`classification/pipeline.py`) z subagentem albo węzłem eskalacji przez `interrupt()`/`Command(resume=...)`, z `MemorySaver` jako checkpointerem. |
| Demo grafu end-to-end (na żywo) | [`scripts/demo_graph.py`](../scripts/demo_graph.py) | Trzy realne przypadki: auto-odpowiedź, odrzucenie walidacji, eskalacja z pauzą i wznowieniem HITL. |
| Streamlit UI | [`app.py`](../app.py) | Formularz pytania (+ opcjonalny upload PDF), panel HITL operatora, historia rozmowy ze szczegółami technicznymi. Jedna strona, dwie sekcje — patrz decision log po uzasadnienie. |
| Observability (Langfuse) | [`src/multiagent_poc/observability/langfuse_client.py`](../src/multiagent_poc/observability/langfuse_client.py) | `@observe()` na kluczowych funkcjach (walidacja, klasyfikacja, gate, subagent) tworzy zagnieżdżone spany; `CallbackHandler` przekazany do `ChatOllama.invoke()` łapie model/tokeny/latencję generacji jako observation typu `GENERATION`. |
| Root trace grafu | [`src/multiagent_poc/graph/pipeline_graph.py`](../src/multiagent_poc/graph/pipeline_graph.py) (`invoke_graph`) | Jedyny punkt wejścia do `graph.invoke()`/`Command(resume=...)` w `app.py` i `scripts/demo_graph.py` — daje jeden trace na całe pytanie zamiast osobnych trace'ów per węzeł. |

**Zweryfikowane działanie:** `pytest` (32/32 testy), pełny graf na żywo
(auto-odpowiedź z Ollama, odrzucenie walidacji, pauza/wznowienie HITL) —
patrz wpisy "Tydzień 3", "Tydzień 4" i "Tydzień 5" w `decision_log.md`, w tym
uczciwie odnotowane znane ograniczenie klasyfikatora ujawnione w live demo
grafu, pełny przepływ zweryfikowany ręcznie w przeglądarce (Streamlit UI),
oraz realny trace pobrany z powrotem przez Langfuse API (`lf.api.trace.get(...)`)
potwierdzający poprawne zagnieżdżenie spanów i przechwycone tokeny/latencję.

### Zaplanowane, jeszcze puste

| Moduł | Plik | Odpowiada za warstwę |
|---|---|---|
| HITL — trwała kolejka (wiele jednoczesnych eskalacji) | `src/multiagent_poc/hitl/` | 6 |

## Stack

LangGraph + LangChain, Ollama (lokalnie: `llama3.1:8b` do generacji,
`nomic-embed-text` do embeddingów), Chroma (lokalna, persystentna), Langfuse
Cloud (free tier — działa), Streamlit (UI — działa, `app.py`).

## Środowisko dev

Python postawiony jako dystrybucja "embeddable" (`.python/`, gitignored) —
standardowy instalator MSI nie działał w tym środowisku (usługa Windows
Installer nie miała dostępu do plików tymczasowych). Szczegóły i obejście w
`decision_log.md` (Tydzień 2). Uruchamianie kodu: `.python/python.exe -m ...`
zamiast `python -m ...`, dopóki `.python/Scripts` nie jest dodane do PATH.
