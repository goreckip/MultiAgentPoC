"""Req 3.7 — one real question through the entire pipeline, no mocks.

Marked `slow` because it makes two live Ollama calls (subagent answer +
drafting agent) and takes ~4-5 minutes on CPU-only inference. Excluded from
the default run; opt in with:

    pytest -m slow

Everything else in the suite mocks the LLM, so this is the only test that
proves the whole graph — validation, classification, gate, retrieval,
generation, document drafting — actually holds together against a live model.
"""

import re
import uuid

import httpx
import pytest

from multiagent_poc.config import settings
from multiagent_poc.graph.pipeline_graph import build_graph, invoke_graph


def _ollama_available() -> bool:
    try:
        httpx.get(settings.ollama_base_url, timeout=2.0)
        return True
    except httpx.HTTPError:
        return False


pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(not _ollama_available(), reason="Ollama not reachable"),
]

QUESTION = (
    "Przy odbiorze towaru brakuje dwóch palet względem WZ, kierowca już odjechał, "
    "dostawa była dziś rano od Centralnego Dostawcy, co mam zrobić?"
)


@pytest.fixture(scope="module")
def result():
    graph = build_graph()
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    return invoke_graph(graph, {"question": QUESTION}, config=config)


def test_pipeline_completes_without_escalating(result):
    assert result["rejected"] is False
    assert result["should_escalate"] is False
    assert result["intent"] == "dostawy"
    assert "__interrupt__" not in result


def test_answer_is_grounded_in_the_right_runbook(result):
    """The delivery subagent must cite only its own runbook — the Chroma
    metadata filter is what guarantees a "dostawy" question can't be answered
    out of the BHP or HR procedure.
    """
    assert result["sources"] == ["01_dostawy.md"]
    assert result["answer"] and len(result["answer"]) > 40


def test_answer_does_not_invent_an_expansion_for_wz(result):
    """Regression guard for a hallucination caught live: the model invents an
    expansion for "WZ", which no runbook spells out.

    Pattern-based rather than a blocklist of known-bad strings on purpose — the
    first version of this test listed the three phrasings seen at the time, and
    promptly missed the next two the model came up with ("Zamówienia Zamkowego",
    "Widza Zlecenia"). Matching the *shape* of an expansion catches wordings
    nobody has seen yet.
    """
    combined = f"{result['answer']} {result.get('draft_text') or ''}"

    # 01_dostawy.md itself writes "listu przewozowego (WZ)", so that one
    # expansion is legitimate — anything else is the model filling a gap.
    def is_invented(phrase: str) -> bool:
        return "przewozow" not in phrase.lower()

    # "Jakieś Słowa (WZ)" — expansion placed before the abbreviation.
    before = re.findall(r"((?:\w+\s+){0,2}\w+)\s*\(\s*WZ\s*\)", combined)
    # "WZ (jakieś słowa)" — expansion placed after it.
    after = re.findall(r"\bWZ\s*\(\s*([^)]{4,})\)", combined)

    invented = [p for p in before + after if is_invented(p)]
    assert not invented, f"model invented an expansion for the WZ abbreviation: {invented}"


def test_drafting_agent_produced_a_document(result):
    assert result["draft_doc_type"] == "Zgłoszenie rozbieżności dostawy"
    assert result["draft_text"]
    assert result["draft_pending_review"] is False  # dostawy needs no human review
