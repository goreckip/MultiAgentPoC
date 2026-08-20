# Case study: Multi-Agent Retail Ops Assistant

**Projekt portfolio pod rozmowy AI Product Manager — niezależny, niezwiązany z i
nieautoryzowany przez Żabka Polska sp. z o.o.**
Repo: [github.com/goreckip/MultiAgentPoC](https://github.com/goreckip/MultiAgentPoC)

---

## 1. Kontekst i cel

Asystent operacyjny dla sklepów sieci convenience — franczyzobiorcy/pracownicy
zadają pytania proceduralne (dostawy, reklamacje, płatności, BHP, HR, higiena,
awarie techniczne, skargi klienta). System klasyfikuje intencję, sprawdza
pewność klasyfikacji, i albo odpowiada na bazie wewnętrznych runbooków (RAG),
albo eskaluje do człowieka — nigdy nie zgaduje.

Projekt modelowany na projekcie Procurement, który realizowałem w PwC, ale
celowo doprowadzony do końca łącznie z warstwą **walidacji danych
wejściowych** i **human-in-the-loop**, których tamtemu projektowi zabrakło z
powodu cięć budżetowych. Kontekst biznesowy (sieć convenience, franczyza)
świadomie zbliżony do realiów Żabki.

Pełny, surowy log decyzji (co, dlaczego, z jakim skutkiem — po każdym etapie)
jest publiczny w repo: [`docs/decision_log.md`](https://github.com/goreckip/MultiAgentPoC/blob/main/docs/decision_log.md).
Ten dokument to jego skondensowana, czytelna wersja.

## 2. Architektura — 7 warstw

| # | Warstwa | Status |
|---|---|---|
| 1 | Klasyfikacja intencji (9 kategorii: 8 procesowych + `inne`) | ✅ |
| 2 | Confidence gate (próg pewności → auto-odpowiedź vs. eskalacja) | ✅ |
| 3 | RAG nad runbookami (Chroma + Ollama) | ✅ |
| 4 | Dwa agenty per kategoria (subagent odpowiedzi + drafting agent dokumentów) | ✅ |
| 5 | Walidacja danych wejściowych (dane wrażliwe, format, załącznik PDF + skan AV) | ✅ |
| 6 | Human-in-the-loop (współdzielona kolejka, `interrupt()`/`resume`) | ✅ |
| 7 | Observability (Langfuse Cloud) | ✅ |

Diagram sekwencji pełnego przepływu (renderuje się natywnie na GitHubie):
[`docs/sequence_diagram.md`](https://github.com/goreckip/MultiAgentPoC/blob/main/docs/sequence_diagram.md)

Pełny opis modułów i plików: [`docs/architecture.md`](https://github.com/goreckip/MultiAgentPoC/blob/main/docs/architecture.md)

### Stack

LangGraph + LangChain, Ollama (`llama3.1:8b` lokalnie, CPU-only), Chroma,
Langfuse Cloud (free tier), Streamlit. Wszystko darmowe/lokalne poza
observability.

### Dwa agenty, nie jeden

Każda z 7 kategorii procesowych (bez `higiena` — to kategoria checklist, nie
korespondencji) ma **dwóch** agentów:

1. **Subagent** ([`agents/subagent.py`](https://github.com/goreckip/MultiAgentPoC/blob/main/src/multiagent_poc/agents/subagent.py)) —
   odpowiada na pytanie proceduralne, retrieval przefiltrowany do właściwego runbooka.
2. **Drafting agent** ([`agents/drafting_agent.py`](https://github.com/goreckip/MultiAgentPoC/blob/main/src/multiagent_poc/agents/drafting_agent.py)) —
   generuje gotowy dokument (zgłoszenie, karta zdarzenia, pismo), reużywając
   kontekstu RAG już pobranego przez subagenta. Brakujące dane → jawny
   placeholder `[uzupełnij: ...]`, nigdy zgadywanie. Kategorie wrażliwe (BHP,
   HR) — dokument zawsze przechodzi przez tę samą kolejkę HITL co eskalacje,
   zanim trafi do pracownika.

## 3. Walkthrough na żywo — pytanie BHP

Poniżej dokładny, rzeczywisty przebieg jednego zapytania w uruchomionej
aplikacji (Streamlit), z komentarzem co dzieje się pod spodem na każdym
kroku. Wszystkie cytowane treści i liczby pochodzą z faktycznego uruchomienia
(łącznie z realnym trace'em pobranym z Langfuse API), nie są ilustracyjne.

**Pytanie pracownika:**
> Pracownik poparzył się podczas czyszczenia grilla, co robimy? Zdarzenie
> miało miejsce dzisiaj o 14:30, świadkiem był kolega z zmiany Marek.

**Krok 1 — walidacja (`validate_input`, <1ms).** Pytanie sprawdzane pod kątem
PESEL (suma kontrolna), prompt injection, próśb o dane osób trzecich. Brak
naruszeń → przechodzi dalej. Gdyby zawierało dane wrażliwe, zostałoby
odrzucone *zanim* dotarłoby do klasyfikatora czy LLM-a.

**Krok 2 — klasyfikacja intencji (`classify_intent`, 3.9s).** k-NN (k=3) nad
embeddingami przykładowych fraz w Chroma. Wynik: intencja `bhp`, wysoka
pewność (spójne z wcześniejszą ewaluacją klasyfikatora — patrz sekcja 4).

**Krok 3 — confidence gate.** Pewność powyżej progu → routing do subagenta
`bhp`, bez eskalacji.

**Krok 4 — subagent odpowiada (134s, 876 tokenów wejścia / 86 wyjścia).**
RAG przefiltrowany do `04_bhp.md` generuje odpowiedź:

> Należy udzielić pierwszej pomocy pracownikowi, który poparzył się.
> Następnie należy wezwać pomoc medyczną jeśli konieczne. Ponadto należy
> zabezpieczyć miejsce zdarzenia i wypełnić kartę zdarzenia BHP w systemie w
> tym samym dniu roboczym.

**Krok 5 — drafting agent (143s, 990 tokenów wejścia / 121 wyjścia).**
Ponieważ `bhp` ma zdefiniowany szablon dokumentu (`requires_human_review=True`),
agent generuje szkic "Karty zdarzenia BHP", reużywając tych samych chunków co
subagent:

```
Data godzina zdarzenia: 14:30
Opis zdarzenia: Pracownik poparzył się podczas czyszczenia grilla. [Uzupełnij: opis_zdarzenia]
Udzielona pomoc: Zastąpiono pracownika, zapewniono mu pierwszą pomoc i wezwanie pogotowia medycznego. [Uzupełnij: udzielona_pomoc]
Świadkowie: Marek, kolega z zmiany.
```

Model poprawnie wyciągnął godzinę (14:30) i świadka (Marek) z treści pytania.
**Zaobserwowana niedoskonałość, nieukrywana:** dla dwóch pól model wypełnił
treść *i* mimo to dopisał obok placeholder — niespójność instruction-following,
odnotowana w `decision_log.md` jako znane ograniczenie do poprawy promptu.

**Krok 6 — pauza grafu.** Ponieważ dokument wymaga recenzji, graf LangGraph
wstrzymuje się przez `interrupt()` (nie kończy się błędem — to zaprojektowana
pauza z zapisanym stanem). Payload: `{"kind": "document_review", "document_type": "Karta zdarzenia BHP", ...}`.
Pracownik widzi: *"Twoje pytanie czeka na operatora"*. Dokument trafia do
**współdzielonej kolejki HITL** — widoczny dla operatora niezależnie od tego,
w której sesji/przeglądarce został zgłoszony (zweryfikowane wcześniej w
dwóch niezależnych kartach przeglądarki).

**Krok 7 — operator zatwierdza.** W panelu HITL operator widzi pytanie, powód
("dokument do zatwierdzenia: Karta zdarzenia BHP") i edytowalną treść. Klika
"Zatwierdź dokument" → graf wznawia się przez `Command(resume=...)`.
Wznowienie jest natychmiastowe (0.016s) — operator dostarczył gotowy tekst,
więc nie ma potrzeby ponownego wywołania LLM-a.

**Krok 8 — pracownik dostaje odpowiedź.** Po kliknięciu "Sprawdź, czy jest
odpowiedź" pracownik widzi **oba** elementy razem: proceduralną odpowiedź
subagenta *i* zatwierdzony przez operatora dokument — mimo że dokument
przeszedł przez pauzę/wznowienie grafu, a odpowiedź nie.

### Co pokazuje realny trace z Langfuse (pobrany przez API tej samej interakcji)

```
handle_user_turn (285.6s total)
├─ validate_input                 <1ms
├─ classify_intent                3.9s
├─ confidence_gate                <1ms
├─ subagent_answer                138.0s
│   └─ GENERATION ChatOllama      134.0s  876 in / 86 out tokens
└─ draft_document                 143.7s
    └─ GENERATION ChatOllama      143.0s  990 in / 121 out tokens
```

Każde pytanie w systemie generuje dokładnie taki zagnieżdżony trace —
widoczny w Langfuse Cloud z modelem, liczbą tokenów i latencją każdego kroku,
nie tylko całości. `total_cost` wychodzi `None` — oczekiwane, model lokalny
przez Ollama nie ma wpisu w cenniku Langfuse, ale tokeny/latencja i tak dają
realną obserwowalność.

**Uczciwa uwaga o wydajności:** ~285s na pełny cykl (dwa wywołania LLM
sekwencyjnie) to realna latencja CPU-only inference na tej maszynie. GPU albo
mniejszy model skróciłyby to znacząco — świadomy trade-off "wszystko lokalne
i darmowe" z reszty projektu.

## 4. Ewaluacja — nie tylko "działa", ale "jak dobrze"

### Klasyfikator intencji (`scripts/evaluate_classifier.py`, 20 pytań)

- **65% trafności top-1**, ale **100% (5/5) na pytaniach bezpieczeństwa**
  (dane wrażliwe, prompt injection, pytania spoza katalogu — zawsze poprawnie
  eskalowane). Confidence gate świadomie eskaluje przy niepewności zamiast
  zgadywać — bezpieczeństwo ponad automatyzację.

### RAG — retrieval + jakość odpowiedzi (`scripts/evaluate_rag.py`, 15 pytań)

Trzy niezależne sygnały, celowo nie jeden:

| Sygnał | Wynik | Co łapie |
|---|---|---|
| Retrieval hit-rate | 86% (12/14) | czy RAG w ogóle sięgnął po właściwą sekcję |
| Pokrycie słów kluczowych | 38% | tani, deterministyczny, ale sztywny wobec parafraz |
| LLM-as-judge (1-5) | 4.67/5 | łapie parafrazy, ale to ten sam model co generuje odpowiedzi |

**Najsilniejsze odkrycie tej ewaluacji:** dla jednego pytania retrieval pobrał
złą sekcję runbooka (nadgodziny zamiast zamiany grafiku), a mimo to model
odpowiedział przekonującym, proceduralnym tonem — LLM-judge ocenił to na 5/5,
nie zauważając błędu. Tylko sygnał keyword-matching to wyłapał (0%). Żaden
pojedynczy sygnał osobno by tego nie ujawnił — dopiero zestawienie ich
obnażyło lukę. Pełny opis: [`docs/decision_log.md`, Sprint 6](https://github.com/goreckip/MultiAgentPoC/blob/main/docs/decision_log.md).

## 5. Wybrane decyzje projektowe (materiał STAR)

- **Section-based chunking zamiast fixed-size** — realny eksperyment na
  Chroma pokazał, że fixed-size (500 znaków) zwracał chunk zaczynający się od
  uciętego słowa, bez informacji o sekcji źródłowej; section-based dawał
  samodzielny, czytelny fragment. Decyzja podjęta na podstawie danych, nie
  intuicji.
- **Ollama zamiast Claude/GPT jako silnik LLM** — rozważone i odrzucone:
  subskrypcja Claude nie daje dostępu do API używanego przez LangChain, a
  podpięcie płatnego API na stałe złamałoby założenie "wszystko za darmo".
  Świadomy trade-off jakość vs koszt/lokalność.
- **Walidacja przed klasyfikacją, nie po** — dane wrażliwe nigdy nie trafiają
  nawet do klasyfikatora, nie tylko do LLM-a.
- **Malware scan lokalny (ClamAV), nie chmurowy** — plik nigdy nie opuszcza
  maszyny, zgodnie z założeniem lokalności.
- **Kolejka HITL: brakujące pole → placeholder, nie zgadywanie** — dokument z
  halucynowaną datą jest gorszy niż dokument z widocznym brakiem.

## 6. Znane ograniczenia (uczciwie, nie ukryte)

- Klasyfikator ma 65% top-1 accuracy — realny przypadek błędnej klasyfikacji
  (pytanie o sanepid → `hr` zamiast eskalacji) został złapany na żywo w demo
  grafu i opisany, nie ukryty.
- LLM-as-judge to ten sam model co generuje odpowiedzi — słaby, czasem
  niespójny sędzia (złapany przypadek: ocena 1/5 dla odpowiedzi, która
  faktycznie była zgodna z procedurą).
- Model czasem duplikuje pole (wypełnia je i mimo to dodaje placeholder) —
  niespójność instruction-following w drafting agencie.
- Kolejka HITL i checkpointer grafu żyją w pamięci procesu — nie przetrwają
  restartu serwera (świadome uproszczenie PoC, w produkcji: Redis/Postgres).

## 7. Uruchomienie

Pełne instrukcje setup (Python, Ollama, ClamAV, Langfuse) w
[`README.md`](https://github.com/goreckip/MultiAgentPoC/blob/main/README.md).
Status każdego wymagania z pierwotnego planu, ze znacznikami ✅/🚧/⬜/❌:
[`docs/requirements.md`](https://github.com/goreckip/MultiAgentPoC/blob/main/docs/requirements.md).

---

*Ten dokument i cały projekt to niezależna praca portfolio, niezwiązana z i
nieautoryzowana przez Żabka Polska sp. z o.o. Kontekst biznesowy jest
fikcyjny/mockowy — żadne dane, procedury ani znaki towarowe Żabki nie zostały
użyte.*
