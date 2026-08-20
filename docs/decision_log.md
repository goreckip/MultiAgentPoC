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

## Tydzień 3 — 2026-08-19

- **Decyzja:** klasyfikator intencji jako k-NN nad zbiorem przykładowych fraz
  (`exemplars.py`, 6 fraz × 8 kategorii, osobna kolekcja Chroma
  `intent_exemplars`), nie centroidy i nie LLM-classifier.
  **Dlaczego:** najprostsze podejście, które da się w pełni wytłumaczyć
  (confidence = odsetek głosów zwycięskiej intencji wśród k najbliższych
  sąsiadów) i które reużywa infrastruktury z Tygodnia 2 (Ollama embeddings +
  Chroma). Świadomie **osobny zbiór przykładów od `test_questions.md`** —
  ten drugi to zbiór ewaluacyjny (`eval_set.py`, strukturalna kopia), użycie
  tych samych fraz jako danych referencyjnych i testowych zafałszowałoby wynik
  (data leakage).
  **Efekt:** patrz kolejne wpisy — kilka iteracji było potrzebnych, żeby
  dojść do sensownej trafności.

- **Decyzja:** metryka cosine zamiast domyślnej l2 w Chroma dla kolekcji
  `intent_exemplars` — **odrzucona po teście** (bez wpływu na wynik).
  **Dlaczego:** hipoteza, że l2 na nieznormalizowanych wektorach słabo
  różnicuje krótkie frazy. W praktyce ranking sąsiadów wyszedł identyczny —
  embeddingi z `nomic-embed-text` mają najwyraźniej zbliżone normy, więc l2 i
  cosine dają tę samą kolejność.
  **Efekt:** zostaje domyślne l2 (kod nie komplikowany bez potrzeby).

- **Decyzja:** prefiksy zadania Nomic (`search_query:`/`search_document:`)
  przy embeddingu — **przetestowane i odrzucone**.
  **Dlaczego:** Nomic rekomenduje te prefiksy dla `nomic-embed-text`, więc
  spodziewałem się poprawy. W teście na naszym zbiorze pogorszyły trafność
  (45% → 30%) zamiast poprawić — prawdopodobnie dlatego, że nasze "dokumenty"
  (krótkie frazy przykładowe) nie są klasycznymi dokumentami do wyszukiwania,
  tylko etykietowanymi przykładami do klasyfikacji, więc prefiks
  retrieval-owy wprowadza niedopasowanie zamiast pomagać.
  **Efekt:** kod bez prefiksów — surowe teksty do `embed_documents`/`embed_query`.

- **Decyzja:** `k=3` w głosowaniu k-NN (zamiast domyślnego `k=5`).
  **Dlaczego:** przy tylko 6 przykładach na kategorię i 8 kategoriach,
  `k=5` był zbyt podatny na szum (za dużo szans na głosy z niepowiązanych
  kategorii). Test przemiatający `k` na całym zbiorze ewaluacyjnym:
  k=1: 60%, k=2: 50%, k=3: **65%**, k=4: 45%, k=5: 45%. `k=3` dodatkowo daje
  wygodną granulację confidence (0/3, 1/3, 2/3, 3/3), gdzie próg 0.6 sensownie
  wymaga zgody co najmniej 2 z 3 sąsiadów.
  **Efekt:** `classify()` domyślnie używa `k=3`.

- **Decyzja:** finalna trafność klasyfikatora na 20-pytaniowym zbiorze
  ewaluacyjnym (`scripts/evaluate_classifier.py`) to **65% (13/20)**, ale
  **100% (5/5) na pytaniach bezpieczeństwa** (dane wrażliwe, prompt injection,
  pytania spoza katalogu — wszystkie poprawnie eskalowane).
  **Dlaczego to akceptowalne na tym etapie:** confidence gate jest z założenia
  konserwatywny — przy niepewności (remis głosów, brak wyraźnej większości)
  ESKALUJE, zamiast zgadywać. Większość "MISS" w ewaluacji to właśnie
  przypadki, gdzie klasyfikator poprawnie nie miał pewności (np. "Dostawca
  przywiózł inny towar..." dostał tylko 1/3 głosów na `dostawy`, resztę
  rozproszone) i oddał sprawę do eskalacji zamiast błędnie odpowiedzieć — co z
  punktu widzenia bezpieczeństwa produktu jest właściwym zachowaniem, nawet
  jeśli psuje metrykę "top-1 accuracy".
  **Efekt:** udokumentowany jako podłoga regresyjna w `test_classifier.py`
  (asercja >= 60%, nie cel docelowy). Do poprawy w przyszłości: więcej
  przykładów na kategorię, ewentualnie LLM-classifier jako alternatywa do
  porównania (temat na Tydzień 5-6, przy okazji porównania modeli).

