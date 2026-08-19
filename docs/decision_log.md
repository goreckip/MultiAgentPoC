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

## Szablon na kolejne tygodnie

```
## Tydzień N — YYYY-MM-DD

- **Decyzja:** ...
  **Dlaczego:** ...
  **Efekt:** ...
```
