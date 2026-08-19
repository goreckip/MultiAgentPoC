# Wymagania — status realizacji

Legenda: ✅ zrobione i zweryfikowane · 🚧 częściowo / kod napisany, nie w pełni
zweryfikowany end-to-end · ⬜ nie zaczęte. Kolumna "Tydzień" to plan z
[`../README.md`](../README.md) (mile stone, niekoniecznie kalendarzowy tydzień).
MVP/Stretch — patrz sekcja "MVP vs. stretch goals" w oryginalnym planie.

## Warstwa 1 — Klasyfikacja intencji

| # | Wymaganie | Status | Tydzień | Zakres |
|---|---|---|---|---|
| 1.1 | Katalog intencji zdefiniowany (8 procesowych + `inne`) | ✅ | 1 | MVP |
| 1.2 | Jedno źródło prawdy: intencja ↔ plik runbooka | ✅ | 1 | MVP |
| 1.3 | Klasyfikator (embedding similarity lub lekki LLM classifier) | ⬜ | 3 | MVP |
| 1.4 | Zwracanie confidence score razem z intencją | ⬜ | 3 | MVP |

## Warstwa 2 — Confidence gate

| # | Wymaganie | Status | Tydzień | Zakres |
|---|---|---|---|---|
| 2.1 | Próg pewności w konfiguracji | ✅ (wartość domyślna w `config.py`, nieużywana jeszcze w logice) | 1 | MVP |
| 2.2 | Logika: powyżej progu → auto-odpowiedź | ⬜ | 3 | MVP |
| 2.3 | Logika: poniżej progu → dopytanie lub eskalacja | ⬜ | 3 | MVP |
| 2.4 | Test na pytaniach dwuznacznych (3, 10, 13 w `test_questions.md`) | ⬜ | 3 | MVP |
| 2.5 | Test na pytaniach spoza katalogu / kategoria `inne` (14, 15) | ⬜ | 3 | MVP |

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
| 4.1 | Graf LangGraph (routing między węzłami) | ⬜ | 4 | Stretch |
| 4.2 | Osobny subagent/prompt per kategoria procesu | ⬜ | 4 | Stretch |
| 4.3 | Routing przy zazębiających się kategoriach (pytania 3, 10, 13) | ⬜ | 4 | Stretch |

## Warstwa 5 — Walidacja danych wejściowych

| # | Wymaganie | Status | Tydzień | Zakres |
|---|---|---|---|---|
| 5.1 | Wykrywanie danych wrażliwych w pytaniu (np. PESEL — pytanie 16) | ⬜ | 4 | Stretch |
| 5.2 | Walidacja formatu numeru zamówienia (pytania 17, 18) | ⬜ | 4 | Stretch |
| 5.3 | Sprawdzanie uprawnień do kategorii pytań (pytanie 19) | ⬜ | 4 | Stretch |
| 5.4 | Odporność na prompt injection (pytanie 20) | ⬜ | 4 | Stretch |

## Warstwa 6 — Human-in-the-loop

| # | Wymaganie | Status | Tydzień | Zakres |
|---|---|---|---|---|
| 6.1 | Kolejka zatwierdzeń dla eskalacji (niska pewność / `inne`) | ⬜ | 4 | Stretch (dodane po planie bazowym) |
| 6.2 | `interrupt()` + checkpointer w LangGraph | ⬜ | 4 | Stretch |
| 6.3 | Panel HITL w Streamlit (człowiek widzi kolejkę, odpowiada) | ⬜ | 5 | Stretch |

## Warstwa 7 — Observability

| # | Wymaganie | Status | Tydzień | Zakres |
|---|---|---|---|---|
| 7.1 | Integracja z Langfuse Cloud (traces, koszty, latencja) | ⬜ | 4 | Stretch |
| 7.2 | Konfiguracja gotowa (klucze w `.env.example`, host cloud) | ✅ | 2 | — |

## Warstwa 8 — UI i polish

| # | Wymaganie | Status | Tydzień | Zakres |
|---|---|---|---|---|
| 8.1 | Streamlit UI (zadawanie pytań, wyświetlanie odpowiedzi) | ⬜ | 5 | Stretch |
| 8.2 | Testy end-to-end na pełnym pipeline | ⬜ | 5 | MVP (dla samego MVP: klasyfikacja→RAG→odpowiedź) |

## Warstwa 9 — Ewaluacja i dokumentacja

| # | Wymaganie | Status | Tydzień | Zakres |
|---|---|---|---|---|
| 9.1 | Zestaw pytań testowych (15-20, w tym dwuznaczne i "inne") | ✅ (20 pytań) | 1 | MVP |
| 9.2 | Log decyzji prowadzony na bieżąco | ✅ (aktualizowany co sesję) | ciągłe | MVP |
| 9.3 | Dokumentacja architektury | ✅ (ten zestaw dokumentów) | — | MVP |
| 9.4 | Diagram sekwencji docelowego procesu | ✅ (`sequence_diagram.md`) | — | MVP |
| 9.5 | Framework ewaluacyjny (trafność retrievalu i odpowiedzi) | ⬜ | 6 | Stretch |
| 9.6 | Case study / materiał na LinkedIn | ⬜ | 6 | Stretch |
| 9.7 | Porównanie LangChain/LangGraph vs Pydantic AI w README | ⬜ | 5 | Stretch |

## Infrastruktura / środowisko

| # | Wymaganie | Status | Uwagi |
|---|---|---|---|
| I.1 | Repo GitHub podłączone i zsynchronizowane | ✅ | `goreckip/MultiAgentPoC` |
| I.2 | Środowisko Python działające lokalnie | ✅ | dystrybucja embeddable, MSI nie działał w tym środowisku |
| I.3 | Ollama zainstalowana i modele pobrane | ✅ | `llama3.1:8b`, `nomic-embed-text` |
| I.4 | `pytest` przechodzi | ✅ | 4/4 testy |

## Skrócone podsumowanie (na dziś)

- **MVP core (klasyfikacja → RAG → odpowiedź z confidence gate):** RAG gotowe
  i zweryfikowane, klasyfikacja intencji i confidence gate — jeszcze nie zaczęte.
  To jest priorytet na Tydzień 3.
- **Stretch (subagenci, walidacja, HITL, Langfuse, UI, ewaluacja):** w całości
  przed nami, zaplanowane na Tygodnie 4-6.