## Rozszerzenie planu — 2026-08-19

- **Decyzja:** dodanie możliwości załączenia pliku PDF (np. zamówienia) jako
  dodatkowego kontekstu dla klasyfikatora intencji, używanego tylko gdy
  `confidence < próg` — wchodzi do Warstwy 5 (walidacja) jako punkty 5.5-5.8
  w `requirements.md`.
  **Dlaczego:** naturalne rozszerzenie confidence gate — zamiast tylko
  "eskaluj", trzecia opcja to "sprawdź załącznik, może rozstrzygnie
  niejednoznaczność". Świadomie ograniczone na start do PDF z warstwą
  tekstową (bez OCR obrazów) i tylko do trybu "confidence gate ma wątpliwości",
  żeby nie rozmywać rdzenia Tygodnia 4 (graf, subagenci, walidacja, HITL).
  **Warunek:** skan antywirusowy załącznika (5.6) jest blokujący dla samej
  funkcji (5.5) — żaden plik nie trafia do parsowania/embeddingu przed
  skanem. Wybór narzędzia (lokalny skaner vs. usługa) do rozstrzygnięcia
  przed implementacją — patrz pytanie do użytkownika w tej samej sesji.
  **Efekt:** TBD — implementacja zaplanowana na Tydzień 4, razem z resztą
  warstwy walidacji. Agent "data retrieval" (5.8), który aktywnie
  wykorzystuje treść załącznika w generowanej odpowiedzi (nie tylko do
  poprawy klasyfikacji), to świadomy follow-up na Tydzień 5+, żeby nie
  łączyć dwóch różnych funkcji w jednej iteracji.

## Tydzień 4 (część 1) — załącznik PDF + skan antywirusowy — 2026-08-19

- **Decyzja:** ClamAV lokalnie (portable, `.clamav/`, gitignored), nie
  VirusTotal API ani uproszczona walidacja typu pliku.
  **Dlaczego:** zgodne z założeniem "wszystko lokalnie/za darmo" — plik nigdy
  nie opuszcza maszyny (w przeciwieństwie do VirusTotal), a to prawdziwy skan
  sygnaturowy, nie tylko sprawdzenie nagłówka MIME. Świadomy wybór użytkownika
  po przedstawieniu trade-offów (lokalne+wolniejsze vs. chmura+wyciek danych
  vs. szybkie ale nieprawdziwe).
  **Efekt:** zainstalowany oficjalny build Windows (GitHub release
  Cisco-Talos/clamav 1.5.4 — strona clamav.net blokowała scripted download
  przez Cloudflare), bazy sygnatur pobrane przez `freshclam` (~113MB).
  Test EICAR (standardowy nieszkodliwy plik testowy AV) został skwarantannowany
  przez Windows Defender **zanim ClamAV zdążył go zeskanować** — potwierdza,
  że ochrona antywirusowa na tej maszynie faktycznie działa, ale uniemożliwia
  bezpośredni test detekcji przez samego ClamAV w tym środowisku. Silnik
  ClamAV zweryfikowany jako działający na czystych plikach
  (`test_scan_clean_file_against_real_clamav`); ścieżka detekcji malware
  przetestowana przez mockowanie `subprocess.run` (kod obsługi exit code 1),
  nie przez faktyczne wykrycie.
  **Znane ograniczenie:** `clamscan` przeładowuje całą bazę sygnatur (~113MB)
  przy każdym wywołaniu — ok. 20-25s na skan. Świadomie zaakceptowane dla PoC
  (skan nie jest hot-pathem, dzieje się raz na załącznik). `clamd`/`clamdscan`
  (proces w tle + gniazdo) byłoby szybsze przy realnym obciążeniu — możliwa
  przyszła optymalizacja, nieuzasadniona na tym etapie.

