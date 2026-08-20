# Diagram sekwencji — docelowy proces

Pełny przepływ pytania użytkownika przez wszystkie 7 warstw architektury
(patrz [`architecture.md`](architecture.md)). To jest diagram **docelowy** —
opisuje, jak proces ma działać po ukończeniu Sprintów 3-4, nie stan obecny
(status implementacji per element — patrz [`requirements.md`](requirements.md)).

> Odwzorowanie **faktycznej** topologii grafu wykonawczego (węzły i krawędzie
> 1:1 z `pipeline_graph.py`) to osobny dokument:
> [`graph_diagram.md`](graph_diagram.md).

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
    participant AV as Skan antywirusowy
    participant Doc as Parser załącznika (PDF)
    participant HITL as Kolejka HITL
    actor Human as Człowiek (operator/kierownik)
    participant LF as Langfuse (observability)

    User->>UI: Zadaje pytanie (opcjonalnie: załącza PDF, np. zamówienie)
    UI->>Graph: invoke(pytanie, załącznik?)

    opt załącznik obecny
        Graph->>AV: scan(załącznik)
        alt wykryto malware / plik podejrzany
            AV-->>Graph: reject
            Graph->>LF: log: attachment_rejected
            Graph-->>UI: Odpowiedź: "załącznik odrzucony"
            UI-->>User: Wyświetla odmowę
        else plik czysty
            AV-->>Graph: ok
        end
    end
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
            Gate-->>Graph: escalate (wstępnie)

            opt załącznik obecny i przeszedł skan
                Graph->>Doc: parse(załącznik) — tylko warstwa tekstowa PDF, bez OCR
                Doc-->>Graph: tekst_dokumentu
                Graph->>Clf: classify(pytanie + tekst_dokumentu)
                Clf-->>Graph: (intencja', confidence')
                Graph->>Gate: check(confidence', intencja')
            end

            alt confidence (po ew. doczytaniu załącznika) >= próg
                Gate-->>Graph: auto-handle
                Note over Graph,Agent: dalej jak w gałęzi "auto-handle" powyżej
            else nadal poniżej progu
                Gate-->>Graph: escalate
                Graph->>HITL: enqueue(pytanie, kontekst_częściowy, załącznik?)
                Graph->>Graph: interrupt() — graf wstrzymany, stan zapisany (checkpointer)
                HITL->>Human: powiadomienie o pytaniu w kolejce
                Human->>HITL: odpowiedź / zatwierdzenie / edycja
                HITL->>Graph: resume(odpowiedź_człowieka)
                Graph->>LF: log: human_escalation (czas oczekiwania, kto odpowiedział)
                Graph-->>UI: odpowiedź (od człowieka)
                UI-->>User: Wyświetla odpowiedź
            end
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
  intencji (dopytanie zamiast eskalacji) — do rozstrzygnięcia w Sprincie 3
  razem z implementacją confidence gate.
- **Skan antywirusowy jest blokujący i bezwarunkowy** — żaden załącznik nie
  trafia do parsera PDF, klasyfikatora ani logów Langfuse przed pozytywnym
  wynikiem skanu. To rozszerzenie dodane po podstawowym planie — patrz
  `decision_log.md` ("Rozszerzenie planu") i punkty 5.5-5.8 w
  `requirements.md`. Docelowy agent "data retrieval" (wykorzystujący treść
  załącznika bezpośrednio w odpowiedzi, nie tylko do reklasyfikacji) to
  świadomy follow-up, nieujęty jeszcze na tym diagramie.
