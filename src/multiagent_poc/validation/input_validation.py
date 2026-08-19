"""Input validation for the raw question text — runs before classification
(see sequence_diagram.md: "Walidacja przed klasyfikacją, nie po").

Heuristic, regex/keyword-based checks — not a general-purpose DLP system.
Scoped to what docs/test_questions.md actually exercises (questions 16-20):
PESEL detection, prompt injection, third-party personal data requests, and
order-number format normalization. Two different outcomes:

- allowed=False: question never reaches the classifier or LLM (PESEL,
  prompt injection, third-party data requests — always a hard reject).
- allowed=True with flags: question proceeds, but callers can act on the
  flag (e.g. order number format looks wrong — dostawy questions 17/18 in
  the eval set are still expected to classify fine, just with a flag noted).
"""

from dataclasses import dataclass, field
import re

_PESEL_RE = re.compile(r"\b\d{11}\b")

_PESEL_WEIGHTS = [1, 3, 7, 9, 1, 3, 7, 9, 1, 3]


def _is_valid_pesel_checksum(digits: str) -> bool:
    checksum = sum(int(d) * w for d, w in zip(digits[:10], _PESEL_WEIGHTS)) % 10
    control_digit = (10 - checksum) % 10
    return control_digit == int(digits[10])


def _detect_pesel(text: str) -> bool:
    return any(_is_valid_pesel_checksum(m) for m in _PESEL_RE.findall(text))


_PROMPT_INJECTION_PATTERNS = [
    r"ignoruj\s+(poprzedni|wcześniejsz)",
    r"zapomnij\s+o\s+instrukcj",
    r"poda[jć]\s+has[łl]o",
    r"jesteś\s+teraz",
    r"dzia[łl]aj\s+jako",
    r"system\s*prompt",
    r"jailbreak",
]
_PROMPT_INJECTION_RE = re.compile("|".join(_PROMPT_INJECTION_PATTERNS), re.IGNORECASE)


def _detect_prompt_injection(text: str) -> bool:
    return bool(_PROMPT_INJECTION_RE.search(text))


_SALARY_KEYWORDS_RE = re.compile(r"ile\s+zarabia|jakie\s+wynagrodzenie|wysokoś[cć]\s+pensji", re.IGNORECASE)
_THIRD_PARTY_ROLE_RE = re.compile(
    r"kierowni[kc]|koleg\w*|pracowni[kc]\w*|dyrektor\w*|prze[łl]ożon\w*", re.IGNORECASE
)


def _detect_third_party_data_request(text: str) -> bool:
    return bool(_SALARY_KEYWORDS_RE.search(text)) and bool(_THIRD_PARTY_ROLE_RE.search(text))


_ORDER_NUMBER_MENTION_RE = re.compile(r"numer\s+zam[oó]wienia\s+(?:to\s+)?([A-Za-z0-9\-]+)", re.IGNORECASE)
_ORDER_NUMBER_FORMAT_RE = re.compile(r"^[A-Z]{2}-\d{4}-\d{5}$")


def _check_order_number_format(text: str) -> list[str]:
    match = _ORDER_NUMBER_MENTION_RE.search(text)
    if match and not _ORDER_NUMBER_FORMAT_RE.match(match.group(1).upper()):
        return ["order_number_invalid_format"]
    return []


class ValidationRejected(Exception):
    """Raised when the raw question must never reach the classifier or LLM."""


@dataclass
class ValidationResult:
    allowed: bool
    reason: str | None = None
    flags: list[str] = field(default_factory=list)


def validate_input(question: str) -> ValidationResult:
    if _detect_pesel(question):
        return ValidationResult(allowed=False, reason="pytanie zawiera numer PESEL (dane wrażliwe)")

    if _detect_prompt_injection(question):
        return ValidationResult(allowed=False, reason="wykryto próbę prompt injection")

    if _detect_third_party_data_request(question):
        return ValidationResult(
            allowed=False, reason="pytanie dotyczy danych osobowych/wynagrodzenia innej osoby"
        )

    return ValidationResult(allowed=True, flags=_check_order_number_format(question))