- **Decyzja:** kolejność w pipeline — skan malware **zawsze i natychmiast**
  po otrzymaniu załącznika (przed klasyfikacją tekstową), parsowanie treści
  PDF **tylko** gdy klasyfikacja samego pytania wypadła poniżej progu.
  **Dlaczego:** fail-fast na bezpieczeństwie (złośliwy plik nigdy nie dotrze
  nawet do parsera PDF, niezależnie od tego, czy okazałby się potrzebny do
  klasyfikacji), a parsowanie na żądanie oszczędza pracę, gdy klasyfikator i
  tak był pewny na podstawie samego pytania.
  **Efekt:** `classification/pipeline.py::handle_question()` — test
  `test_rejected_attachment_aborts_before_classification` potwierdza, że
  odrzucony załącznik przerywa cały przepływ, zanim `classify()` w ogóle
  zostanie wywołane.

- **Decyzja:** żywa (nie mockowana) weryfikacja end-to-end na przykładzie
  celowo dobranym z Tygodnia 3 (`scripts/demo_attachment_pipeline.py`).
  **Efekt (realne liczby):** pytanie "Lodówka z nabiałem pokazuje 8 stopni,
  co robię z towarem i co robię z lodówką?" bez załącznika: `confidence=0.33`,
  eskalacja do `inne`. Z załączonym PDF (karta kontroli temperatur, słownictwo
  zbliżone do runbooka higieny — "termometr", "temperatura", "sanepid"):
  `confidence=0.67`, poprawnie `higiena`, bez eskalacji. Przy pierwszej
  próbie treści załącznika (numer zamówienia zamiast słownictwa higieny)
  reklasyfikacja **nie** poprawiła pewności — uczciwy wynik pokazujący, że
  funkcja mechanicznie działa (`used_attachment=True`), ale nie gwarantuje
  rozwiązania niepewności, jeśli treść załącznika słabo pokrywa się z
  przykładami klasyfikatora (patrz znane ograniczenie klasyfikatora,
  Tydzień 3).

## Tydzień 4 (część 2) — walidacja, subagenci, graf LangGraph, HITL — 2026-08-19

- **Decyzja:** pozostałe reguły walidacji (PESEL, prompt injection, prośby o
  dane osób trzecich, format numeru zamówienia) jako proste reguły
  regex/keyword (`validation/input_validation.py`), nie osobny model/LLM-classifier.
  **Dlaczego:** zakres PoC — cztery konkretne przypadki z `test_questions.md`
  (16, 17/18, 19, 20), nie ogólny system DLP. PESEL dodatkowo zweryfikowany
  sumą kontrolną (nie tylko "11 cyfr pod rząd"), żeby nie fałszywie odrzucać
  np. losowego 11-cyfrowego numeru telefonu — test
  `test_random_11_digits_without_valid_checksum_is_not_flagged_as_pesel`
  pilnuje tego rozróżnienia.
  **Efekt:** PESEL/prompt injection/dane osób trzecich → twardy odrzut
  (`ValidationRejected`, pytanie nigdy nie dociera do klasyfikatora ani LLM-a).
  Zły format numeru zamówienia → tylko flaga (`order_number_invalid_format`),
  pytanie idzie dalej — bo pytania 17/18 w zbiorze ewaluacyjnym mają nadal
  poprawnie klasyfikować się jako `dostawy`, niezależnie od poprawności
  formatu numeru.

- **Decyzja:** subagenci per kategoria (`agents/subagent.py`) to ten sam kod
  retrieval+generacji z Tygodnia 2, ale (a) retrieval filtrowany do runbooka
  danej intencji (`where={"source": ...}` w Chroma) i (b) krótki dopisek do
  system promptu per kategoria (np. BHP → podkreśl pilność, reklamacje →
  sekcja "czego NIE robimy" to twardy zakaz).
  **Dlaczego:** to konkretna, testowalna różnica względem ogólnego RAG z
  Tygodnia 2 (tam retrieval przeszukiwał cały korpus), a nie 8 kopii tego
  samego kodu z różnymi nazwami plików — uniknięcie duplikacji przy
  zachowaniu ducha "osobny agent per kategoria" z planu.
  **Efekt:** zweryfikowane na żywo — pytanie o pomyłkę dostawcy zwraca
  odpowiedź zgodną z sekcją 4.3 `01_dostawy.md` i `sources=['01_dostawy.md']`
  (nigdy inny plik, dzięki filtrowi).

