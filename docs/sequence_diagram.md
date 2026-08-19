# Diagram sekwencji — docelowy proces

Pełny przepływ pytania użytkownika przez wszystkie 7 warstw architektury
(patrz [`architecture.md`](architecture.md)). To jest diagram **docelowy** —
opisuje, jak proces ma działać po ukończeniu Tygodni 3-4, nie stan obecny
(status implementacji per element — patrz [`requirements.md`](requirements.md)).

Renderuje się natywnie w GitHubie (blok ```mermaid).

```mermaid
sequenceDiagram
    actor User as Pracownik/Franczyzobiorca
    participant UI as Streamlit UI
    participant Graph as Graf LangGraph (router)
    participant Val as Walidacja danych wejściowych
    participant Clf as Klasyfikator intencji
    participant Gate as Confidence gate
    participant Agent as Subagent (per kategoria)
    participant RAG as RAG (retrieval)
    participant Chroma as Chroma (vector DB)
    participant LLM as Ollama (LLM)
    participant HITL as Kolejka HITL
    actor Human as Człowiek (operator/kierownik)
    participant LF as Langfuse (observability)

    User->>UI: Zadaje pytanie
    UI->>Graph: invoke(pytanie)
    Graph->>LF: log: trace start

    Graph->>Val: validate(pytanie)
    alt dane wrażliwe / niedozwolona treść (np. PESEL, prompt injection)
        Val-->>Graph: reject(powód)
        Graph->>LF: log: validation_rejected
        Graph-->>UI: Odpowiedź: "nie mogę pomóc z tym pytaniem"
        UI-->>User: Wyświetla odmowę
    else pytanie OK (ew. znormalizowane, np. numer zamówienia)
        Val-->>Graph: ok(pytanie_znormalizowane)

        Graph->>Clf: classify(pytanie)
        Clf-->>Graph: (intencja, confidence)
        Graph->>LF: log: intent + confidence

        Graph->>Gate: check(confidence, intencja)

        alt confidence >= próg AND intencja != "inne"
            Gate-->>Graph: auto-handle
            Graph->>Agent: handle(pytanie, intencja)
            Agent->>RAG: retrieve(pytanie, kolekcja=section)
            RAG->>Chroma: query(embedding)
            Chroma-->>RAG: top-k chunków
            RAG->>LLM: generate(kontekst, pytanie)
            LLM-->>RAG: odpowiedź
            RAG-->>Agent: odpowiedź + źródła
            Agent-->>Graph: odpowiedź
            Graph->>LF: log: rag_answer (chunki, latencja, koszt)
            Graph-->>UI: odpowiedź + źródła (runbook, sekcja)
            UI-->>User: Wyświetla odpowiedź
        else confidence < próg OR intencja == "inne"
            Gate-->>Graph: escalate
            Graph->>HITL: enqueue(pytanie, kontekst_częściowy)
            Graph->>Graph: interrupt() — graf wstrzymany, stan zapisany (checkpointer)
            HITL->>Human: powiadomienie o pytaniu w kolejce
            Human->>HITL: odpowiedź / zatwierdzenie / edycja
            HITL->>Graph: resume(odpowiedź_człowieka)
            Graph->>LF: log: human_escalation (czas oczekiwania, kto odpowiedział)
            Graph-->>UI: odpowiedź (od człowieka)
            UI-->>User: Wyświetla odpowiedź
        end
    end

    Graph->>LF: log: trace end
```

## Uwagi do diagramu

- **Walidacja przed klasyfikacją, nie po** — świadoma decyzja: dane wrażliwe
  (PESEL, próby prompt injection — patrz pytania 16 i 20 w `test_questions.md`)
  mają być odrzucone zanim jakikolwiek fragment pytania trafi do klasyfikatora
  czy LLM-a, żeby nie ryzykować, że trafią do promptu czy logów Langfuse.
- **HITL to nie tylko "przejęcie rozmowy"** — węzeł `interrupt()` w LangGraph
  wstrzymuje graf i zapisuje stan przez checkpointer, więc człowiek może
  odpowiedzieć z opóźnieniem (nie synchronicznie), a graf wznawia się dokładnie
  tam, gdzie stanął. To różni się od prostego "jeśli nisko, to komunikat o
  eskalacji i koniec" — patrz decyzja o HITL w `decision_log.md`.
- **Observability (Langfuse) jest przekrojowe** — na diagramie pokazane jako
  osobne wywołania `log:`, ale docelowo to pojedynczy trace na całą rozmowę
  (nested spans), nie osobne requesty.
- Diagram nie pokazuje pętli powtórnego pytania przy niejednoznacznej
  intencji (dopytanie zamiast eskalacji) — do rozstrzygnięcia w Tygodniu 3
  razem z implementacją confidence gate.
