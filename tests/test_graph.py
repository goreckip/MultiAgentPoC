"""Tests for graph/pipeline_graph.py routing — mocks handle_question() and
the subagent so this runs fast/deterministically. Live end-to-end behavior
(including a real HITL pause/resume) is exercised manually via
scripts/demo_graph.py.
"""

import uuid
from unittest.mock import patch

from langgraph.types import Command

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
    ):
        result = graph.invoke({"question": "cokolwiek"}, config=_config())

    assert result["rejected"] is False
    assert result["should_escalate"] is False
    assert result["answer"] == "magazynuj oddzielnie"
    assert result["sources"] == ["01_dostawy.md"]


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
