"""Intent catalog for the Retail Ops Assistant.

Source of truth: docs/runbooks/README.md. Category 9 ("inne") has no backing
runbook by design — it is the confidence-gate fallback path, not a RAG target.
"""

from enum import Enum
from pathlib import Path

RUNBOOKS_DIR = Path(__file__).resolve().parents[2] / "docs" / "runbooks"


class Intent(str, Enum):
    DOSTAWY = "dostawy"
    REKLAMACJE = "reklamacje"
    PLATNOSCI = "platnosci"
    BHP = "bhp"
    HR = "hr"
    HIGIENA = "higiena"
    AWARIE_TECHNICZNE = "awarie_techniczne"
    SKARGI_KLIENTA = "skargi_klienta"
    INNE = "inne"  # no runbook — always routed to human escalation


INTENT_RUNBOOK_MAP: dict[Intent, str | None] = {
    Intent.DOSTAWY: "01_dostawy.md",
    Intent.REKLAMACJE: "02_reklamacje.md",
    Intent.PLATNOSCI: "03_platnosci_kasa.md",
    Intent.BHP: "04_bhp.md",
    Intent.HR: "05_hr_grafiki.md",
    Intent.HIGIENA: "06_higiena_sanepid.md",
    Intent.AWARIE_TECHNICZNE: "07_awarie_techniczne.md",
    Intent.SKARGI_KLIENTA: "08_obsluga_klienta_skargi.md",
    Intent.INNE: None,
}

INTENT_DESCRIPTIONS: dict[Intent, str] = {
    Intent.DOSTAWY: "odbiór towaru, braki, uszkodzenia, pomyłki dostawcy",
    Intent.REKLAMACJE: "reklamacje klientów, produkty spożywcze i niespożywcze",
    Intent.PLATNOSCI: "kasa, terminal, rozbieżności kasowe",
    Intent.BHP: "wypadki przy pracy, urządzenia, chemikalia",
    Intent.HR: "grafiki, urlopy, nadgodziny, wynagrodzenie",
    Intent.HIGIENA: "HACCP, temperatury, kontrola sanepidu",
    Intent.AWARIE_TECHNICZNE: "kasa fiskalna, lodówki, internet, terminal",
    Intent.SKARGI_KLIENTA: "trudny klient, spory cenowe, agresja",
    Intent.INNE: "pytania spoza katalogu — eskalacja do człowieka, nigdy RAG",
}


def runbook_path(intent: Intent) -> Path | None:
    filename = INTENT_RUNBOOK_MAP[intent]
    return RUNBOOKS_DIR / filename if filename else None
