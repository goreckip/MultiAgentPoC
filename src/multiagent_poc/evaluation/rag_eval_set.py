"""Ground truth for RAG retrieval + answer quality, derived by hand from the
actual runbook text (docs/runbooks/*.md) — not guessed. Covers the 15
questions from classification/eval_set.py that have an in-catalog answer
(the other 5 are escalate-only and never reach a subagent).

Deliberately bypasses the classifier: each entry pins the *correct* intent,
so scripts/evaluate_rag.py tests retrieval+generation quality in isolation
from classifier accuracy (already evaluated separately in Week 3). For the
three questions with two acceptable intents in eval_set.py (ambiguous
by design), `intent` picks one as the primary target to evaluate against —
noted per entry.

`expected_heading_substring`: retrieval hit = did any retrieved chunk's
heading_path contain this string. `expected_keywords`: answer quality =
fraction of these substrings (case-insensitive) present in the generated
answer text.
"""

from dataclasses import dataclass

from multiagent_poc.intents import Intent


@dataclass
class RagGroundTruth:
    question: str
    intent: Intent
    expected_source: str
    expected_heading_substring: str
    expected_keywords: list[str]
    note: str = ""


RAG_EVAL_SET: list[RagGroundTruth] = [
    RagGroundTruth(
        "Dostawca przywiózł inny towar niż zamówiony, kierowca już odjechał, co robię?",
        Intent.DOSTAWY, "01_dostawy.md", "4.3",
        ["magazynować oddzielnie", "5 dni roboczych"],
    ),
    RagGroundTruth(
        "Klient reklamuje jogurt, twierdzi że był po terminie — co mam zrobić?",
        Intent.REKLAMACJE, "02_reklamacje.md", "3.1",
        ["zwrot", "od razu"],
    ),
    RagGroundTruth(
        "Terminal płatniczy nie łączy się z bankiem, co teraz?",
        Intent.PLATNOSCI, "03_platnosci_kasa.md", "4",
        ["wsparcia technicznego", "gotówk"],
        note="dwuznaczne w eval_set.py (też awarie_techniczne) — tu testowane jako platnosci",
    ),
    RagGroundTruth(
        "Brakuje mi 21 zł w kasie na zamknięciu zmiany.",
        Intent.PLATNOSCI, "03_platnosci_kasa.md", "5",
        ["pisemne wyjaśnienie", "podpis kierownika"],
    ),
    RagGroundTruth(
        "Brakuje mi 20 zł w kasie na zamknięciu zmiany.",
        Intent.PLATNOSCI, "03_platnosci_kasa.md", "5",
        ["notatka", "bez dalszej eskalacji"],
    ),
    RagGroundTruth(
        "Pracownik poparzył się podczas czyszczenia grilla, co robimy?",
        Intent.BHP, "04_bhp.md", "3",
        ["pierwszej pomocy", "kart", "30 minut"],
    ),
    RagGroundTruth(
        "Skaleczenie palca nożem, niewielkie, czy to już wypadek do zgłoszenia?",
        Intent.BHP, "04_bhp.md", "3",
        ["30 minut", "zgłosz"],
    ),
    RagGroundTruth(
        "Czy mogę zamienić się zmianą z kolegą bez zgłaszania kierownikowi?",
        Intent.HR, "05_hr_grafiki.md", "2",
        ["akceptacji kierownika"],
    ),
    RagGroundTruth(
        "Kiedy dostanę wypłatę za nadgodziny z zeszłego miesiąca?",
        Intent.HR, "05_hr_grafiki.md", "5",
        ["czasem wolnym", "regulamin"],
    ),
    RagGroundTruth(
        "Lodówka z nabiałem pokazuje 8 stopni, co robię z towarem i co robię z lodówką?",
        Intent.HIGIENA, "06_higiena_sanepid.md", "2",
        ["wstrzymane do sprzedaży", "awarii technicznej"],
        note="dwuznaczne w eval_set.py (też awarie_techniczne) — tu testowane jako higiena",
    ),
    RagGroundTruth(
        "Sanepid zapowiedział kontrolę na jutro, na co mam zwrócić uwagę?",
        Intent.HIGIENA, "06_higiena_sanepid.md", "6",
        ["wezwać kierownika", "HACCP"],
    ),
    RagGroundTruth(
        "Klient krzyczy przy kasie i grozi, że wróci z prawnikiem — co robię?",
        Intent.SKARGI_KLIENTA, "08_obsluga_klienta_skargi.md", "6",
        ["przerwać obsługę", "kierownika"],
    ),
    RagGroundTruth(
        "Klient żąda zwrotu pieniędzy za produkt, którego nie mamy w asortymencie od miesięcy.",
        Intent.REKLAMACJE, "02_reklamacje.md", "",
        ["zarejestr"],
        note="celowo dwuznaczne/trudne w eval_set.py — słabe ground truth, niska waga w interpretacji wyników",
    ),
    RagGroundTruth(
        "Mój numer zamówienia to ZM-2024-00981, dostawa nie doszła, co robię?",
        Intent.DOSTAWY, "01_dostawy.md", "2",
        ["zgłosz", "formularz"],
    ),
    RagGroundTruth(
        "Mój numer zamówienia to abc123, dostawa nie doszła, co robię?",
        Intent.DOSTAWY, "01_dostawy.md", "2",
        ["zgłosz", "formularz"],
        note="format numeru zamówienia niepoprawny — to sprawa warstwy walidacji (5.2), nie RAG; oczekiwana treść odpowiedzi identyczna jak wyżej",
    ),
]
