# Wymagania — status realizacji

Legenda: ✅ zrobione i zweryfikowane · 🚧 częściowo / kod napisany, nie w pełni
zweryfikowany end-to-end · ⬜ nie zaczęte · ❌ świadomie odrzucone z planu
(z datą i uzasadnieniem w `decision_log.md`). Kolumna "Tydzień" to plan z
[`../README.md`](../README.md) (mile stone, niekoniecznie kalendarzowy tydzień).
MVP/Stretch — patrz sekcja "MVP vs. stretch goals" w oryginalnym planie.

## Warstwa 1 — Klasyfikacja intencji

| # | Wymaganie | Status | Tydzień | Zakres |
|---|---|---|---|---|
| 1.1 | Katalog intencji zdefiniowany (8 procesowych + `inne`) | ✅ | 1 | MVP |
| 1.2 | Jedno źródło prawdy: intencja ↔ plik runbooka | ✅ | 1 | MVP |
| 1.3 | Klasyfikator (embedding similarity lub lekki LLM classifier) | ✅ (k-NN nad exemplarami, `classification/classifier.py`) | 3 | MVP |
| 1.4 | Zwracanie confidence score razem z intencją | ✅ (odsetek głosów, `IntentClassification.confidence`) | 3 | MVP |

## Warstwa 2 — Confidence gate

| # | Wymaganie | Status | Tydzień | Zakres |
|---|---|---|---|---|
| 2.1 | Próg pewności w konfiguracji | ✅ | 1 | MVP |
| 2.2 | Logika: powyżej progu → auto-odpowiedź | ✅ (`classification/gate.py`) | 3 | MVP |
| 2.3 | Logika: poniżej progu → eskalacja (efektywna intencja `inne`) | ✅ | 3 | MVP (dopytanie zamiast eskalacji — nie zrobione, patrz uwaga w `sequence_diagram.md`) |
| 2.4 | Test na pytaniach dwuznacznych (3, 10, 13 w `test_questions.md`) | 🚧 (zmierzone, ale klasyfikator ich nie rozróżnia dobrze — patrz `decision_log.md`) | 3 | MVP |
| 2.5 | Test na pytaniach spoza katalogu / danych wrażliwych (14-16, 19, 20) | ✅ (5/5 poprawnie eskalowanych, `test_classifier.py`) | 3 | MVP |

## Warstwa 3 — RAG nad runbookami

| # | Wymaganie | Status | Tydzień | Zakres |
|---|---|---|---|---|
| 3.1 | Mockowe runbooki (min. 5-10 dokumentów, różne kategorie) | ✅ (8 dokumentów) | 1 | MVP |
| 3.2 | Chunking — strategia fixed-size | ✅ | 2 | MVP |
| 3.3 | Chunking — strategia po sekcjach | ✅ | 2 | MVP |
| 3.4 | Porównanie obu strategii na realnym przykładzie | ✅ (`scripts/compare_chunking.py`, wynik: section wygrywa) | 2 | MVP |
| 3.5 | Indeksacja w Chroma | ✅ | 2 | MVP |
| 3.6 | Retrieval (query → top-k chunków) | ✅ | 2 | MVP |
| 3.7 | Generacja odpowiedzi na bazie kontekstu | 🚧 (kod gotowy w `retrieval.generate_answer`, nie mam jeszcze end-to-end testu z realnym pytaniem użytkownika przez cały pipeline) | 2 | MVP |
| 3.8 | Model embeddingowy oddzielony od modelu generacyjnego | ✅ (`nomic-embed-text` vs `llama3.1:8b`) | 2 | — (decyzja dodatkowa) |

## Warstwa 4 — Subagenci per kategoria + router

