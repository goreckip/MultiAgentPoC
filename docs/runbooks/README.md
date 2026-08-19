# Mockowe runbooki — Retail Ops Assistant

Zestaw 8 fikcyjnych dokumentów proceduralnych do RAG. Kontekst: sieć convenience store,
zbliżony realiami do franczyzy typu Żabka — celowo, na potrzeby STAR na rozmowie.

## Katalog intencji → dokument źródłowy

| # | Intencja | Plik | Uwagi |
|---|----------|------|-------|
| 1 | dostawy | `01_dostawy.md` | odbiór towaru, braki, uszkodzenia, pomyłki dostawcy |
| 2 | reklamacje | `02_reklamacje.md` | reklamacje klientów, produkty spoż. i niespoż. |
| 3 | płatności | `03_platnosci_kasa.md` | kasa, terminal, rozbieżności kasowe |
| 4 | BHP | `04_bhp.md` | wypadki przy pracy, urządzenia, chemikalia |
| 5 | HR | `05_hr_grafiki.md` | grafiki, urlopy, nadgodziny, wynagrodzenie |
| 6 | higiena | `06_higiena_sanepid.md` | HACCP, temperatury, kontrola sanepidu |
| 7 | awarie techniczne | `07_awarie_techniczne.md` | kasa fiskalna, lodówki, internet, terminal |
| 8 | skargi klienta | `08_obsluga_klienta_skargi.md` | trudny klient, spory cenowe, agresja |
| 9 | **inne** | *(brak dokumentu — celowo)* | fallback: pytania spoza katalogu → eskalacja do człowieka, nie RAG |

Kategoria 9 ("inne") jest celowo pusta — to test Twojego confidence gate. System
powinien rozpoznać niską pewność klasyfikacji / brak trafnych chunków i eskalować,
zamiast halucynować odpowiedź na bazie najbliższego tematycznie dokumentu.

## Struktura dokumentów (pod testy chunkingu)

Każdy plik ma jednolitą strukturę:
- `## 1. Zakres procedury` — zawsze pierwsza sekcja, dobra pod test "czy chunking po
  nagłówkach faktycznie wyciąga sensowne, samodzielne fragmenty".
- Kolejne sekcje `## N. ...`, część z podsekcjami `### N.1`.
- Ostatnia sekcja to zwykle eskalacja/kontakt — dobry test na pytania graniczne
  typu "kiedy mam to zgłosić wyżej", które wymagają połączenia kontekstu z kilku sekcji.

Sugerowany eksperyment z planu (tydzień 2): porównaj retrieval dla pytania w stylu
*"dostawca przywiózł inny towar niż zamówiony, kierowca już odjechał, co robię?"*
między chunkingiem fixed-size (np. 500 znaków, overlap 50) a chunkingiem po `##`/`###`.
Ten konkretny przypadek (sekcja 4.3 w `01_dostawy.md`) jest krótki i osadzony w
kontekście sekcji nadrzędnej — dobry kandydat na pokazanie różnicy w jakości retrievalu.

## Celowe pułapki w treści (do testów konfliktów/edge case'ów)

- Zazębiające się kategorie: awaria lodówki dotyczy zarówno `07_awarie_techniczne.md`
  (zgłoszenie serwisowe) jak i `06_higiena_sanepid.md` (co zrobić z towarem) —
  dobry test dla routingu multi-agentowego i dla tego, czy subagent wie kiedy
  przekazać pytanie dalej zamiast odpowiadać niepełnie.
- Pytania na granicy dwóch progów kwotowych/czasowych (np. rozbieżność kasowa 20 zł
  vs 21 zł, wypadek "drobny" vs wymagający interwencji medycznej) — dobry test
  confidence gate i precyzji odpowiedzi z RAG.
- Sekcje "Czego NIE robimy" (`02_reklamacje.md`) — sprawdzają, czy model nie
  ignoruje negatywnych instrukcji przy generacji odpowiedzi.

## Do zrobienia dalej (zgodnie z planem, tydzień 1)

- [ ] Zdefiniować finalny katalog intencji w kodzie (JSON/enum) — ta tabela jako punkt wyjścia.
- [ ] Przygotować 15–20 pytań testowych (w tym kilka celowo dwuznacznych i kilka
      spoza katalogu, kategoria "inne") na testy z tygodnia 3.
- [ ] Zdecydować o embeddingu do klasyfikacji intencji (lokalny przez Ollama vs. lekki
      model klasyfikujący) — do logu decyzji.
