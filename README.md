# Multi-Agent Retail Ops Assistant (PoC)

Asystent operacyjny dla sklepów sieci convenience — franczyzobiorcy/pracownicy zadają
pytania proceduralne (dostawy, reklamacje, płatności, BHP, HR, higiena, awarie
techniczne, skargi klienta). System klasyfikuje intencję, sprawdza pewność klasyfikacji,
i albo odpowiada na bazie wewnętrznych runbooków (RAG), albo eskaluje do człowieka.

Projekt portfolio pod rozmowy AI PM — świadomie zbliżony realiami do franczyzy typu
Żabka, modelowany na projekcie Procurement (PwC), ale doprowadzony do końca łącznie z
warstwą walidacji danych wejściowych, której w tamtym projekcie zabrakło.

Pełny plan i harmonogram: patrz log decyzji w [`docs/decision_log.md`](docs/decision_log.md).

## Architektura

1. **Klasyfikacja intencji** — 9 kategorii (8 procesowych + `inne`), patrz
   [`src/multiagent_poc/intents.py`](src/multiagent_poc/intents.py).
2. **Confidence gate** — poniżej progu pewności → dopytanie / eskalacja, nie halucynacja.
3. **RAG nad runbookami** — [`docs/runbooks/`](docs/runbooks/), Chroma jako wektorowa baza.
4. **Subagenci per kategoria procesu**, koordynowani przez agenta-router (LangGraph).
5. **Walidacja danych wejściowych** — dane wrażliwe, format numeru zamówienia,
   uprawnienia do kategorii pytań.
6. **Observability** — Langfuse (self-hosted, Docker).

## Struktura repo

```
docs/
  runbooks/          — mockowe procedury (źródło RAG)
  test_questions.md  — zestaw pytań testowych klasyfikatora/confidence gate
  decision_log.md    — log decyzji projektowych (materiał na STAR)
src/multiagent_poc/
  intents.py         — katalog intencji (źródło prawdy)
  config.py          — konfiguracja (Ollama/Chroma/Langfuse)
  rag/                — chunking, indeksacja, retrieval
  agents/             — subagenci per kategoria
  graph/              — graf LangGraph (routing, confidence gate)
  validation/         — walidacja danych wejściowych
tests/
data/chroma/          — lokalny wektorowy store (gitignored)
```

## Stack

LangGraph + LangChain, Ollama (Llama 3.1 8B, lokalnie), Chroma, Langfuse (self-hosted),
Streamlit (UI, opcjonalnie). Wszystko darmowe / lokalne.

## Status

Tydzień 1 (szkielet): struktura projektu, katalog intencji, runbooki, pytania testowe.
Kolejne kroki — patrz `docs/decision_log.md` i TODO w `docs/runbooks/README.md`.

## Setup (dev)

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -e ".[dev]"
cp .env.example .env
ollama pull llama3.1:8b
pytest
```