| # | Wymaganie | Status | Tydzień | Zakres |
|---|---|---|---|---|
| 4.1 | Graf LangGraph (routing między węzłami) | ✅ (`graph/pipeline_graph.py`) | 4 | Stretch |
| 4.2 | Osobny subagent/prompt per kategoria procesu | ✅ (`agents/subagent.py`, retrieval filtrowany do runbooka + prompt per kategoria) | 4 | Stretch |
| 4.3 | Routing przy zazębiających się kategoriach (pytania 3, 10, 13) | ⬜ (nie osobno testowane w grafie — dziedziczy ograniczenia klasyfikatora z Tygodnia 3) | 4 | Stretch |

## Warstwa 5 — Walidacja danych wejściowych

| # | Wymaganie | Status | Tydzień | Zakres |
|---|---|---|---|---|
| 5.1 | Wykrywanie danych wrażliwych w pytaniu (np. PESEL — pytanie 16) | ✅ (regex + suma kontrolna PESEL, `validation/input_validation.py`) | 4 | Stretch |
| 5.2 | Walidacja formatu numeru zamówienia (pytania 17, 18) | ✅ (flaguje, nie blokuje — patrz decision log) | 4 | Stretch |
| 5.3 | Sprawdzanie uprawnień do kategorii pytań (pytanie 19) | ✅ (heurystyka: pytanie o wynagrodzenie osoby trzeciej → odrzut) | 4 | Stretch |
| 5.4 | Odporność na prompt injection (pytanie 20) | ✅ (lista wzorców, np. "ignoruj poprzednie instrukcje") | 4 | Stretch |
| 5.5 | Załącznik PDF (np. zamówienie) jako dodatkowy kontekst, gdy `confidence < próg` | ✅ (`classification/pipeline.py`, zweryfikowane na żywo — patrz `decision_log.md`) | 4 | Stretch (dodane po planie bazowym, 2026-08-19) |
| 5.6 | Skan antywirusowy załącznika przed jakimkolwiek parsowaniem/przekazaniem dalej | ✅ (ClamAV lokalnie, blokujące i bezwarunkowe — `validation/attachment_scan.py`) | 4 | Stretch |
| 5.7 | Parsowanie treści PDF (tekst → embedding, bez OCR obrazów na start) | ✅ (`validation/attachment.py`, pypdf) | 4 | Stretch |
| 5.8 | Agent "data retrieval" wykorzystujący treść załącznika w odpowiedzi | ⬜ | 5+ | Stretch — followup po 5.5-5.7, osobny agent w warstwie 4 |

## Warstwa 6 — Human-in-the-loop

| # | Wymaganie | Status | Tydzień | Zakres |
|---|---|---|---|---|
| 6.1 | Kolejka zatwierdzeń dla eskalacji (niska pewność / `inne`) | ✅ (`hitl/queue.py`, współdzielona między sesjami, zweryfikowana na żywo w dwóch niezależnych kartach przeglądarki) | 4 | Stretch (dodane po planie bazowym) |
| 6.2 | `interrupt()` + checkpointer w LangGraph | ✅ (`graph/pipeline_graph.py`, zweryfikowane na żywo w `scripts/demo_graph.py`) | 4 | Stretch |
| 6.3 | Panel HITL w Streamlit (człowiek widzi kolejkę, odpowiada) | ✅ (`app.py`, sekcja 2 — jedno pytanie na raz, nie trwała kolejka wielu jednocześnie) | 5 | Stretch |

## Warstwa 7 — Observability

