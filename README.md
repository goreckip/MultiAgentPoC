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
[case study (opis, architektura, walkthrough z realnym trace'em)](docs/case_study.md) ·
[architektura i stan projektu](docs/architecture.md) ·
[diagram sekwencji docelowego procesu](docs/sequence_diagram.md) ·
[lista wymagań ze statusem realizacji](docs/requirements.md)

## Architektura

1. **Klasyfikacja intencji** — 9 kategorii (8 procesowych + `inne`), patrz
   [`src/multiagent_poc/intents.py`](src/multiagent_poc/intents.py).
2. **Confidence gate** — poniżej progu pewności → dopytanie / eskalacja, nie halucynacja.
3. **RAG nad runbookami** — [`docs/runbooks/`](docs/runbooks/), Chroma jako wektorowa baza.
4. **Dwa agenty per kategoria procesu**, koordynowani przez agenta-router (LangGraph):
   subagent odpowiadający na pytanie ([`agents/subagent.py`](src/multiagent_poc/agents/subagent.py))
   i drafting agent przygotowujący gotowy dokument/zgłoszenie
   ([`agents/drafting_agent.py`](src/multiagent_poc/agents/drafting_agent.py), 7/8 kategorii —
   brakujące dane oznacza jawnym placeholderem, nie zgaduje).
5. **Walidacja danych wejściowych** — dane wrażliwe, format numeru zamówienia,
   uprawnienia do kategorii pytań, oraz opcjonalny załącznik PDF (np. zamówienie)
   jako dodatkowy kontekst, gdy klasyfikacja tekstowa ma zbyt niską pewność —
   zawsze poprzedzony skanem antywirusowym (ClamAV, lokalnie).
6. **Human-in-the-loop** — pytania eskalowane (niska pewność / kategoria `inne`) **oraz
   dokumenty z kategorii wrażliwych (BHP, HR)** trafiają do **współdzielonej kolejki**
   ([`src/multiagent_poc/hitl/queue.py`](src/multiagent_poc/hitl/queue.py)),
   widocznej dla operatora niezależnie od tego, który pracownik zadał pytanie —
   nie tylko z jego własnej sesji. Zaimplementowane przez `interrupt()` + checkpointer
   w LangGraph — graf zatrzymuje się na węźle i czeka na input człowieka.
7. **Observability** — Langfuse Cloud (free tier), zamiast self-hosted Dockera.
   Zagnieżdżone trace'y (walidacja → klasyfikacja → gate → subagent →
   generacja LLM z tokenami/latencją) — patrz
   [`src/multiagent_poc/observability/langfuse_client.py`](src/multiagent_poc/observability/langfuse_client.py).

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
  agents/             — subagent (odpowiedzi) + drafting agent (dokumenty) per kategoria
  graph/              — graf LangGraph (routing, confidence gate, HITL interrupt)
  validation/         — walidacja danych wejściowych, skan AV i parser PDF załącznika
  observability/      — integracja Langfuse (@observe, CallbackHandler)
  hitl/               — współdzielona kolejka eskalacji (queue.py)
tests/
data/chroma/          — lokalny wektorowy store (gitignored)
.clamav/               — lokalny, portable install ClamAV (gitignored, patrz Setup)
```

## Stack

LangGraph + LangChain, Ollama (Llama 3.1 8B, lokalnie), Chroma, Langfuse Cloud (free tier),
Streamlit (UI, w tym panel HITL do zatwierdzania eskalacji).
Wszystko darmowe.

## Status

Po Sprincie 7: wszystkie 7 warstw architektury mają działającą implementację,
zweryfikowaną na żywo, nie tylko testami z mockami, z **dwoma agentami per
kategoria** (subagent odpowiedzi + drafting agent dokumentów). Walidacja →
klasyfikacja intencji + confidence gate (opcjonalnie wspomagana załącznikiem
PDF) → subagent (RAG filtrowany do właściwego runbooka) → opcjonalnie
drafting agent (dokument, z placeholderami zamiast zgadywania brakujących
danych) → dla kategorii wrażliwych (BHP, HR) zawsze przez tę samą
współdzieloną kolejkę HITL co eskalacje, zanim trafi do pracownika.
Zweryfikowane end-to-end w przeglądarce: dokument BHP poprawnie trafił do
kolejki jako osobny typ ("dokument do zatwierdzenia"), operator zatwierdził,
pracownik dostał odpowiedź **i** dokument razem — złapano też realną
halucynację modelu (błędny rok w dacie), udokumentowaną, nie ukrytą.
Każde pytanie generuje zagnieżdżony trace w Langfuse Cloud (model, tokeny,
latencja, koszt), pobrany z powrotem przez API jako dowód, że dotarł.
Framework ewaluacyjny (`scripts/evaluate_rag.py`) zmierzył trafność RAG na
trzech niezależnych sygnałach (retrieval hit-rate 86%, pokrycie słów
kluczowych 38%, LLM-judge 4.67/5) i ujawnił konkretny przypadek błędu
retrievalu ukrytego przez przekonujący ton odpowiedzi — patrz
[`docs/decision_log.md`](docs/decision_log.md). Zostało: case study.
Pełny status per wymaganie — patrz [`docs/requirements.md`](docs/requirements.md).

## Wygląd UI

Paleta kolorów i typografia (`.streamlit/config.toml`, CSS w `app.py`) są
wizualnie inspirowane publiczną stroną Żabka.pl (kolory wyprowadzone z jej
CSS — patrz `docs/decision_log.md`, Sprint 8), bez użycia loga ani innych
znaków zastrzeżonych, i z jawnym zastrzeżeniem niezależności widocznym
bezpośrednio w UI. **To niezależny projekt portfolio, niezwiązany z i
nieautoryzowany przez Żabka Polska sp. z o.o.**

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

**Langfuse (observability):** załóż darmowe konto na
[cloud.langfuse.com](https://cloud.langfuse.com) (region EU) lub
[us.cloud.langfuse.com](https://us.cloud.langfuse.com) (region US), utwórz
projekt, wygeneruj klucze API (Settings → API Keys) i wklej je do `.env`
(`LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` zgodnie z
regionem). Bez kluczy tracing po prostu się wyłącza (SDK loguje ostrzeżenie,
reszta aplikacji działa normalnie).
