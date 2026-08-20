"""Deterministic guard against invented abbreviation expansions.

Why this exists as code and not just a prompt rule: the runbooks use bare
abbreviations (WZ, HACCP, e-ZLA, FIFO) and llama3.1:8b keeps filling that gap
by inventing an expansion. Three rounds of prompt work each held for a run or
two, then produced a brand-new wording — "Wywiad Zamówienia", "Widok
Zamówienia", "Zamówienia Zamkowego", "Widza Zlecenia", "Wariant Zgodności".
At that point the honest conclusion is that a model this size will not comply
reliably, so compliance stops being a prompting problem and becomes a
post-processing one.

The rule enforced here: an expansion may stand only if it literally appears
in the context the model was given. Anything else is stripped down to the
bare abbreviation, which is always safe — the runbook itself writes it that
way. The prompt rule stays in place as a first line of defence; this is the
net underneath it.
"""

import re

# "Jakieś Słowa (WZ)" — expansion before the abbreviation.
_BEFORE = re.compile(r"((?:[\wąćęłńóśźż]+\s+){0,2}[\wąćęłńóśźż]+)\s*\(\s*([A-ZŁŚŻŹĆÓĄĘŃ]{2,6})\s*\)")
# "WZ (jakieś słowa)" — expansion after it.
_AFTER = re.compile(r"\b([A-ZŁŚŻŹĆÓĄĘŃ]{2,6})\s*\(\s*([^)]{4,}?)\s*\)")


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).casefold()


def strip_invented_expansions(text: str, context: str) -> str:
    """Removes abbreviation expansions that don't occur in `context`.

    Keeps expansions the source material actually uses — 01_dostawy.md writes
    "listu przewozowego (WZ)", so that one survives untouched.
    """
    if not text:
        return text

    normalized_context = _normalize(context)

    def drop_before(match: re.Match) -> str:
        expansion, abbr = match.group(1), match.group(2)
        if _normalize(expansion) in normalized_context:
            return match.group(0)
        return abbr

    def drop_after(match: re.Match) -> str:
        abbr, expansion = match.group(1), match.group(2)
        if _normalize(expansion) in normalized_context:
            return match.group(0)
        return abbr

    return _AFTER.sub(drop_after, _BEFORE.sub(drop_before, text))