| # | Wymaganie | Status | Tydzień | Zakres |
|---|---|---|---|---|
| 7.1 | Integracja z Langfuse Cloud (traces, koszty, latencja) | ✅ (`observability/langfuse_client.py`, zweryfikowane realnym trace'em przez API — patrz `decision_log.md`) | 4 | Stretch |
| 7.2 | Konfiguracja gotowa (klucze w `.env.example`, host cloud) | ✅ | 2 | — |

## Warstwa 8 — UI i polish

| # | Wymaganie | Status | Tydzień | Zakres |
|---|---|---|---|---|
| 8.1 | Streamlit UI (zadawanie pytań, wyświetlanie odpowiedzi) | ✅ (`app.py`, w tym upload PDF i szczegóły techniczne w expanderze) | 5 | Stretch |
| 8.2 | Testy end-to-end na pełnym pipeline | ✅ (ręczna weryfikacja w przeglądarce: auto-odpowiedź, odrzucenie walidacji, HITL pause/resume — patrz `decision_log.md`) | 5 | MVP (dla samego MVP: klasyfikacja→RAG→odpowiedź) |

## Warstwa 9 — Ewaluacja i dokumentacja

| # | Wymaganie | Status | Tydzień | Zakres |
|---|---|---|---|---|
| 9.1 | Zestaw pytań testowych (15-20, w tym dwuznaczne i "inne") | ✅ (20 pytań) | 1 | MVP |
| 9.2 | Log decyzji prowadzony na bieżąco | ✅ (aktualizowany co sesję) | ciągłe | MVP |
| 9.3 | Dokumentacja architektury | ✅ (ten zestaw dokumentów) | — | MVP |
| 9.4 | Diagram sekwencji docelowego procesu | ✅ (`sequence_diagram.md`) | — | MVP |
| 9.5 | Framework ewaluacyjny (trafność retrievalu i odpowiedzi) | ⬜ | 6 | Stretch |
| 9.6 | Case study / materiał na LinkedIn | ⬜ | 6 | Stretch |
| ~~9.7~~ | ~~Porównanie LangChain/LangGraph vs Pydantic AI w README~~ | ❌ odrzucone z planu (2026-08-20) | 5 | Stretch |

## Infrastruktura / środowisko

| # | Wymaganie | Status | Uwagi |
|---|---|---|---|
| I.1 | Repo GitHub podłączone i zsynchronizowane | ✅ | `goreckip/MultiAgentPoC` |
| I.2 | Środowisko Python działające lokalnie | ✅ | dystrybucja embeddable, MSI nie działał w tym środowisku |
| I.3 | Ollama zainstalowana i modele pobrane | ✅ | `llama3.1:8b`, `nomic-embed-text` |
| I.4 | `pytest` przechodzi | ✅ | 32/32 testy (po Tygodniu 4) |
| I.5 | ClamAV zainstalowane lokalnie (do skanu załączników) | ✅ | portable build, `.clamav/` (gitignored) |

## Skrócone podsumowanie (na dziś)

- **MVP core + większość stretch celów Tygodnia 4 gotowe:** walidacja → gate
  → klasyfikacja → (opcjonalnie załącznik) → subagent/RAG albo HITL, spięte w
  jeden graf LangGraph z działającym `interrupt()`/`resume`. Zweryfikowane na
  żywo (`scripts/demo_graph.py`), nie tylko testami z mockami.
- **Klasyfikator — znana słabość, teraz widoczna też w grafie:** 65% top-1
  accuracy (Tydzień 3). Live demo grafu ujawniło realny przypadek błędnej
  klasyfikacji (pytanie o sanepid → `hr` zamiast eskalacji) — uczciwie
  udokumentowane w `decision_log.md`, nie ukryte. Pytania bezpieczeństwa
  (dane wrażliwe/prompt injection/spoza katalogu) nadal 100% poprawnie
  odrzucane/eskalowane.
- **Wszystkie 7 warstw architektury mają teraz działającą implementację**
  (Langfuse jako ostatnia, Tydzień 5 część 2) — zweryfikowana realnym
  trace'em pobranym z powrotem przez API Langfuse, nie tylko "wysłane i mam
  nadzieję że doszło".
- **Kolejka HITL dokończona** (Tydzień 5 część 3) — współdzielona między
  sesjami/użytkownikami (moduł `hitl/queue.py`), zweryfikowana na żywo w
  dwóch niezależnych kartach przeglądarki. Uproszczenie: w pamięci procesu,
  nie w trwałej bazie — patrz `decision_log.md`.
- **Zostało realnie do zrobienia:** routing przy jawnie zazębiających się
  kategoriach, framework ewaluacyjny, case study. Porównanie LangChain vs
  Pydantic AI świadomie odrzucone z planu (patrz 9.7).
