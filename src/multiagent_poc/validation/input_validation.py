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

from multiagent_poc.observability.langfuse_client import observe

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


@observe(name="validate_input")
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


REDACTION = "[dane wrażliwe usunięte]"


def redact_sensitive(text: str) -> tuple[str, list[str]]:
    """Replaces validated PESEL numbers with a marker, returning the flags raised.

    Used for attachment text rather than rejection, see validate_attachment_text.
    """
    flags: list[str] = []

    def replace(match: re.Match) -> str:
        if _is_valid_pesel_checksum(match.group(0)):
            flags.append("attachment_pesel_redacted")
            return REDACTION
        return match.group(0)

    return _PESEL_RE.sub(replace, text), flags


@dataclass
class AttachmentValidation:
    allowed: bool
    text: str
    reason: str | None = None
    flags: list[str] = field(default_factory=list)


@observe(name="validate_attachment_text")
def validate_attachment_text(text: str) -> AttachmentValidation:
    """Content check for text extracted from an attachment.

    The two risks are handled differently on purpose, because their causes are
    different:

    - **Prompt injection → reject.** A delivery note does not accidentally
      contain "ignoruj poprzednie instrukcje". Text like that in a document the
      model is about to read is indirect prompt injection, i.e. an attack on the
      system, and the whole request is refused.
    - **Sensitive personal data → redact, don't reject.** The employee did not
      write the PDF; a supplier's document may legitimately carry someone's
      PESEL. Rejecting would punish the employee for a third party's formatting
      while a redaction already achieves the actual goal — the number never
      reaches the classifier, the agents, or Langfuse. The rest of the document
      (order number, supplier, dates) stays usable.
    """
    if _detect_prompt_injection(text):
        return AttachmentValidation(
            allowed=False,
            text=text,
            reason="załącznik zawiera treść wyglądającą na próbę prompt injection",
        )

    cleaned, flags = redact_sensitive(text)
    return AttachmentValidation(allowed=True, text=cleaned, flags=flags)