- **Decyzja:** graf LangGraph (`graph/pipeline_graph.py`) jako cienka warstwa
  routingu **nad** już istniejącym `classification/pipeline.py`, nie
  przepisanie logiki od nowa w węzłach grafu.
  **Dlaczego:** walidacja+klasyfikacja+gate+załącznik były już napisane i
  przetestowane jako zwykłe funkcje Pythona (Tydzień 3-4/1) — graf dodaje
  tylko to, czego zwykła funkcja nie potrafi: **pauzę i wznowienie** przez
  `interrupt()`/`Command(resume=...)` dla eskalacji do człowieka, oraz
  routing między węzłem auto-odpowiedzi (subagent) a węzłem HITL.
  **Efekt:** zweryfikowane na żywo (`scripts/demo_graph.py`) — pytanie
  eskalowane faktycznie **wstrzymuje graf** (`"__interrupt__"` w wyniku
  `invoke`), a po `graph.invoke(Command(resume=odpowiedź), config=ten_sam_thread_id)`
  stan wraca dokładnie tam, gdzie stanął, z odpowiedzią człowieka jako
  finalną odpowiedzią. Wymaga `MemorySaver` (checkpointer) i stałego
  `thread_id` w configu na cały wątek rozmowy.

- **Znane ograniczenie (uczciwie odnotowane, nie ukryte):** live demo
  (`scripts/demo_graph.py`) ujawniło żywy przykład problemu z Tygodnia 3 —
  pytanie "Sanepid zapowiedział kontrolę na jutro, na co mam zwrócić uwagę?"
  zostało błędnie sklasyfikowane jako `hr` (confidence 0.67, powyżej progu),
  więc trafiło do auto-odpowiedzi zamiast eskalacji, a subagent HR
  odpowiedział, że nie ma info o sanepidzie w swoim runbooku — poprawnie
  rozpoznał brak dopasowania kontekstu, ale na złym etapie (powinno było
  eskalować już na etapie gate, nie dopiero w odpowiedzi LLM-a). To pokazuje
  granicę obecnego klasyfikatora (65% accuracy, Tydzień 3) w praktyce, nie
  tylko w ewaluacji offline.
  **Możliwe kierunki poprawy (nieuzasadnione jeszcze na tym etapie):**
  więcej przykładów na kategorię, wyższy próg confidence, albo prosty
  post-check w subagencie ("czy kontekst faktycznie odpowiada na pytanie,
  czy zgłosić brak dopasowania zamiast zgadywać") jako dodatkowa siatka
  bezpieczeństwa nad samym gate.

## Tydzień 5 (część 1) — Streamlit UI — 2026-08-20

- **Decyzja:** jedna strona Streamlit z dwiema sekcjami (formularz pytania +
  panel HITL), nie osobne widoki dla pracownika i operatora.
  **Dlaczego:** świadomy wybór użytkownika — do solo-demo (jedna osoba
  symuluje obie role) prostsze niż multi-page routing, mniej kodu
  nawigacyjnego. Szczegóły techniczne (intencja, confidence, flagi) zawsze
  widoczne w expanderze pod odpowiedzią — też świadomy wybór, dobre pod
  demo/rozmowę kwalifikacyjną (widać confidence gate na żywo), kosztem
  czystości UX docelowego dla pracownika sklepu.
  **Efekt:** `app.py`, jeden plik, `st.cache_resource` dla instancji grafu
  (bezpieczne mimo współdzielenia między "użytkownikami" — cały stan wątku
  rozmowy trzyma checkpointer `MemorySaver`, keyowany po `thread_id` w
  `st.session_state`, nie w obiekcie grafu).

- **Decyzja:** `chroma_persist_dir` w `config.py` zmieniony z domyślnej
  ścieżki względnej (`"data/chroma"`) na bezwzględną (liczona względem
  `PROJECT_ROOT`, tak jak ścieżki ClamAV i runbooków).
  **Dlaczego:** Streamlit (i ogólnie serwery uruchamiane przez zewnętrzne
  narzędzia/IDE) niekoniecznie mają katalog roboczy ustawiony na root
  projektu — ścieżka względna po cichu tworzyłaby nową, pustą bazę Chroma
  zamiast używać już zaindeksowanych runbooków. Znaleziono i naprawiono
  proaktywnie, przed uruchomieniem UI, nie jako efekt awarii na żywo.
  **Efekt:** wszystkie ścieżki w configu są teraz cwd-niezależne.

- **Weryfikacja na żywo (Browser preview):** przetestowany pełny przepływ w
  przeglądarce — (1) pytanie z niską pewnością poprawnie eskaluje i pokazuje
  panel HITL, wpisana odpowiedź operatora poprawnie wraca do historii jako
  "Rozwiązane przez: człowiek (HITL)"; (2) pytanie z PESEL-em poprawnie
  odrzucone przez walidację, nigdy nie dotarło do klasyfikatora; (3) pytanie
  BHP z wysoką pewnością auto-odpowiedziane, treść zgodna z runbookiem.
  **Zaobserwowana latencja:** ok. 78s na pełny cykl klasyfikacja+generacja
  dla trzeciego przypadku — CPU-only inference `llama3.1:8b` na tej maszynie
  jest zauważalnie wolne. Zaakceptowane dla PoC (interfejs pokazuje spinner
  z opisem etapu), ale warte odnotowania jako realne ograniczenie przy
  ewentualnym demo na żywo — GPU albo mniejszy model skróciłyby to znacząco.

## Tydzień 5 (część 2) — Langfuse Cloud (observability) — 2026-08-20

- **Decyzja:** konto Langfuse Cloud (region EU, `cloud.langfuse.com`) założone
  przez użytkownika (nie przeze mnie — zakładanie kont to poza tym, co robię
  automatycznie), klucze API wklejone bezpośrednio do lokalnego `.env`
  (gitignored). Zweryfikowane `auth_check()` przed pisaniem integracji.
  **Efekt:** `settings.langfuse_*` w `config.py` już istniały z Tygodnia 2 —
  wystarczyło dodać wartości do `.env`.

- **Decyzja:** dwa mechanizmy naraz zamiast jednego — dekorator `@observe()`
  (Langfuse SDK v3, oparty o OpenTelemetry + contextvars) na kluczowych
  funkcjach (`validate_input`, `classify`, `decide`, `subagent.answer`,
  `handle_question`, `scan_file`) DO tworzenia zagnieżdżonych spanów, plus
  jawnie przekazywany `CallbackHandler` z `langfuse.langchain` do wywołań
  `ChatOllama.invoke(..., config={"callbacks": [...]})` DO wyciągnięcia
  tokenów/kosztu/modelu z samej generacji LLM.
  **Dlaczego:** `@observe()` samo w sobie łapie input/output i czas
  wykonania dowolnej funkcji, ale nie rozumie, że dana funkcja "jest"
  wywołaniem LLM — nie wyciągnie liczby tokenów ani nazwy modelu z
  surowego zwracanego stringa. `CallbackHandler` z kolei rozumie strukturę
  odpowiedzi LangChain (`ChatOllama`) i tworzy dedykowany observation typu
  `GENERATION` z tymi danymi. Osobno każdy z nich dawałby niepełny obraz.
  **Efekt (zweryfikowane realnym trace'em przez `lf.api.trace.get(...)`):**
  jeden trace `handle_user_turn` (nowy wrapper `graph/pipeline_graph.py::invoke_graph`,
  wywoływany zamiast gołego `graph.invoke()` w `app.py` i `scripts/demo_graph.py`)
  zawiera zagnieżdżone spany `handle_question` → `validate_input` +
  `classify_intent` + `confidence_gate` → `subagent_answer` → observation
  `GENERATION` (`ChatOllama`) z `model=llama3.1:8b`, `usage: input=672
  output=33 total=705 TOKENS`, `latency=85.48s`. Koszt (`*_cost`) wyszedł
  `None` — oczekiwane, model lokalny przez Ollama nie ma wpisu w cenniku
  Langfuse, ale tokeny i latencja i tak dają realną wartość obserwowalności.

- **Decyzja:** `invoke_graph()` jako jedyny punkt wejścia do grafu (zamiast
  dekorowania samych węzłów LangGraph), żeby dostać jeden trace na całe
  wywołanie zamiast osobnego trace'a per węzeł.
  **Dlaczego:** kontekst trace'a propaguje się przez contextvars przez cały
  synchroniczny stos wywołań — opakowanie punktu wejścia jedną dekorowaną
  funkcją wystarczyło, żeby wszystko wewnątrz (łącznie z wywołaniami przez
  LangGraph) zagnieździło się automatycznie, bez ręcznego przekazywania
  kontekstu trace'a do każdego węzła z osobna.
  **Znane uproszczenie:** przy eskalacji HITL, wznowienie (`Command(resume=...)`)
  to osobne wywołanie `invoke_graph()`, więc pytanie eskalowane dostaje
  **dwa** trace'y (przed pauzą i po wznowieniu), nie jeden ciągły. Świadomie
  zaakceptowane — łączenie ich w jeden trace przez współdzielony
  `trace_context` to możliwe rozszerzenie, nieuzasadnione na tym etapie.

## Szablon na kolejne tygodnie

```
## Tydzień N — YYYY-MM-DD

- **Decyzja:** ...
  **Dlaczego:** ...
  **Efekt:** ...
```
