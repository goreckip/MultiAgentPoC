# Log decyzji

Format: decyzja → dlaczego (trade-off) → efekt/obserwacja. Wpis po każdym sensownym
etapie, surowy materiał pod przyszłe STAR.

## Tydzień 1 — 2026-08-19

- **Decyzja:** framework agentowy: LangGraph jako baza szkieletu (zamiast Pydantic AI + pydantic-deep).
  **Dlaczego:** LangGraph ma dojrzalsze wsparcie dla grafu stanów i multi-agent routingu
  (confidence gate jako węzeł warunkowy, subagenci per kategoria jako osobne node'y) oraz
  więcej przykładów/dokumentacji do szybkiego postawienia szkieletu. Porównanie z Pydantic AI
  zaplanowane później (Tydzień 5, README) — jedno drzewo decyzyjne trzeba było wybrać jako pierwsze.
  **Efekt:** TBD po zbudowaniu grafu (Tydzień 3-4).

- **Decyzja:** katalog intencji zdefiniowany jako `Enum` w kodzie (`src/multiagent_poc/intents.py`),
  z mapowaniem intencja → plik runbooka, zamiast trzymania tylko w dokumentacji.
  **Dlaczego:** pojedyncze źródło prawdy używane jednocześnie przez klasyfikator, router
  subagentów i indeksację RAG — unika rozjazdu między dokumentacją a kodem.
  **Efekt:** test `test_intents.py` pilnuje, że każda intencja poza `inne` ma istniejący plik runbooka.

- **Decyzja:** kategoria `inne` celowo nie ma runbooka.
  **Dlaczego:** to podstawowy test confidence gate — system musi rozpoznać brak trafnych
  chunków / niską pewność klasyfikacji i eskalować do człowieka zamiast halucynować
  odpowiedź na bazie najbliższego tematycznie dokumentu.
  **Efekt:** do zweryfikowania w Tygodniu 3 na pytaniach 14-20 z `docs/test_questions.md`.

## Tydzień 2 — dokończenie (realny eksperyment) — 2026-08-19

- **Decyzja:** finalnie wybieram `section_chunks` (chunking po `##`/`###`) jako
  strategię produkcyjną dla RAG, nie fixed-size.
  **Dlaczego:** uruchomiony realny eksperyment (Ollama + `nomic-embed-text`,
  `scripts/compare_chunking.py`) na pytaniu z README runbooków ("dostawca przywiózł
  inny towar niż zamówiony, kierowca już odjechał") potwierdza to na żywych danych:
  - `fixed_size` (500 znaków, overlap 50): najlepszy wynik (distance 0.4286) trafia
    właściwą sekcję 4.3, ale **chunk zaczyna się od uciętego słowa "ransporcie..."**
    (środek zdania z poprzedniej sekcji) i nie ma żadnej informacji o tym, do jakiej
    sekcji należy — model dostałby fragment bez kontekstu. Wyniki #2 i #3 to
    kompletnie niepowiązane fragmenty (kasa, BHP).
  - `section`: najlepszy wynik (distance 0.4090, niższy = lepszy) to **cały,
    samodzielny akapit sekcji 4.3** z pełną ścieżką nagłówków w treści
    ("4. Rozbieżności ilościowe i jakościowe > 4.3 Pomyłka dostawcy...") — czytelny
    i gotowy do wklejenia w prompt bez dodatkowej obróbki.
  **Efekt:** `COLLECTION_SECTION` (`runbooks_section`) będzie domyślną kolekcją
  używaną przez warstwę RAG w kolejnych tygodniach; `COLLECTION_FIXED` zostaje w
  kodzie jako baseline porównawczy do README/demo, nie jako ścieżka produkcyjna.

- **Decyzja:** osobny model do embeddingów (`nomic-embed-text`, ~274MB) zamiast
  używania `llama3.1:8b` (modelu generatywnego) do liczenia wektorów.
  **Dlaczego:** `llama3.1:8b` nie jest modelem embeddingowym — użycie go do tego
  celu byłoby wolniejsze i przyniosłoby gorszą jakość wyszukiwania niż dedykowany,
  mały model embeddingowy. Rozdzielenie ról (embedding vs. generacja) to
  standardowa praktyka w architekturach RAG.
  **Efekt:** `config.py` ma teraz `ollama_embed_model` obok `ollama_model`.

## Aktualizacja planu — 2026-08-19

- **Decyzja:** Langfuse Cloud (free/Hobby tier) zamiast self-hosted (Docker).
  **Dlaczego:** free tier wystarcza na traces/koszty/latencję/podstawowe evals w PoC
  i eliminuje cały krok stawiania i utrzymywania kontenerów w Tygodniu 4. Trade-off:
  dane (treść pytań/odpowiedzi) trafiają na serwery Langfuse (EU/US) zamiast zostać
  lokalnie — akceptowalne, bo runbooki i pytania testowe są w całości fikcyjne/mockowe;
  gdyby projekt miał kiedyś realne dane, ta decyzja wymagałaby rewizji.
  **Efekt:** TBD po integracji w Tygodniu 4 — do zweryfikowania czy limity free tier
  (liczba eventów/mies.) wystarczą na testy end-to-end.

- **Decyzja:** dodanie warstwy Human-in-the-loop (7. w architekturze) jako osobnego
  elementu, nie tylko "eskalacja = koniec".
  **Dlaczego:** confidence gate i tak kieruje niskopewne/kategorię `inne` do człowieka —
  HITL rozszerza to o kolejkę zatwierdzeń, w której człowiek może też zaakceptować/
  edytować odpowiedź wygenerowaną z RAG przed wysłaniem, a nie tylko przejąć całą
  rozmowę. Zaimplementowane przez `interrupt()` + checkpointer w LangGraph — to też
  dodatkowo uzasadnia wcześniejszy wybór LangGraph nad Pydantic AI (wbudowane wsparcie
  dla przerwania grafu i czekania na input człowieka, bez pisania własnego mechanizmu
  kolejkowania od zera).
  **Efekt:** TBD — planowana implementacja w Tygodniu 4 razem z warstwą walidacji.

## Tydzień 2 — 2026-08-19

- **Decyzja:** rozważono i odrzucono podpięcie modeli Claude (Sonnet/Opus) jako
  głównego silnika LLM, zamiast Ollamy — projekt zostaje przy Ollamie.
  **Dlaczego:** subskrypcja Claude (Pro/Max, czat/Claude Code) nie daje dostępu do
  Anthropic API używanego przez LangChain/LangGraph w kodzie — to osobne,
  rozliczane per-token rozliczenie. Podpięcie na stałe złamałoby założenie
  "wszystko za darmo" z planu projektu. Ollama (Llama 3.1 8B) jest wyraźnie słabsza
  jakościowo, ale to świadomy trade-off koszt/lokalność vs jakość — sam w sobie
  dobry materiał na STAR.
  **Efekt:** brak zmian w kodzie/configu. Opcja porównania z API (darmowe/tanie
  kredyty, np. `claude-haiku-4-5`) zostaje odłożona do Tygodnia 5-6 jako
  jednorazowy test jakościowy w README, nie jako stały provider w pipeline.

- **Decyzja:** dwie strategie chunkingu zaimplementowane jako osobne, testowalne
  funkcje (`fixed_size_chunks`, `section_chunks`) w `src/multiagent_poc/rag/chunking.py`,
  każda indeksowana do osobnej kolekcji Chroma (`runbooks_fixed_size`, `runbooks_section`).
  **Dlaczego:** żeby porównanie z README runbooków (pytanie o pomyłkę dostawcy, sekcja
  4.3) dało się zweryfikować kodem, a nie tylko "na oko". `section_chunks` dodatkowo
  dokleja ścieżkę nagłówków (`heading_path`) do treści chunku, żeby fragment osadzony
  w podsekcji (`### 4.3`) nie tracił kontekstu sekcji nadrzędnej (`## 4.`).
  **Efekt:** test strukturalny (`tests/test_chunking.py`, bez potrzeby uruchamiania
  embeddingów) potwierdza, że `section_chunks` daje dokładnie jeden, samodzielny,
  tematycznie czysty chunk dla sekcji 4.3, podczas gdy `fixed_size_chunks` (500
  znaków, overlap 50) nie gwarantuje ani spójności, ani informacji o sekcji źródłowej.
  Pełne porównanie jakości retrievalu (z realnymi embeddingami) czeka na decyzję
  o modelu (Ollama vs. inny) — patrz niżej.

- **Decyzja:** środowisko Python postawione jako "embeddable" dystrybucja
  (`.python/` w repo, gitignored) + ręcznie doinstalowany pip, zamiast standardowego
  instalatora MSI czy `winget`.
  **Dlaczego:** zarówno `winget install Python.Python.3.12`, jak i oficjalny
  installer python.org (nawet w trybie per-user, `/quiet InstallAllUsers=0`)
  zawodziły w tym środowisku — MSI kończył się błędem `0x80070003` (usługa Windows
  Installer nie miała dostępu do plików tymczasowych, prawdopodobnie z powodu
  ograniczeń sandboxa/uprawnień na tej maszynie). Wariant embeddable (ZIP, bez
  instalatora) obszedł problem, bo nie korzysta z usługi MSI.
  **Efekt:** `pytest` (4 testy: chunking + katalog intencji) przechodzi lokalnie.
  Ollama celowo jeszcze nie zainstalowana — decyzja o modelu/wyborze narzędzia
  odłożona na następny krok.

## Szablon na kolejne tygodnie

```
## Tydzień N — YYYY-MM-DD

- **Decyzja:** ...
  **Dlaczego:** ...
  **Efekt:** ...
```
