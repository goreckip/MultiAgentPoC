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

Obaj agenci widzą też **treść załącznika**, jeśli pracownik go dołączył — dzięki
czemu dokument potrafi wypełnić numer zamówienia z PDF-a zamiast wstawić
placeholder (scenariusz C niżej).

## 3. Walkthrough na żywo — obsługa braku w dostawie

Poniżej trzy **rzeczywiste** przebiegi, wszystkie z domeny zamówień/dostaw.
Wszystkie cytowane treści, czasy i liczby tokenów pochodzą z faktycznego
wykonania i z trace'ów pobranych z Langfuse API — nic nie jest ilustracyjne.

Scenariusze dobrane celowo — **A i B są niemal identyczne merytorycznie**
(brakuje palet, kierowca odjechał), a mimo to system potraktował je zupełnie
inaczej, co pokazuje działanie confidence gate'u i realną słabość
klasyfikatora. **C** to znów to samo pytanie, tym razem z załączonym PDF —
pokazuje, jak dane z dokumentu trafiają do generowanego zgłoszenia.

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

**Krok 4 — subagent odpowiada** (`subagent_answer`, ~150s na CPU)
RAG przefiltrowany wyłącznie do `01_dostawy.md` (`sources=['01_dostawy.md']` —
nigdy inny runbook, dzięki filtrowi metadanych w Chroma):

> Zgodnie z opisem procedury w sekcji 4.3 Pomyłka dostawcy
> `[01_dostawy.md | 4. Rozbieżności ilościowe i jakościowe > 4.3]`:
> * Towar odesłać z tym samym kierowcą, jeśli to możliwe.
> * Jeśli kierowca już odjechał, produkt magazynować oddzielnie do czasu
>   instrukcji z regionu — maksymalnie 5 dni roboczych.
>
> Krok 2: (…) zrób notatkę na WZ z podpisem kierowcy potwierdzającą
> niepełność dostawy.
> Krok 3: W ciągu 24 godzin zgłoś problem przez system wewnętrzny,
> kategoria „Dostawy".

