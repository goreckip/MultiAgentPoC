"""Integration test for the intent classifier + confidence gate — requires a
running Ollama with nomic-embed-text pulled. Skips gracefully if unreachable
(e.g. CI without Ollama), matching how scripts/evaluate_classifier.py is
meant to be run manually during development.
"""

import httpx
import pytest

from multiagent_poc.classification.classifier import build_exemplar_index, classify
from multiagent_poc.classification.eval_set import EVAL_QUESTIONS
from multiagent_poc.classification.gate import decide
from multiagent_poc.config import settings


def _ollama_available() -> bool:
    try:
        httpx.get(settings.ollama_base_url, timeout=2.0)
        return True
    except httpx.HTTPError:
        return False


pytestmark = pytest.mark.skipif(not _ollama_available(), reason="Ollama not reachable")


@pytest.fixture(scope="module", autouse=True)
def _index():
    build_exemplar_index()


def test_safety_critical_questions_always_escalate():
    """The 5 out-of-catalog/sensitive questions must escalate regardless of
    which intent the nearest-neighbor vote happens to lean toward — this is
    the property the confidence gate exists to guarantee.
    """
    escalate_items = [item for item in EVAL_QUESTIONS if item.expect_escalate]
    assert len(escalate_items) == 5

    failures = []
    for item in escalate_items:
        decision = decide(classify(item.question))
        if not decision.should_escalate:
            failures.append(item.question)

    assert not failures, f"expected escalation but got auto-routed: {failures}"


def test_classifier_accuracy_above_baseline():
    """Documents the current accuracy (65% with k=3, see decision_log.md) as a
    regression floor, not a target — tightening exemplars/k should raise this,
    but it should not silently drop.
    """
    correct = 0
    for item in EVAL_QUESTIONS:
        decision = decide(classify(item.question))
        if item.expect_escalate:
            correct += decision.should_escalate
        else:
            correct += (not decision.should_escalate) and decision.effective_intent in item.expected_intents

    accuracy = correct / len(EVAL_QUESTIONS)
    assert accuracy >= 0.6, f"accuracy regressed: {accuracy:.0%}"
