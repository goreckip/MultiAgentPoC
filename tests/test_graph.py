"""Tests for graph/pipeline_graph.py routing — mocks handle_question() and
the subagent so this runs fast/deterministically. Live end-to-end behavior
(including a real HITL pause/resume) is exercised manually via
scripts/demo_graph.py.
"""

import uuid
from unittest.mock import patch

from langgraph.types import Command

from multiagent_poc.agents.drafting_agent import DraftedDocument
from multiagent_poc.agents.subagent import AgentAnswer
from multiagent_poc.classification.classifier import IntentClassification
from multiagent_poc.classification.gate import GateDecision
from multiagent_poc.classification.pipeline import PipelineResult
from multiagent_poc.graph.pipeline_graph import build_graph
from multiagent_poc.intents import Intent
from multiagent_poc.validation.input_validation import ValidationRejected


def _config():
    return {"configurable": {"thread_id": str(uuid.uuid4())}}


def _pipeline_result(intent: Intent, confidence: float, escalate: bool) -> PipelineResult:
    clf = IntentClassification(intent=intent, confidence=confidence, vote_counts={})
    decision = GateDecision(
        effective_intent=Intent.INNE if escalate else intent,
        should_escalate=escalate,
        raw_classification=clf,
    )
    return PipelineResult(decision=decision, used_attachment=False, validation_flags=[])


def test_auto_answer_route():
    graph = build_graph()
    with patch(
        "multiagent_poc.graph.pipeline_graph.handle_question",
        return_value=_pipeline_result(Intent.DOSTAWY, 1.0, escalate=False),
    ), patch(
        "multiagent_poc.graph.pipeline_graph.agent_answer",
        return_value=AgentAnswer(text="magazynuj oddzielnie", sources=["01_dostawy.md"], chunks=[]),
    ), patch("multiagent_poc.graph.pipeline_graph.draft_document", return_value=None):
        result = graph.invoke({"question": "cokolwiek"}, config=_config())

    assert result["rejected"] is False
    assert result["should_escalate"] is False
    assert result["answer"] == "magazynuj oddzielnie"
    assert result["sources"] == ["01_dostawy.md"]
    assert "__interrupt__" not in result


def test_rejected_route_never_calls_agent():
    graph = build_graph()
    with patch(
        "multiagent_poc.graph.pipeline_graph.handle_question",
        side_effect=ValidationRejected("wykryto PESEL"),
    ), patch("multiagent_poc.graph.pipeline_graph.agent_answer") as mock_agent:
        result = graph.invoke({"question": "cokolwiek"}, config=_config())

    assert result["rejected"] is True
    assert "PESEL" in result["answer"]
    mock_agent.assert_not_called()


def test_draft_without_review_flows_straight_through():
    graph = build_graph()
    draft = DraftedDocument(doc_type="Zgłoszenie rozbieżności dostawy", text="SZKIC", requires_review=False)
    with patch(
        "multiagent_poc.graph.pipeline_graph.handle_question",
        return_value=_pipeline_result(Intent.DOSTAWY, 1.0, escalate=False),
    ), patch(
        "multiagent_poc.graph.pipeline_graph.agent_answer",
        return_value=AgentAnswer(text="magazynuj oddzielnie", sources=["01_dostawy.md"], chunks=[]),
    ), patch("multiagent_poc.graph.pipeline_graph.draft_document", return_value=draft):
        result = graph.invoke({"question": "cokolwiek"}, config=_config())

    assert "__interrupt__" not in result
    assert result["draft_doc_type"] == "Zgłoszenie rozbieżności dostawy"
    assert result["draft_text"] == "SZKIC"
    assert result["draft_pending_review"] is False


def test_draft_requiring_review_pauses_then_resumes_with_approved_text():
    graph = build_graph()
    config = _config()
    draft = DraftedDocument(doc_type="Karta zdarzenia BHP", text="SZKIC surowy", requires_review=True)

    with patch(
        "multiagent_poc.graph.pipeline_graph.handle_question",
        return_value=_pipeline_result(Intent.BHP, 1.0, escalate=False),
    ), patch(
        "multiagent_poc.graph.pipeline_graph.agent_answer",
        return_value=AgentAnswer(text="pierwsza pomoc", sources=["04_bhp.md"], chunks=[]),
    ), patch("multiagent_poc.graph.pipeline_graph.draft_document", return_value=draft):
        first = graph.invoke({"question": "poparzenie"}, config=config)

    assert "__interrupt__" in first
    payload = first["__interrupt__"][0].value
    assert payload["kind"] == "document_review"
    assert payload["document_type"] == "Karta zdarzenia BHP"
    assert payload["document_text"] == "SZKIC surowy"

    second = graph.invoke(Command(resume="SZKIC zatwierdzony przez operatora"), config=config)
    assert second["answer"] == "pierwsza pomoc"  # procedural answer survives the pause
    assert second["draft_text"] == "SZKIC zatwierdzony przez operatora"
    assert second["draft_pending_review"] is False


def test_escalate_pauses_then_resumes_with_human_answer():
    graph = build_graph()
    config = _config()

    with patch(
        "multiagent_poc.graph.pipeline_graph.handle_question",
        return_value=_pipeline_result(Intent.HR, 0.33, escalate=True),
    ):
        first = graph.invoke({"question": "niejednoznaczne pytanie"}, config=config)

    assert "__interrupt__" in first
    payload = first["__interrupt__"][0].value
    assert "reason" in payload

    second = graph.invoke(Command(resume="odpowiedź człowieka"), config=config)
    assert second["answer"] == "odpowiedź człowieka"