Odpowiedź jest ugruntowana we właściwym runbooku i cytuje konkretną sekcję ze
ścieżką nagłówków. Skrót **WZ zostaje skrótem** — pilnuje tego reguła w system
prompcie, a ostatecznie gwarantuje **deterministyczny strażnik w kodzie**
(patrz „Znane ograniczenia" — to najciekawsza porażka w tym projekcie).

**Krok 5 — drafting agent tworzy dokument** (`draft_document`, ~116s na CPU)
`dostawy` ma `requires_human_review=False`, więc dokument trafia do pracownika
od razu, bez kolejki:

```
Numer zamówienia lub dostawy: [uzupełnij: numer_zamowienia_lub_dostawy]
Dostawca: Centralny Dostawca
Opis rozbieżności: Brakuje dwóch palet względem WZ
Data dostawy: dzisiaj rano
```

Agent wyciągnął z pytania **dostawcę** i **datę**, a numeru zamówienia — którego
w pytaniu nie było — **nie wymyślił, tylko jawnie oznaczył placeholderem**.
To zaprojektowane zachowanie: dokument z halucynowanym numerem jest gorszy niż
dokument z widocznym brakiem. Jak ten sam dokument wygląda, gdy numer *jest*
dostępny w załączniku — patrz scenariusz C.

**Łącznie ~274s** (z czego ~266s to dwa wywołania LLM na CPU — patrz uwaga o
wydajności wyżej; reszta pipeline'u to 3 sekundy).

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

### Scenariusz C — to samo pytanie, ale z załączonym PDF zamówienia

Dokładnie ta sama treść pytania co w scenariuszu A, tym razem z załączonym
plikiem PDF (mockowy wydruk zamówienia):

```
Zamowienie nr ZM-2024-00981 / Dostawca: Centralny Dostawca Sp. z o.o. /
Data dostawy: 2026-08-20 / Pozycje: 12 palet
```

**Krok 1 — skan antywirusowy** (blokujący, bezwarunkowy)
Zanim cokolwiek przeczyta zawartość pliku, załącznik przechodzi przez lokalny
**ClamAV**. Plik nie opuszcza maszyny. Odrzucenie na tym etapie przerywa całe
zapytanie — parser PDF, klasyfikator ani LLM nigdy go nie zobaczą.

**Krok 2 — ekstrakcja treści** (pypdf, tylko warstwa tekstowa, bez OCR)
Wyciągnięty tekst jest niesiony dalej w `PipelineResult.attachment_text` i
trafia do **obu agentów** jako osobno oznaczony blok — opisany w prompcie jako
„dane konkretnej sprawy, nie procedura", żeby model nie pomylił dokumentu
pracownika ze źródłem procedur.

**Krok 3 — dokument wypełniony danymi z załącznika**

```
Numer zamówienia lub dostawy: ZM-2024-00981
Dostawca: Centralny Dostawca Sp. z o.o.
Opis rozbieżności: brakuje dwóch palet względem WZ
Data dostawy: 2026-08-20
```

**Kontrast z tym samym pytaniem bez załącznika (scenariusz A):**

| Pole | Bez załącznika | Z załącznikiem PDF |
|---|---|---|
| Numer zamówienia | `[uzupełnij: …]` | **ZM-2024-00981** |
| Dostawca | Centralny Dostawca | Centralny Dostawca **Sp. z o.o.** |
| Data dostawy | „dzisiaj rano" | **2026-08-20** |

Załącznik pełni więc **dwie różne role**: przełamuje remis, gdy klasyfikacja ma
zbyt niską pewność, **oraz** dostarcza dane do dokumentu. Wcześniej PDF był
parsowany wyłącznie w pierwszym przypadku — teraz, jeśli pracownik zadał sobie
trud dołączenia dokumentu, obaj agenci potrafią go przeczytać.

> **Uwaga na mylącą flagę:** w tym przebiegu `used_attachment=False`, mimo że
> dokument ewidentnie korzysta z załącznika. Ta flaga śledzi wyłącznie
> **reklasyfikację** — a tu klasyfikacja od razu była pewna (0.67), więc drugie
> przejście nie było potrzebne. Nazwa jest myląca i to znany dług.

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

**Scenariusz A — bez załącznika:**
```
handle_user_turn                    329.400s
├─ handle_question                    3.116s
│   ├─ validate_input                 0.001s
│   ├─ classify_intent                3.113s
│   └─ confidence_gate                0.000s
├─ subagent_answer                  217.585s
│   └─ GENERATION ChatOllama         213.680s    965 in / 286 out tok
└─ draft_document                   108.684s
    └─ GENERATION ChatOllama         107.852s   1136 in / 88 out tok
```

**Scenariusz C — z załącznikiem PDF** (widoczny krok skanu antywirusowego):
```
handle_user_turn                    136.013s
├─ handle_question                   20.200s
│   ├─ validate_input                 0.002s
│   ├─ attachment_malware_scan       16.481s   ← ClamAV, blokujący
│   ├─ classify_intent                3.705s
│   └─ confidence_gate                0.000s
├─ subagent_answer                   64.449s
│   └─ GENERATION ChatOllama          60.752s   1040 in / 109 out tok
└─ draft_document                    51.355s
    └─ GENERATION ChatOllama          50.635s   1226 in / 79 out tok
```

Każde pytanie generuje taki zagnieżdżony trace — z modelem, liczbą tokenów i
latencją **każdego kroku z osobna**, nie tylko całości. `total_cost` wychodzi
`None`, bo model lokalny przez Ollamę nie ma wpisu w cenniku Langfuse; tokeny
i latencja i tak dają pełną obserwowalność.

Dwie rzeczy dobrze widać w tym zestawieniu: **skan antywirusowy jest realnym,
mierzalnym krokiem** (16.5s — `clamscan` przeładowuje ~113 MB sygnatur przy
każdym wywołaniu), a **rozrzut czasów LLM jest ogromny** (213s vs 61s za tę
samą pracę) — typowe dla inferencji CPU-only, zależne od stanu cache modelu.

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

### Testy automatyczne

**62 szybkie testy** (mockowany LLM, ~2,5 min) + **4 wolne end-to-end**
(`pytest -m slow`, realna Ollama, ~4 min), w tym:

- **własność dla pytań dwuznacznych** — dla pytań z dwiema dopuszczalnymi
  intencjami nie ma jednej poprawnej odpowiedzi, więc mierzenie top-1 accuracy
  mierzyłoby złą rzecz. Testowana jest zamiast tego własność bezpieczeństwa:
  wolno eskalować, wolno wybrać dowolną z dopuszczalnych intencji, **nie wolno
  pewnie trafić w obcy runbook**;
- **realne pytanie przez cały graf** — bez mocków, z asercjami na ugruntowanie
  odpowiedzi we właściwym runbooku i na brak zmyślonych rozwinięć skrótów;
- **treść załącznika dociera do obu agentów** — asercja, że tekst z PDF trafia
  i do subagenta odpowiedzi, i do drafting agenta.

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
- **Zaciąganie danych z załącznika bez trzeciego agenta** — pierwotny plan
  zakładał osobnego „agenta data retrieval". Przy implementacji okazało się, że
  byłby pustym opakowaniem: treść załącznika to **dodatkowy kontekst** dla
  agentów, którzy już istnieją, a nie zadanie wymagające własnego rozumowania.
  Trzeci agent oznaczałby trzecie wywołanie modelu (+2 min na CPU) bez zysku
  jakościowego. Odrzucenie własnego wcześniejszego pomysłu okazało się tańsze
  niż jego dowiezienie.
- **Deterministyczny strażnik zamiast kolejnej iteracji promptu** — po trzech
  nieudanych rundach pracy nad promptem (model za każdym razem wracał z nowym
  zmyślonym rozwinięciem skrótu) uznałem, że to nie jest problem promptowy.
  Rozwiązaniem jest kod, który sprawdza wynik, a nie kolejne zaklinanie modelu.
  Szczegóły — patrz „Znane ograniczenia".

## 6. Znane ograniczenia (uczciwie, nie ukryte)

- Klasyfikator ma 65% top-1 accuracy — widać to wprost w scenariuszu B wyżej,
  a także w złapanym na żywo przypadku pytania o sanepid błędnie
  sklasyfikowanego jako `hr`.
- **Wyniki są niedeterministyczne i to jest ryzyko produktowe, nie usterka do
  wyprompotowania.** Ten sam prompt i to samo pytanie w dwóch kolejnych
  przebiegach dały: raz cytowanie sekcji **4.1** (brak towaru — poprawnie), raz
  **4.3** (pomyłka dostawcy — merytorycznie obok). W jednym przebiegu dokument
  bez załącznika zamiast czystego placeholdera zawierał **zmyślony link
  markdown** z nieistniejącym adresem. Właśnie dlatego warstwy HITL i walidacji
  nie są ozdobnikiem: przy modelu tej klasy trzeba **projektować pod założenie,
  że model czasem zawiedzie**, zamiast liczyć na to, że przestanie.
- **Zmyślanie rozwinięć skrótów — najciekawsza porażka i to, czego nauczyła.**
  Runbooki piszą skróty bez rozwinięć (WZ, HACCP, e-ZLA), a model uporczywie
  wypełniał tę lukę zgadywaniem. **Trzy rundy pracy nad promptem** —
  zwykła reguła, potem przykłady DOBRZE/ŹLE, potem przykłady jako urwane
  fragmenty z innego runbooka — i za każdym razem model wracał z **nowym**
  wymysłem: „Wywiad Zamówienia", „Widok Zamówienia", „Zamówienia Zamkowego",
  „Widza Zlecenia", wreszcie „Wariant Zgodności". Po drodze dwie lekcje:
  - **Pierwszy test regresyjny był bezużyteczny** — listował konkretne znane
    frazy, więc przechodził na zielono, gdy model wymyślił kolejną. Przepisany
    na wzorzec *kształtu* rozwinięcia.
  - **Przykład w prompcie stał się szablonem** — po dodaniu „DOBRZE: Odnotuj
    brak na WZ z podpisem kierowcy." model zaczął zwracać dokładnie to jedno
    zdanie jako całą odpowiedź, gubiąc kroki procedury.

  **Wniosek, który uważam za najważniejszy w całym projekcie:** przy modelu tej
  klasy zgodność z instrukcją nie jest problemem promptowym, tylko
  inżynierskim. Ostatecznie zadziałał **deterministyczny strażnik w kodzie**
  ([`agents/abbreviations.py`](https://github.com/goreckip/MultiAgentPoC/blob/main/src/multiagent_poc/agents/abbreviations.py)):
  rozwinięcie skrótu przechodzi tylko wtedy, gdy **dosłownie występuje w
  kontekście** podanym modelowi; wszystko inne jest sprowadzane do samego
  skrótu. Reguła w prompcie została jako pierwsza linia obrony, ale to kod
  daje gwarancję. Pokryte 10 testami jednostkowymi — po jednym na każdy
  wymysł, który model faktycznie wyprodukował.
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
