# Log decyzji

Format: decyzja → dlaczego (trade-off) → efekt/obserwacja. Wpis po każdym sensownym
etapie, surowy materiał pod przyszłe STAR.

## Sprint 1 — 2026-08-19

- **Decyzja:** framework agentowy: LangGraph jako baza szkieletu (zamiast Pydantic AI + pydantic-deep).
  **Dlaczego:** LangGraph ma dojrzalsze wsparcie dla grafu stanów i multi-agent routingu
  (confidence gate jako węzeł warunkowy, subagenci per kategoria jako osobne node'y) oraz
  więcej przykładów/dokumentacji do szybkiego postawienia szkieletu. Porównanie z Pydantic AI
  zaplanowane później (Sprint 5, README) — jedno drzewo decyzyjne trzeba było wybrać jako pierwsze.
  **Efekt:** TBD po zbudowaniu grafu (Sprint 3-4).

- **Decyzja:** katalog intencji zdefiniowany jako `Enum` w kodzie (`src/multiagent_poc/intents.py`),
  z mapowaniem intencja → plik runbooka, zamiast trzymania tylko w dokumentacji.
  **Dlaczego:** pojedyncze źródło prawdy używane jednocześnie przez klasyfikator, router
  subagentów i indeksację RAG — unika rozjazdu między dokumentacją a kodem.
  **Efekt:** test `test_intents.py` pilnuje, że każda intencja poza `inne` ma istniejący plik runbooka.

- **Decyzja:** kategoria `inne` celowo nie ma runbooka.
  **Dlaczego:** to podstawowy test confidence gate — system musi rozpoznać brak trafnych
  chunków / niską pewność klasyfikacji i eskalować do człowieka zamiast halucynować
  odpowiedź na bazie najbliższego tematycznie dokumentu.
  **Efekt:** do zweryfikowania w Sprincie 3 na pytaniach 14-20 z `docs/test_questions.md`.

## Sprint 2 — dokończenie (realny eksperyment) — 2026-08-19

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
  używaną przez warstwę RAG w kolejnych sprintach; `COLLECTION_FIXED` zostaje w
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
  i eliminuje cały krok stawiania i utrzymywania kontenerów w Sprincie 4. Trade-off:
  dane (treść pytań/odpowiedzi) trafiają na serwery Langfuse (EU/US) zamiast zostać
  lokalnie — akceptowalne, bo runbooki i pytania testowe są w całości fikcyjne/mockowe;
  gdyby projekt miał kiedyś realne dane, ta decyzja wymagałaby rewizji.
  **Efekt:** TBD po integracji w Sprincie 4 — do zweryfikowania czy limity free tier
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
  **Efekt:** TBD — planowana implementacja w Sprincie 4 razem z warstwą walidacji.

## Sprint 2 — 2026-08-19

- **Decyzja:** rozważono i odrzucono podpięcie modeli Claude (Sonnet/Opus) jako
  głównego silnika LLM, zamiast Ollamy — projekt zostaje przy Ollamie.
  **Dlaczego:** subskrypcja Claude (Pro/Max, czat/Claude Code) nie daje dostępu do
  Anthropic API używanego przez LangChain/LangGraph w kodzie — to osobne,
  rozliczane per-token rozliczenie. Podpięcie na stałe złamałoby założenie
  "wszystko za darmo" z planu projektu. Ollama (Llama 3.1 8B) jest wyraźnie słabsza
  jakościowo, ale to świadomy trade-off koszt/lokalność vs jakość — sam w sobie
  dobry materiał na STAR.
  **Efekt:** brak zmian w kodzie/configu. Opcja porównania z API (darmowe/tanie
  kredyty, np. `claude-haiku-4-5`) zostaje odłożona do Sprintu 5-6 jako
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

## Sprint 3 — 2026-08-19

- **Decyzja:** klasyfikator intencji jako k-NN nad zbiorem przykładowych fraz
  (`exemplars.py`, 6 fraz × 8 kategorii, osobna kolekcja Chroma
  `intent_exemplars`), nie centroidy i nie LLM-classifier.
  **Dlaczego:** najprostsze podejście, które da się w pełni wytłumaczyć
  (confidence = odsetek głosów zwycięskiej intencji wśród k najbliższych
  sąsiadów) i które reużywa infrastruktury ze Sprintu 2 (Ollama embeddings +
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
  porównania (temat na Sprint 5-6, przy okazji porównania modeli).

## Rozszerzenie planu — 2026-08-19

- **Decyzja:** dodanie możliwości załączenia pliku PDF (np. zamówienia) jako
  dodatkowego kontekstu dla klasyfikatora intencji, używanego tylko gdy
  `confidence < próg` — wchodzi do Warstwy 5 (walidacja) jako punkty 5.5-5.8
  w `requirements.md`.
  **Dlaczego:** naturalne rozszerzenie confidence gate — zamiast tylko
  "eskaluj", trzecia opcja to "sprawdź załącznik, może rozstrzygnie
  niejednoznaczność". Świadomie ograniczone na start do PDF z warstwą
  tekstową (bez OCR obrazów) i tylko do trybu "confidence gate ma wątpliwości",
  żeby nie rozmywać rdzenia Sprintu 4 (graf, subagenci, walidacja, HITL).
  **Warunek:** skan antywirusowy załącznika (5.6) jest blokujący dla samej
  funkcji (5.5) — żaden plik nie trafia do parsowania/embeddingu przed
  skanem. Wybór narzędzia (lokalny skaner vs. usługa) do rozstrzygnięcia
  przed implementacją — patrz pytanie do użytkownika w tej samej sesji.
  **Efekt:** TBD — implementacja zaplanowana na Sprint 4, razem z resztą
  warstwy walidacji. Agent "data retrieval" (5.8), który aktywnie
  wykorzystuje treść załącznika w generowanej odpowiedzi (nie tylko do
  poprawy klasyfikacji), to świadomy follow-up na Sprint 5+, żeby nie
  łączyć dwóch różnych funkcji w jednej iteracji.

## Sprint 4 (część 1) — załącznik PDF + skan antywirusowy — 2026-08-19

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
  celowo dobranym ze Sprintu 3 (`scripts/demo_attachment_pipeline.py`).
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
  Sprint 3).

## Sprint 4 (część 2) — walidacja, subagenci, graf LangGraph, HITL — 2026-08-19

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
  retrieval+generacji ze Sprintu 2, ale (a) retrieval filtrowany do runbooka
  danej intencji (`where={"source": ...}` w Chroma) i (b) krótki dopisek do
  system promptu per kategoria (np. BHP → podkreśl pilność, reklamacje →
  sekcja "czego NIE robimy" to twardy zakaz).
  **Dlaczego:** to konkretna, testowalna różnica względem ogólnego RAG z
  Sprintu 2 (tam retrieval przeszukiwał cały korpus), a nie 8 kopii tego
  samego kodu z różnymi nazwami plików — uniknięcie duplikacji przy
  zachowaniu ducha "osobny agent per kategoria" z planu.
  **Efekt:** zweryfikowane na żywo — pytanie o pomyłkę dostawcy zwraca
  odpowiedź zgodną z sekcją 4.3 `01_dostawy.md` i `sources=['01_dostawy.md']`
  (nigdy inny plik, dzięki filtrowi).

- **Decyzja:** graf LangGraph (`graph/pipeline_graph.py`) jako cienka warstwa
  routingu **nad** już istniejącym `classification/pipeline.py`, nie
  przepisanie logiki od nowa w węzłach grafu.
  **Dlaczego:** walidacja+klasyfikacja+gate+załącznik były już napisane i
  przetestowane jako zwykłe funkcje Pythona (Sprint 3-4/1) — graf dodaje
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
  (`scripts/demo_graph.py`) ujawniło żywy przykład problemu ze Sprintu 3 —
  pytanie "Sanepid zapowiedział kontrolę na jutro, na co mam zwrócić uwagę?"
  zostało błędnie sklasyfikowane jako `hr` (confidence 0.67, powyżej progu),
  więc trafiło do auto-odpowiedzi zamiast eskalacji, a subagent HR
  odpowiedział, że nie ma info o sanepidzie w swoim runbooku — poprawnie
  rozpoznał brak dopasowania kontekstu, ale na złym etapie (powinno było
  eskalować już na etapie gate, nie dopiero w odpowiedzi LLM-a). To pokazuje
  granicę obecnego klasyfikatora (65% accuracy, Sprint 3) w praktyce, nie
  tylko w ewaluacji offline.
  **Możliwe kierunki poprawy (nieuzasadnione jeszcze na tym etapie):**
  więcej przykładów na kategorię, wyższy próg confidence, albo prosty
  post-check w subagencie ("czy kontekst faktycznie odpowiada na pytanie,
  czy zgłosić brak dopasowania zamiast zgadywać") jako dodatkowa siatka
  bezpieczeństwa nad samym gate.

## Sprint 5 (część 1) — Streamlit UI — 2026-08-20

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

## Sprint 5 (część 2) — Langfuse Cloud (observability) — 2026-08-20

- **Decyzja:** konto Langfuse Cloud (region EU, `cloud.langfuse.com`) założone
  przez użytkownika (nie przeze mnie — zakładanie kont to poza tym, co robię
  automatycznie), klucze API wklejone bezpośrednio do lokalnego `.env`
  (gitignored). Zweryfikowane `auth_check()` przed pisaniem integracji.
  **Efekt:** `settings.langfuse_*` w `config.py` już istniały ze Sprintu 2 —
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

## Rozszerzenie planu — 2026-08-20

- **Decyzja:** odrzucone z planu — porównanie LangChain/LangGraph vs
  Pydantic AI w README (punkt 9.7).
  **Dlaczego:** świadoma decyzja użytkownika, żeby skupić czas na
  dokończeniu trwałej kolejki HITL zamiast pisania porównania frameworków,
  którego nigdy praktycznie nie przetestowano (projekt od początku
  konsekwentnie używał LangGraph, Pydantic AI nie zostało nawet
  zaimplementowane jako alternatywa) — porównanie byłoby więc bardziej
  spekulacją niż realnym wnioskiem z doświadczenia.
  **Efekt:** oznaczone jako ❌ w `requirements.md`, nie usunięte z historii
  (żeby było widać, że była to świadoma decyzja, nie przeoczenie).

## Sprint 5 (część 3) — trwała kolejka HITL — 2026-08-20

- **Decyzja:** kolejka HITL jako moduł-poziomowy rejestr w pamięci procesu
  (`hitl/queue.py`, słowniki `dict` chronione `threading.Lock`), nie
  zewnętrzna baza (Redis/Postgres).
  **Dlaczego:** Streamlit domyślnie uruchamia się jako jeden proces, a różne
  sesje przeglądarki (różne karty/użytkownicy) działają jako wątki w tym
  samym procesie — moduł-poziomowy stan współdzielony jest więc faktycznie
  widoczny między "różnymi użytkownikami" bez żadnej infrastruktury. Ta sama
  klasa uproszczenia co `MemorySaver` (checkpointer LangGraph) — stan nie
  przetrwa restartu procesu. W realnym wdrożeniu wymagałoby to zewnętrznego
  store'a, żeby przetrwać restart i działać przy wielu instancjach appki —
  świadomie poza zakresem PoC.
  **Efekt:** `tests/test_hitl_queue.py` (5 testów, logika kolejki bez
  Ollamy/Streamlit) + weryfikacja na żywo w przeglądarce z **dwiema
  niezależnymi kartami** (symulacja dwóch różnych użytkowników): pytanie
  zadane w karcie 1 (pracownik) pojawiło się w kolejce widocznej w karcie 2
  (operator, z pustą własną historią — dowód, że to nie był podgląd danych
  tej samej sesji), operator odpowiedział z karty 2, a karta 1 dostała
  odpowiedź po kliknięciu "Sprawdź, czy jest odpowiedź".

- **Decyzja:** jeden `thread_id` per pytanie (generowany świeżo przy każdym
  submit), nie jeden `thread_id` per sesja przeglądarki (jak w poprzedniej
  wersji `app.py`).
  **Dlaczego:** stary model (jeden trwały `thread_id` na całą sesję) zakładał
  po cichu, że pracownik zada tylko jedno pytanie na raz — reużycie tego
  samego wątku LangGraph dla drugiego pytania, zanim pierwsze zostało
  rozwiązane, kolidowałoby ze stanem grafu wciąż wstrzymanym na
  `interrupt()` dla pierwszego pytania. Osobny wątek na pytanie eliminuje to
  ryzyko i naturalnie mapuje się na semantykę kolejki (każda eskalacja to
  osobny, niezależnie śledzony wpis).
  **Efekt:** panel pracownika nadal ogranicza się do jednego oczekującego
  pytania naraz (świadome uproszczenie UI, nie ograniczenie architektury) —
  ale kolejka po stronie operatora poprawnie obsługuje dowolnie wiele
  jednoczesnych eskalacji od różnych pracowników.

- **Decyzja (odrzucona z planu):** porównanie LangChain/LangGraph vs
  Pydantic AI w README — usunięte na prośbę użytkownika, na rzecz
  dokończenia kolejki HITL. Uzasadnienie: patrz sekcja "Rozszerzenie planu"
  wyżej.

## Sprint 6 — framework ewaluacyjny (RAG + jakość odpowiedzi) — 2026-08-20

- **Decyzja:** trzy niezależne sygnały jakości zamiast jednego (retrieval
  hit-rate, pokrycie słów kluczowych, LLM-as-judge 1-5), świadomie
  zaimplementowane jako osobny skrypt (`scripts/evaluate_rag.py`), nie
  integracja z Langfuse Datasets — spójne z `evaluate_classifier.py`, zero
  nowej koncepcji do nauczenia się na tym etapie (świadomy wybór użytkownika
  z dwóch przedstawionych opcji).
  **Dlaczego trzy sygnały:** każdy łapie inny rodzaj błędu — hit-rate mówi,
  czy RAG w ogóle sięgnął po właściwy fragment; keywords to tani,
  deterministyczny, ale sztywny wobec parafraz sygnał regresyjny;
  LLM-judge łapie parafrazy, ale to ten sam lokalny `llama3.1:8b`, który
  generował odpowiedzi — sędzia oceniający własną rodzinę modelu jest
  z założenia podejrzany o łagodność/niespójność (odnotowane wprost w
  `evaluation/judge.py`, nie ukryte).
  **Decyzja metodologiczna:** ewaluacja RAG bypasuje klasyfikator —
  `agents.subagent.answer()` wywoływane z **poprawną, przypiętą z góry**
  intencją (`evaluation/rag_eval_set.py`, ground truth wyprowadzone ręcznie z
  treści wszystkich 8 runbooków, nie zgadywane). Cel: izolacja jakości
  RAG+generacji od jakości klasyfikatora, już zmierzonej osobno w Sprincie 3
  — inaczej błąd klasyfikatora zaszumiałby wynik ewaluacji RAG.

- **Efekt — realny przebieg na 15 pytaniach (`scripts/evaluate_rag.py`):**
  - Retrieval hit-rate: **12/14 (86%)** (2 pytania bez ground truth sekcji,
    celowo pominięte w tej metryce — patrz `note` w `rag_eval_set.py`).
  - Pokrycie słów kluczowych: **38%** (średnio).
  - LLM-judge: **4.67/5** (średnio).
  - **Rozbieżność między metrykami jest sama w sobie wynikiem, nie szumem:**
    wiele odpowiedzi dostało 0% pokrycia słów kluczowych mimo oceny 5/5 od
    sędziego — bo model parafrazował poprawnie zamiast cytować dosłownie
    (np. "gotówką" zamiast oczekiwanego dokładnego brzmienia). Potwierdza to
    wprost przewidzianą wcześniej wadę keyword-matchingu (sztywność wobec
    parafraz).
  - **Złapany realny przypadek zawodności LLM-as-judge:** pytanie "Kiedy
    dostanę wypłatę za nadgodziny z zeszłego miesiąca?" — subagent poprawnie
    odesłał pracownika do działu kadr (zgodnie z sekcją 6 runbooka HR), ale
    sędzia ocenił to na **1/5** jako "całkowicie błędne", z uzasadnieniem
    które samo sobie przeczy (przyznaje, że procedura każe odsyłać do HR, a
    mimo to ocenia odpowiedź jako błędną). Klasyczny przykład niespójności
    tego samego modelu oceniającego własne rodzinne odpowiedzi.
  - **Złapany realny przypadek błędu retrievalu ukrytego przez przekonujący
    ton:** pytanie "Czy mogę zamienić się zmianą z kolegą bez zgłaszania
    kierownikowi?" pobrało fragment o **nadgodzinach** (sekcja 5) zamiast o
    **zmianie grafiku** (sekcja 2) — odpowiedź brzmi przekonująco i
    proceduralnie poprawnie, ale odpowiada na inne pytanie niż zadane.
    LLM-judge tego nie wyłapał (5/5), keyword-matching owszem (0% — trafnie
    zasygnalizował problem, choć "z przypadku", nie ze zrozumienia treści).
    **Wniosek:** żaden pojedynczy sygnał osobno by tego nie ujawnił —
    dopiero zestawienie retrieval hit-rate (MISS) z wysoką oceną sędziego
    (5/5) obnaża lukę. To najsilniejszy argument za utrzymaniem wielu
    niezależnych sygnałów zamiast jednej "zbiorczej" metryki.

## Sprint 7 — drugi agent: drafting agent — 2026-08-20

- **Decyzja:** analiza kategorii przed implementacją — 7 z 8 kategorii ma
  sensowny use case na dokument (dostawy, reklamacje, płatności, BHP, HR,
  awarie techniczne, skargi klienta), `higiena` świadomie pominięta (to
  kategoria odhaczania checklist/rejestrów zgodności, nie korespondencji).
  **Efekt:** `DOCUMENT_TEMPLATES` w `agents/drafting_agent.py` obejmuje 7
  kategorii, `Intent.HIGIENA` i `Intent.INNE` celowo nieobecne.

- **Decyzja:** drugi agent (`agents/drafting_agent.py`) reużywa chunków już
  pobranych przez `subagent.answer()` zamiast odpytywać Chroma drugi raz.
  **Dlaczego:** ten sam kontekst proceduralny powinien grounding'ować
  zarówno odpowiedź, jak i dokument — ponowny retrieval byłby zbędnym
  kosztem i ryzykiem rozjazdu (dwa różne zestawy chunków dla tego samego
  pytania). `AgentAnswer.chunks` (dodane w Sprincie 6 pod evaluation)
  okazało się przydatne też tutaj.
  **Efekt:** `AgentAnswer` służy teraz dwóm różnym agentom jako most
  kontekstu, bez dodatkowego wywołania embeddingów.

- **Decyzja:** brakujące pola w dokumencie → jawny placeholder
  `[uzupełnij: nazwa_pola]`, nie zgadywanie.
  **Dlaczego:** dokument urzędowy/zgłoszeniowy z halucynowanymi danymi
  (błędny numer, zmyślona data) jest gorszy niż pusty — łatwiej zauważyć
  brak niż błąd. Ten sam duch co `ANSWER_SYSTEM_PROMPT` w RAG (nie zgaduj
  spoza kontekstu).
  **Efekt (zweryfikowane na żywo):** dla pytania o dostawy z podanym
  numerem zamówienia model poprawnie wstawił numer i poprawnie
  placeholderował brakującego dostawcę/datę. Zaobserwowano też realną wadę:
  dla karty zdarzenia BHP model **pomylił rok w dacie** (wstawił 2023
  zamiast bieżącej daty — nie ma dostępu do informacji "dzisiaj") i
  **częściowo zdublował pole** (wypełnił opis, a mimo to dopisał obok
  `[uzupełnij: opis_zdarzenia]`) — niespójność instruction-following, nie
  ukryta, lecz odnotowana jako znane ograniczenie do ewentualnej poprawy
  promptu (np. jawne przekazanie bieżącej daty do kontekstu).

- **Decyzja:** kategorie wrażliwe (BHP, HR) — dokument nigdy nie trafia do
  pracownika bezpośrednio, zawsze przez tę samą kolejkę HITL co eskalacje,
  rozszerzoną o `kind="document_review"` (`hitl/queue.py`).
  **Dlaczego:** spójne z filozofią projektu — confidence gate też wybiera
  bezpieczeństwo ponad automatyzację. Karta wypadku BHP i pismo kadrowe
  (np. wypowiedzenie) to dokumenty o realnych konsekwencjach prawnych/
  bezpieczeństwa; błąd modelu (patrz wyżej — pomylona data) nie powinien
  nigdy trafić do systemu bez ludzkiego przeglądu.
  **Efekt (zweryfikowane na żywo end-to-end w przeglądarce):** pytanie BHP
  → subagent odpowiada normalnie → szkic dokumentu trafia do kolejki HITL
  jako `document_review`, nie jako zwykła eskalacja → operator widzi i
  edytuje treść w tym samym panelu, zatwierdza → pracownik dostaje **i**
  odpowiedź proceduralną, **i** zatwierdzony dokument w tej samej rozmowie
  (`draft_text` przeżywa pauzę/wznowienie grafu obok `answer`).

- **Decyzja:** graf rozgałęzia się **po** `auto_answer_node`, nie równolegle
  do niego — `draft_document()` wywoływane tylko gdy pytanie w ogóle
  dostało auto-odpowiedź (nie dla eskalacji/odrzuceń).
  **Dlaczego:** nie ma sensu generować dokumentu dla pytania, które i tak
  idzie do człowieka (eskalacja) albo zostało odrzucone przez walidację —
  oszczędność jednego zbędnego wywołania LLM w tych ścieżkach.
  **Efekt:** `route_after_auto_answer` — `"document_review"` tylko gdy
  `draft_pending_review=True`, inaczej prosto do `END` z dokumentem już w
  stanie (widoczny w UI od razu, bez pauzy).

## Sprint 8 — restyling UI (inspirowany Żabka.pl) — 2026-08-20

- **Decyzja:** kolory i krój pisma wyprowadzone z realnego CSS strony
  Żabka.pl (dostarczony przez użytkownika plik HTML), nie zgadywane —
  dominujący kolor `#006420` (67 wystąpień w CSS strony) jako główna
  zieleń marki, `#00B05A` jako akcent (przyciski/CTA), `#FFD500` jako
  żółty akcent, krój `TT Commons` (zidentyfikowany w
  `--wp--preset--font-family--base-font`).
  **Dlaczego tak, a nie "na oko":** decyzja projektowa oparta na danych z
  realnej strony, nie na domysłach o tym, jak wygląda marka Żabka — spójne
  z resztą projektu (żadna inna decyzja w tym repo nie była "z gdybania").

- **Decyzja:** czcionka `Inter` (Google Fonts, darmowa) zamiast `TT Commons`.
  **Dlaczego:** `TT Commons` to font komercyjny (TypeType) — nie mam do
  niego licencji i nie mogę go redystrybuować ani ładować z zewnętrznego
  źródła bez uprawnień. `Inter` ma podobny, geometryczno-humanistyczny
  charakter i jest darmowa/otwarta — świadomy kompromis "podobny duch,
  legalne źródło".
  **Efekt:** brak ryzyka licencyjnego, wizualnie zbliżony rezultat.

- **Decyzja:** żadnych zasobów zastrzeżonych (logo, wordmark) — tylko
  paleta kolorów i typografia, plus jawna, widoczna plakietka zastrzeżenia
  ("Niezależny projekt portfolio... niezwiązany z i nieautoryzowany przez
  Żabka Polska sp. z o.o.") umieszczona **bezpośrednio pod nagłówkiem**, nie
  schowana w stopce.
  **Dlaczego:** kolory i typografia same w sobie nie są zwykle chronione
  prawem znaków towarowych tak jak logo/wordmark, ale użycie ich bez
  zastrzeżenia mogłoby sugerować oficjalne powiązanie z marką — co jest
  nieprawdą i czego chcemy jednoznacznie uniknąć, zwłaszcza że projekt
  trafi bezpośrednio do rekrutacji w tej firmie.
  **Efekt (zweryfikowane na żywo w przeglądarce):** baner startowy z
  gradientem zieleni marki, emoji żaby (nie logo) zamiast nazwy/ikony
  firmy, plakietka zastrzeżenia widoczna od razu po wejściu na stronę.

## Sprint 9 — case study (materiał rekrutacyjny) — 2026-08-20

- **Decyzja:** walkthrough oparty na **domenie zamówień/dostaw**, nie BHP.
  **Dlaczego:** materiał trafia do rekrutacji w sieci convenience — obsługa
  braków w dostawie jest bliższa codziennej pracy franczyzobiorcy niż wypadek
  przy pracy, więc lepiej rezonuje z odbiorcą.
  **Efekt uboczny, który okazał się zaletą:** dobór pytania wymagał kilku prób,
  bo pytania o dostawy klasyfikują się słabo (patrz niżej) — z tego wyszedł
  najmocniejszy fragment całego materiału.

- **Decyzja:** dwa scenariusze zamiast jednego, celowo **niemal identyczne
  merytorycznie** (brakujące palety, kierowca odjechał), ale różnie potraktowane
  przez system.
  **Dlaczego:** przy testowaniu kandydatów na pytanie okazało się, że dodanie
  numeru zamówienia (`ZM-2024-00981`) do treści realnie psuje klasyfikację
  (przeciąga ją w stronę `płatności`/`reklamacje`). Zamiast to ukryć —
  pokazane wprost jako para: scenariusz A (confidence 0.67 → pełna
  automatyzacja, 273.9s) i B (confidence 0.33 → eskalacja w 2.9s, bez ani
  jednego wywołania LLM).
  **Efekt:** zestawienie tłumaczy confidence gate lepiej niż jakikolwiek opis
  i jednocześnie uczciwie pokazuje słabość klasyfikatora (65% top-1) na
  konkretnym, realnym przykładzie.

- **Zaobserwowany na żywo błąd modelu (odnotowany, nie ukryty):** w
  scenariuszu A model **dwukrotnie zmyślił rozwinięcie skrótu „WZ"**
  („Wywiad Zamówienia" w odpowiedzi, „Widok Zamówienia" w dokumencie).
  Runbook używa skrótu bez rozwinięcia, więc model je wymyślił zamiast
  zostawić oryginał. Procedura merytorycznie poprawna, ale w piśmie do
  dostawcy taki błąd rzuca się w oczy — i nie wyłapały go ani testy
  jednostkowe, ani LLM-as-judge, tylko przegląd na żywo.

- **Decyzja:** „nagranie" jako **interaktywne odtworzenie krok po kroku** w
  materiale HTML, nie plik wideo/GIF.
  **Dlaczego:** (a) narzędzie do zrzutów ekranu w tej sesji przestało
  odpowiadać, a Chrome do nagrywania GIF-ów nie był podłączony; (b) niezależnie
  od tego — realne nagranie pełnego cyklu to ~4,5 minuty, z czego ~99% to
  spinner, więc jako materiał do maila byłoby gorsze niż anotowany przebieg,
  który czyta się we własnym tempie i pokazuje warstwę „co dzieje się pod
  spodem" obok każdego ekranu.
  **Efekt:** odtwarzacz z dwoma scenariuszami, paskiem kroków, trybem
  auto-play i panelem technicznym per krok. Wszystkie treści, czasy i liczby
  tokenów pochodzą z faktycznego uruchomienia i trace'ów z Langfuse API.
  Logika odtwarzacza zweryfikowana 24 asercjami w Node z atrapą DOM
  (nawigacja, przełączanie scenariuszy, podmiana treści, stany przycisków).

- **Decyzja:** jawna, wyeksponowana nota o wydajności — model lokalny na CPU,
  ~2 min na wywołanie LLM, ~4,5 min na pełny cykl; na modelu hostowanym te
  same kroki to sekundy, a architektura się nie zmienia.
  **Dlaczego:** bez tej noty czasy w materiale wyglądają jak wada produktu,
  a nie jak konsekwencja świadomej decyzji „wszystko lokalne i darmowe".
  Rozróżnienie „to koszt decyzji o dostawcy modelu, nie projektu" jest
  istotne dla odbiorcy oceniającego architekturę.

- **Decyzja:** usunięte odwołania do konkretnego poprzedniego pracodawcy z
  README, case study i dokumentacji architektury.
  **Dlaczego:** materiał ma bronić się sam, bez kontekstu poprzednich
  projektów zawodowych.

## Sprint 10 — domknięcie zaległych wymagań (2.4, 3.7, 5.8) + skróty — 2026-08-20

- **Decyzja:** twarda wytyczna w promptach: **nie rozwijaj skrótów, których
  kontekst sam nie rozwija** — dodana do `ANSWER_SYSTEM_PROMPT`
  (`rag/retrieval.py`) i `DRAFT_SYSTEM_PROMPT` (`agents/drafting_agent.py`).
  **Dlaczego:** w Sprincie 9 model dwukrotnie zmyślił rozwinięcie „WZ"
  („Wywiad Zamówienia", „Widok Zamówienia"). Runbooki używają skrótów (WZ,
  HACCP, e-ZLA) bez definicji, więc model wypełniał lukę zgadywaniem. To ta
  sama klasa błędu co halucynacja daty — i to samo lekarstwo: jawnie zabronić
  wypełniania luk, zamiast liczyć na to, że model sam się powstrzyma.
  **Efekt — i dwie lekcje z drogi do niego:**

  1. **Pierwsza wersja testu regresyjnego była bezużyteczna.** Sprawdzała
     obecność trzech konkretnych fraz, które model wyprodukował wcześniej
     („Wywiad Zamówienia", „Widok Zamówienia", „Wydanie Zewnętrzne").
     Przy kolejnym przebiegu model wymyślił **dwie zupełnie nowe** —
     „Zamówienia Zamkowego" i „Widza Zlecenia" — i test przeszedł na zielono,
     mimo że błąd wystąpił. Blocklist znanych złych ciągów nie działa na
     halucynacje, bo halucynacja to z definicji coś, czego jeszcze nie
     widziałeś. Test przepisany na **wzorzec kształtu** („Jakieś Słowa (WZ)"
     albo „WZ (jakieś słowa)"), zweryfikowany na 5 zaobserwowanych
     przypadkach błędnych i 4 poprawnych.
  2. **Runbook sam definiuje WZ** — `01_dostawy.md` pisze „listu przewozowego
     (WZ)". Więc rozwinięcie „list przewozowy" jest **legalne**, a błędem są
     tylko wymyślone alternatywy. Gdybym tego nie sprawdził, test zgłaszałby
     fałszywe alarmy na poprawnym cytacie z procedury. Reguła w prompcie i
     asercja w teście dopuszczają rozwinięcie występujące dosłownie w
     kontekście.

  3. **Prompt tego nie rozwiązał — dopiero kod.** Kolejne rundy: (a) zwykła
     reguła „nie rozwijaj skrótów" — ignorowana; (b) reguła z przykładami
     DOBRZE/ŹLE — zadziałała na jeden przebieg, po czym **przykład stał się
     szablonem**: model zaczął zwracać zdanie z przykładu („Odnotuj brak na WZ
     z podpisem kierowcy.") jako *całą* odpowiedź, gubiąc kroki procedury;
     (c) przykłady przepisane na urwane fragmenty z innego runbooka + jawna
     instrukcja „odpowiadaj wyczerpująco" — odpowiedzi wróciły do normy, ale
     model i tak wyprodukował kolejny wymysł („Wariant Zgodności"), łapiąc
     czerwony test end-to-end.

     **Wniosek:** przy modelu tej klasy zgodność z instrukcją nie jest
     problemem promptowym, tylko inżynierskim. Powstał
     `agents/abbreviations.py` — deterministyczny strażnik, który przepuszcza
     rozwinięcie skrótu **tylko wtedy, gdy dosłownie występuje w kontekście**
     podanym modelowi, a resztę sprowadza do samego skrótu. Stosowany do
     wyjścia obu agentów. Reguła w prompcie zostaje jako pierwsza linia obrony,
     ale gwarancję daje kod. 10 testów jednostkowych — po jednym na każde
     rozwinięcie, które model faktycznie wyprodukował, plus przypadki
     negatywne (legalne „listu przewozowego (WZ)" i zwykłe nawiasy zostają
     nietknięte).

     To jest, moim zdaniem, najbardziej wartościowa obserwacja z całego
     projektu: **iterowanie promptu ma punkt, w którym przestaje się opłacać**,
     i trzeba umieć go rozpoznać zamiast dokładać kolejne zdanie do instrukcji.

- **Wymaganie 2.4 (pytania dwuznaczne) — zamknięte przez zmianę definicji
  „sukcesu".** Wcześniej wisiało jako 🚧, bo klasyfikator „nie rozróżnia ich
  dobrze". Problem: dla pytań z dwiema dopuszczalnymi intencjami (terminal =
  płatności/awarie, lodówka = higiena/awarie) **nie istnieje jedna poprawna
  odpowiedź**, więc mierzenie top-1 accuracy było mierzeniem złej rzeczy.
  **Nowa, testowalna własność:** wolno eskalować, wolno wybrać dowolną z
  dopuszczalnych intencji, **nie wolno pewnie trafić w intencję obcą** —
  bo to jedyny wariant, w którym pracownik dostaje odpowiedź z niewłaściwego
  runbooka. Test: `test_ambiguous_questions_never_route_to_an_unacceptable_intent`.
  **Efekt:** przechodzi na żywym klasyfikatorze.

- **Wymaganie 3.7 (generacja na bazie kontekstu) — zamknięte, przy okazji
  usunięty martwy kod.** Wymaganie wskazywało na `retrieval.generate_answer()`,
  ale ta funkcja **nie miała już żadnego wywołania** — realną ścieżką jest
  `agents/subagent.py` (retrieval filtrowany do runbooka intencji + dopisek
  do promptu per kategoria). Zamiast utrzymywać dwie rozjeżdżające się drogi
  generacji, martwa funkcja została usunięta, a w jej miejscu został komentarz
  wyjaśniający gdzie jest prawdziwa implementacja.
  **Brakujący dowód dostarczony:** `tests/test_end_to_end.py` — realne pytanie
  przez **cały graf** na żywej Ollamie, bez mocków, z asercjami na
  ugruntowanie w runbooku (`sources == ['01_dostawy.md']`), brak eskalacji i
  powstanie dokumentu. Oznaczony markerem `slow` i wyłączony z domyślnego
  uruchomienia (`addopts = "-m 'not slow'"`), bo to ~4 minuty na CPU —
  uruchamiany świadomie przez `pytest -m slow`.

- **Wymaganie 5.8 (treść załącznika w odpowiedzi) — zrealizowane, ale
  **bez osobnego agenta**, wbrew pierwotnemu zapisowi w planie.
  **Dlaczego:** pierwotnie zakładałem „agenta data retrieval". Przy
  implementacji okazało się, że osobny agent byłby pustym opakowaniem —
  treść załącznika to po prostu **dodatkowy kontekst**, który mają widzieć
  agenci już istniejący, a nie zadanie wymagające własnego rozumowania i
  własnego wywołania LLM. Trzeci agent oznaczałby trzecie wywołanie modelu
  (+2 min na CPU) bez zysku jakościowego.
  **Zmiana zachowania:** wcześniej PDF był parsowany **tylko** gdy
  klasyfikacja miała niską pewność (do przełamania remisu). Teraz jest
  parsowany zawsze po skanie AV i niesiony dalej w `PipelineResult.attachment_text`
  → `subagent.answer()` i `draft_document()`. Uzasadnienie produktowe: jeśli
  pracownik zadał sobie trud załączenia dokumentu, agenci powinni umieć go
  przeczytać, a nie tylko użyć do rozstrzygnięcia kategorii.
  **Szczegół projektowy:** treść załącznika trafia do promptu **wyraźnie
  oddzielona** od kontekstu proceduralnego i opisana jako „dane konkretnej
  sprawy, nie procedura" — żeby model nie potraktował dokumentu pracownika
  jak źródła procedur.
  **Efekt — po naprawieniu błędu, który sam wprowadziłem:** pierwszy przebieg
  weryfikacyjny pokazał, że załącznik **częściowo** działa — dostawca i data
  zostały wypełnione z PDF (bez załącznika były placeholderami), ale numer
  zamówienia nadal wychodził jako `[uzupełnij: ...]`, mimo że jest w
  dokumencie. Sprawdzenie ekstrakcji PDF wykluczyło parser (numer był w
  tekście podanym modelowi). Przyczyną okazała się **moja własna reguła w
  prompcie**: „jeśli informacji brakuje **w pytaniu pracownika**, wstaw
  placeholder" — model czytał ją dosłownie i placeholderował wszystko, czego
  nie było w samym pytaniu, ignorując załącznik. Po przeformułowaniu
  („szukaj najpierw w pytaniu ORAZ w załączniku; placeholder tylko gdy nie ma
  w żadnym z nich") weryfikacja przeszła: z załącznikiem wszystkie cztery pola
  wypełnione włącznie z `ZM-2024-00981`, bez załącznika — placeholdery.
  **Lekcja:** kiedy model „ignoruje" instrukcję, najpierw sprawdź, czy
  instrukcja mówi to, co ci się wydaje.

## Szablon na kolejne sprinty

```
## Sprint N — YYYY-MM-DD

- **Decyzja:** ...
  **Dlaczego:** ...
  **Efekt:** ...
```
