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

Projekt świadomie doprowadzony do końca łącznie z warstwami, które w projektach
tego typu bywają pierwsze do wycięcia: **walidacją danych wejściowych**,
**human-in-the-loop** i **ewaluacją**. Kontekst biznesowy (sieć convenience,
franczyza) celowo zbliżony do realiów Żabki, ale w całości fikcyjny.

Pełny, surowy log decyzji (co, dlaczego, z jakim skutkiem — po każdym etapie)
jest publiczny w repo: [`docs/decision_log.md`](https://github.com/goreckip/MultiAgentPoC/blob/main/docs/decision_log.md).
Ten dokument to jego skondensowana, czytelna wersja.

## 2. Architektura — 7 warstw

| # | Warstwa | Status |
|---|---|---|
| 1 | Klasyfikacja intencji (9 kategorii: 8 procesowych + `inne`) | ✅ |
| 2 | Confidence gate (próg pewności → auto-odpowiedź vs. eskalacja) | ✅ |
| 3 | RAG nad runbookami (Chroma + Ollama) | ✅ |
| 4 | Dwaj agenci per kategoria (subagent odpowiedzi + drafting agent dokumentów) | ✅ |
| 5 | Walidacja danych wejściowych (dane wrażliwe, format, załącznik PDF + skan AV) | ✅ |
| 6 | Human-in-the-loop (współdzielona kolejka, `interrupt()`/`resume`) | ✅ |
| 7 | Observability (Langfuse Cloud) | ✅ |

Diagram sekwencji pełnego przepływu (renderuje się natywnie na GitHubie):
[`docs/sequence_diagram.md`](https://github.com/goreckip/MultiAgentPoC/blob/main/docs/sequence_diagram.md)

Pełny opis modułów i plików: [`docs/architecture.md`](https://github.com/goreckip/MultiAgentPoC/blob/main/docs/architecture.md)

### Stack i uwaga o wydajności

LangGraph + LangChain, Ollama (`llama3.1:8b`), Chroma, Langfuse Cloud (free
tier), Streamlit.

> **Ważne dla oceny czasów w tym dokumencie:** na potrzeby PoC model działa
> **lokalnie przez Ollamę, na CPU, bez GPU i bez płatnego API**. Skutek: jedno
> wywołanie LLM trwa ~2 minuty, a pełny cykl z dwoma agentami ~4,5 minuty.
> To wyłącznie konsekwencja świadomej decyzji „wszystko lokalne i darmowe" —
> na modelu hostowanym (Claude, GPT) te same kroki wykonują się w kilka sekund.
> Architektura, prompty i graf pozostają bez zmian; zmienia się wyłącznie
> dostawca modelu w `config.py`. Wszystkie pozostałe kroki (walidacja,
> klasyfikacja, routing, gate) są rzędu milisekund–sekund i nie zależą od LLM-a.

### Dwaj agenci, nie jeden

Każda z 7 kategorii procesowych (bez `higiena` — to kategoria checklist, nie
korespondencji) ma **dwóch** agentów o różnych rolach:

1. **Subagent odpowiedzi** ([`agents/subagent.py`](https://github.com/goreckip/MultiAgentPoC/blob/main/src/multiagent_poc/agents/subagent.py)) —
   odpowiada na pytanie proceduralne, retrieval przefiltrowany do właściwego runbooka.
2. **Drafting agent** ([`agents/drafting_agent.py`](https://github.com/goreckip/MultiAgentPoC/blob/main/src/multiagent_poc/agents/drafting_agent.py)) —
   generuje gotowy dokument (zgłoszenie, karta zdarzenia, pismo), reużywając
   kontekstu RAG już pobranego przez subagenta. Brakujące dane → jawny
   placeholder `[uzupełnij: ...]`, nigdy zgadywanie. Kategorie wrażliwe (BHP,
   HR) — dokument zawsze przechodzi przez kolejkę HITL, zanim trafi do pracownika.

## 3. Walkthrough na żywo — obsługa braku w dostawie

Poniżej dwa **rzeczywiste** przebiegi z jednego uruchomienia, oba z domeny
zamówień/dostaw. Wszystkie cytowane treści, czasy i liczby tokenów pochodzą z
faktycznego wykonania i z trace'ów pobranych z Langfuse API — nic nie jest
ilustracyjne.

Scenariusze dobrane celowo: **pytania są niemal identyczne merytorycznie**
(brakuje palet, kierowca odjechał), ale system potraktował je zupełnie inaczej —
co pokazuje, jak działa confidence gate i gdzie leży realna słabość klasyfikatora.

---

### Scenariusz A — wysoka pewność, pełna obsługa automatyczna

**Pytanie pracownika:**
> Przy odbiorze towaru brakuje dwóch palet względem WZ, kierowca już odjechał,
> dostawa była dziś rano od Centralnego Dostawcy, co mam zrobić?

**Krok 1 — walidacja** (`validate_input`, **0.000s**)
Sprawdzenie pod kątem PESEL (suma kontrolna), prompt injection, próśb o dane
osób trzecich, formatu numeru zamówienia. Czysto → dalej. Gdyby pytanie
zawierało dane wrażliwe, zostałoby odrzucone *zanim* dotarłoby do
klasyfikatora czy jakiegokolwiek LLM-a.

**Krok 2 — klasyfikacja intencji** (`classify_intent`, **3.070s**)
k-NN (k=3) nad embeddingami przykładowych fraz w Chroma.
Wynik: **`dostawy`, confidence 0.67** (głosy: `dostawy` 2, `bhp` 1).

**Krok 3 — confidence gate** (`confidence_gate`, **0.000s**)
0.67 ≥ próg 0.6 → **auto-obsługa**, routing do subagenta `dostawy`. Bez eskalacji.

**Krok 4 — subagent odpowiada** (`subagent_answer`, **154.3s**; LLM: 150.2s, 713 in / 168 out tokenów)
RAG przefiltrowany wyłącznie do `01_dostawy.md` (`sources=['01_dostawy.md']` —
nigdy inny runbook, dzięki filtrowi metadanych w Chroma):

> Zgodnie z procedurą opisaną w rozdziale 4.1 Brak towaru (niedostarczona
> pozycja), musisz:
> 1. Odnotować brak towaru na WZ (…) z podpisem kierowcy.
> 2. Zgłosić brak towaru przez system w ciągu 24 godzin.
> 3. Nie koryguje się stanów magazynowych ręcznie, ponieważ system generuje
>    korektę automatycznie po zatwierdzeniu zgłoszenia przez dział zaopatrzenia.

Model trafnie wybrał **sekcję 4.1** (brak towaru), a nie 4.3 (pomyłka
dostawcy) — istotne rozróżnienie, bo obie sekcje dotyczą rozbieżności przy
odbiorze, ale mają inne procedury.

**Krok 5 — drafting agent tworzy dokument** (`draft_document`, **116.6s**; LLM: 115.8s, 834 in / 94 out tokenów)
`dostawy` ma `requires_human_review=False`, więc dokument trafia do pracownika
od razu, bez kolejki:

```
Numer zamówienia lub dostawy: [uzupełnij: numer_zamowienia_lub_dostawy]
Dostawca: Centralny Dostawca
Opis rozbieżności: Brakuje dwóch palet w porównaniu do (…) WZ (…)
Data dostawy: dzisiaj rano
```

Agent poprawnie wyciągnął z pytania **dostawcę** i **datę**, a brakujący numer
zamówienia **jawnie oznaczył placeholderem zamiast go wymyślić** — to
zaprojektowane zachowanie: dokument z halucynowanym numerem jest gorszy niż
dokument z widocznym brakiem.

**Łącznie: 273.9s** (z czego 266s to dwa wywołania LLM na CPU — patrz uwaga o
wydajności wyżej; reszta pipeline'u to 3 sekundy).

#### Uczciwie: co model zrobił źle w tym przebiegu

Dwukrotnie **rozwinął skrót „WZ" — i za każdym razem błędnie** („Wywiad
Zamówienia" w odpowiedzi, „Widok Zamówienia" w dokumencie). Runbook używa
skrótu WZ bez rozwinięcia, więc model go zmyślił zamiast zostawić w oryginale.
Merytorycznie procedura jest poprawna, ale w piśmie idącym do dostawcy taki
błąd rzuca się w oczy. To dokładnie rodzaj usterki, który wyłapuje dopiero
przegląd na żywo — nie testy jednostkowe i nie LLM-as-judge.

---

### Scenariusz B — niska pewność, eskalacja do człowieka

**Pytanie pracownika** (to samo zdarzenie, inaczej sformułowane):
> Brakuje palet w dostawie, kierowca odjechał. Zamówienie ZM-2024-00981.

**Krok 1-2 — walidacja i klasyfikacja** (**2.939s** łącznie)
Walidacja czysta. Klasyfikator: **confidence 0.33** — głosy rozproszone, brak
większości.

**Krok 3 — confidence gate → STOP**
0.33 < próg 0.6 → efektywna intencja `inne`, **eskalacja**. Kluczowe: żaden LLM
nie został wywołany, żaden dokument nie powstał. System **nie zgadywał** —
cały przebieg zajął niecałe 3 sekundy.

**Krok 4 — pauza grafu** (`interrupt()`)
Graf wstrzymuje się z zachowanym stanem. Payload:
```json
{ "kind": "escalation",
  "question": "Brakuje palet w dostawie, kierowca odjechał. Zamówienie ZM-2024-00981.",
  "reason": "confidence=0.33 < próg" }
```
Pytanie trafia do **współdzielonej kolejki HITL** — widocznej dla operatora
niezależnie od tego, w której sesji/przeglądarce zostało zadane (zweryfikowane
w dwóch niezależnych kartach przeglądarki).

**Krok 5 — operator odpowiada, graf wznawia się** (`Command(resume=...)`, **0.006s**)
Operator wpisuje odpowiedź w panelu HITL; graf wznawia się natychmiast i
dostarcza ją pracownikowi jako finalną odpowiedź.

---

### Czego uczy zestawienie A i B

Dwa pytania o to samo zdarzenie biznesowe, dwie różne ścieżki. To **nie jest
przypadek** — to zaprojektowane zachowanie confidence gate'u, ale też
odsłonięta słabość klasyfikatora: dodanie numeru zamówienia (`ZM-2024-00981`)
do treści realnie pogarsza klasyfikację, przeciągając ją w stronę `płatności`.
Znane, udokumentowane ograniczenie (65% top-1 accuracy — sekcja 4), a nie
niespodzianka.

**Z perspektywy produktowej to zachowanie pożądane:** system, który przy
niepewności eskaluje w 3 sekundy, jest lepszy niż system, który po 4 minutach
wygeneruje pewnie brzmiący, ale potencjalnie błędny dokument.

### Realny trace z Langfuse — scenariusz A

```
handle_user_turn                    273.910s
├─ handle_question                    3.073s
│   ├─ validate_input                 0.000s
│   ├─ classify_intent                3.070s
│   └─ confidence_gate                0.000s
├─ subagent_answer                  154.250s
│   └─ GENERATION ChatOllama         150.229s   713 in / 168 out tok
└─ draft_document                   116.559s
    └─ GENERATION ChatOllama         115.825s   834 in / 94 out tok
```

Każde pytanie generuje taki zagnieżdżony trace — z modelem, liczbą tokenów i
latencją **każdego kroku z osobna**, nie tylko całości. `total_cost` wychodzi
`None`, bo model lokalny przez Ollamę nie ma wpisu w cenniku Langfuse; tokeny
i latencja i tak dają pełną obserwowalność.

## 4. Ewaluacja — nie tylko „działa", ale „jak dobrze"

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
  podpięcie płatnego API na stałe złamałoby założenie „wszystko za darmo".
  Świadomy trade-off jakość i szybkość vs koszt/lokalność — z pełną
  świadomością, że w produkcji wybór byłby odwrotny.
- **Walidacja przed klasyfikacją, nie po** — dane wrażliwe nigdy nie trafiają
  nawet do klasyfikatora, nie tylko do LLM-a.
- **Malware scan lokalny (ClamAV), nie chmurowy** — plik nigdy nie opuszcza
  maszyny, zgodnie z założeniem lokalności.
- **Brakujące pole → placeholder, nie zgadywanie** — dokument z halucynowaną
  datą czy numerem jest gorszy niż dokument z widocznym brakiem.

## 6. Znane ograniczenia (uczciwie, nie ukryte)

- Klasyfikator ma 65% top-1 accuracy — widać to wprost w scenariuszu B wyżej,
  a także w złapanym na żywo przypadku pytania o sanepid błędnie
  sklasyfikowanego jako `hr`.
- Model potrafi zmyślić rozwinięcie skrótu (WZ → „Wywiad Zamówienia") albo rok
  w dacie — złapane na żywo w tym i poprzednim przebiegu, opisane, nie ukryte.
- LLM-as-judge to ten sam model co generuje odpowiedzi — słaby, czasem
  niespójny sędzia (złapany przypadek: ocena 1/5 dla odpowiedzi, która
  faktycznie była zgodna z procedurą).
- Czasy odpowiedzi (~4,5 min na pełny cykl) wynikają wyłącznie z lokalnej
  Ollamy na CPU — patrz uwaga w sekcji 2.
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
