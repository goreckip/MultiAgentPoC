"""Every "invented" case below is a real wording llama3.1:8b produced during
development — the guard exists because prompt rules alone didn't stop them.
"""

import pytest

from multiagent_poc.agents.abbreviations import strip_invented_expansions

RUNBOOK_CONTEXT = (
    "Przed podpisaniem listu przewozowego (WZ) należy sprawdzić liczbę palet. "
    "Porównać ilości pozycji na WZ z rzeczywistą zawartością. "
    "Dokumentacja HACCP przechowywana jest minimum 12 miesięcy."
)


@pytest.mark.parametrize(
    "invented",
    [
        "Odnotuj brak na WZ (Wywiad Zamówienia) z podpisem kierowcy.",
        "Brakuje palet względem Widoku Zamówienia (WZ).",
        "Brak dwóch palet względem Widza Zlecenia (WZ)",
        "Brakuje 2 palet względem Zamówienia Zamkowego (WZ).",
        "Sprawdź WZ (Wariant Zgodności) przed podpisem.",
        "Zgodnie z kartą HACCP (Analiza Zagrożeń i Krytycznych Punktów).",
    ],
)
def test_invented_expansion_is_stripped_to_the_bare_abbreviation(invented):
    cleaned = strip_invented_expansions(invented, RUNBOOK_CONTEXT)

    assert "(" not in cleaned or "przewozow" in cleaned.lower()
    for word in ("Wywiad", "Widok", "Widza", "Zamkowego", "Wariant", "Analiza"):
        assert word not in cleaned, f"invented fragment survived: {cleaned}"


def test_expansion_present_in_context_is_preserved():
    """01_dostawy.md itself writes "listu przewozowego (WZ)" — that expansion is
    legitimate and must survive, otherwise the guard would mangle a correct
    quote from the procedure.
    """
    text = "Przed podpisaniem listu przewozowego (WZ) sprawdź liczbę palet."

    assert strip_invented_expansions(text, RUNBOOK_CONTEXT) == text


def test_bare_abbreviation_is_left_alone():
    text = "Odnotuj brak na WZ z podpisem kierowcy i zgłoś w ciągu 24 h."

    assert strip_invented_expansions(text, RUNBOOK_CONTEXT) == text


def test_ordinary_parentheses_are_not_touched():
    text = "Zgłoś rozbieżność (najlepiej tego samego dnia) przez system."

    assert strip_invented_expansions(text, RUNBOOK_CONTEXT) == text


def test_handles_empty_input():
    assert strip_invented_expansions("", RUNBOOK_CONTEXT) == ""
