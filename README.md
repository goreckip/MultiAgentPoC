# Multi-Agent Retail Ops Assistant (PoC)

Asystent operacyjny dla sklepów sieci convenience — franczyzobiorcy/pracownicy zadają
pytania proceduralne (dostawy, reklamacje, płatności, BHP, HR, higiena, awarie
techniczne, skargi klienta). System klasyfikuje intencję, sprawdza pewność klasyfikacji,
i albo odpowiada na bazie wewnętrznych runbooków (RAG), albo eskaluje do człowieka.

Projekt portfolio pod rozmowy AI PM — świadomie zbliżony realiami do franczyzy typu
Żabka, modelowany na projekcie Procurement (PwC), ale doprowadzony do końca łącznie z
warstwą walidacji danych wejściowych, której w tamtym projekcie zabrakło.

Pełny plan i harmonogram: patrz log decyzji w [`docs/decision_log.md`](docs/decision_log.md).

**Dokumentacja:**
[architektura i stan projektu](docs/architecture.md) ·
[diagram sekwencji docelowego procesu](docs/sequence_diagram.md) ·
[lista wymagań ze statusem realizacji](docs/requirements.md)

## Architektura

1. **Klasyfikacja intencji** — 9 kategorii (8 procesowych + `inne`), patrz
   [`src/multiagent_poc/intents.py`](src/multiagent_poc/intents.py).
2. **Confidence gate** — poniżej progu pewności → dopytanie / eskalacja, nie halucynacja.
3. **RAG nad runbookami** — [`docs/runbooks/`](docs/runbooks/), Chroma jako wektorowa baza.
4. **Subagenci per kategoria procesu**, koordynowani przez agenta-router (LangGraph).
5. **Walidacja danych wejściowych** — dane wrażliwe, format numeru zamówienia,
   uprawnienia do kategorii pytań, oraz opcjonalny załącznik PDF (np. zamówienie)
   jako dodatkowy kontekst, gdy klasyfikacja tekstowa ma zbyt niską pewność —
   zawsze poprzedzony skanem antywirusowym (ClamAV, lokalnie).
6. **Human-in-the-loop** — pytania eskalowane (niska pewność / kategoria `inne`) trafiają
   do kolejki zatwierdzeń; człowiek odpowiada albo zatwierdza/edytuje odpowiedź z RAG
   zanim pójdzie do użytkownika. Zaimplementowane przez `interrupt()` + checkpointer
   w LangGraph — graf zatrzymuje się na węźle i czeka na input człowieka.
7. **Observability** — Langfuse Cloud (free tier), zamiast self-hosted Dockera.

## Struktura repo

```
docs/
  runbooks/          — mockowe procedury (źródło RAG)
  test_questions.md  — zestaw pytań testowych klasyfikatora/confidence gate
  decision_log.md    — log decyzji projektowych (materiał na STAR)
app.py                — Streamlit UI (pytanie + upload PDF, panel HITL, historia)
src/multiagent_poc/
  intents.py         — katalog intencji (źródło prawdy)
  config.py          — konfiguracja (Ollama/Chroma/Langfuse)
  rag/                — chunking, indeksacja, retrieval
  classification/     — klasyfikator intencji, confidence gate, pipeline z załącznikiem
  agents/             — subagenci per kategoria
  graph/              — graf LangGraph (routing, confidence gate, HITL interrupt)
  validation/         — walidacja danych wejściowych, skan AV i parser PDF załącznika
  hitl/               — kolejka zatwierdzeń, integracja z Streamlit UI
tests/
data/chroma/          — lokalny wektorowy store (gitignored)
.clamav/               — lokalny, portable install ClamAV (gitignored, patrz Setup)
```

## Stack

LangGraph + LangChain, Ollama (Llama 3.1 8B, lokalnie), Chroma, Langfuse Cloud (free tier),
Streamlit (UI, w tym panel HITL do zatwierdzania eskalacji).
Wszystko darmowe.

## Status

Po Tygodniu 5 (część 1): warstwy 1-5 kompletne i spięte w jeden graf
LangGraph, z działającym UI — walidacja → klasyfikacja intencji + confidence
gate (opcjonalnie wspomagana załącznikiem PDF) → subagent per kategoria (RAG
filtrowany do właściwego runbooka) albo eskalacja do człowieka przez
`interrupt()`/`resume`, obsługiwana w panelu HITL w Streamlit
([`app.py`](app.py)). Zweryfikowane na żywo end-to-end w przeglądarce, łącznie
z uczciwie udokumentowanym, realnym przypadkiem błędnej klasyfikacji — patrz
[`docs/decision_log.md`](docs/decision_log.md). Zostało: Langfuse (czeka na
konto), trwała kolejka HITL dla wielu jednoczesnych eskalacji, framework
ewaluacyjny. Pełny status per wymaganie — patrz
[`docs/requirements.md`](docs/requirements.md).

## Uruchomienie UI

```bash
streamlit run app.py
```
Wymaga działającej Ollamy (`llama3.1:8b`, `nomic-embed-text` — patrz Setup
poniżej) i wcześniej zbudowanego indeksu Chroma
(`python -m multiagent_poc.rag.index` oraz
`python -m multiagent_poc.classification.classifier` do zaindeksowania
przykładów intencji). Odpowiedzi generowane lokalnie na CPU — jeden pełny
cykl (klasyfikacja + generacja) może potrwać do ok. minuty, patrz `decision_log.md`.

## Setup (dev)

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -e ".[dev]"
cp .env.example .env
ollama pull llama3.1:8b
pytest
```

Uwaga (Windows): jeśli standardowy instalator Pythona (MSI) nie działa w Twoim
środowisku (np. sandbox blokujący usługę Windows Installer), zadziałał wariant
embeddable Python + ręczny `get-pip.py` — patrz `docs/decision_log.md`.

**ClamAV (do skanu załączników):** pobierz portable build z
[GitHub Releases Cisco-Talos/clamav](https://github.com/Cisco-Talos/clamav/releases)
(`*.win.x64.zip`), rozpakuj do `.clamav/clamav-<wersja>.win.x64/` w katalogu
projektu, potem zaktualizuj bazy sygnatur:
```bash
cd .clamav/clamav-<wersja>.win.x64
./freshclam.exe --config-file=freshclam.conf   # wymaga freshclam.conf, patrz decision_log.md
```
Jeśli Twoja wersja/ścieżka różni się od domyślnej, ustaw `CLAMSCAN_PATH` i
`CLAMAV_DB_PATH` w `.env`.
