from unittest.mock import MagicMock, patch

from multiagent_poc.evaluation.judge import judge_answer
from multiagent_poc.evaluation.rag_eval_set import RAG_EVAL_SET
from multiagent_poc.intents import INTENT_RUNBOOK_MAP, RUNBOOKS_DIR


def test_ground_truth_expected_source_matches_intent_runbook_map():
    """Guards against a copy-paste mistake between intent and expected_source
    — if these ever disagree, the whole eval is silently testing the wrong
    runbook for that question.
    """
    for item in RAG_EVAL_SET:
        assert INTENT_RUNBOOK_MAP[item.intent] == item.expected_source, item.question


def test_ground_truth_expected_source_files_exist():
    for item in RAG_EVAL_SET:
        assert (RUNBOOKS_DIR / item.expected_source).exists(), item.expected_source


def test_ground_truth_has_at_least_one_keyword_per_question():
    for item in RAG_EVAL_SET:
        assert len(item.expected_keywords) >= 1, item.question


def _fake_response(content: str):
    r = MagicMock()
    r.content = content
    return r


def test_judge_answer_parses_well_formed_response():
    with patch("langchain_ollama.ChatOllama.invoke", return_value=_fake_response("SCORE: 4\nREASON: Zgodne z procedurą.")):
        result = judge_answer("pytanie", "kontekst", "odpowiedź")

    assert result.score == 4
    assert result.reason == "Zgodne z procedurą."


def test_judge_answer_handles_unparseable_response_gracefully():
    with patch("langchain_ollama.ChatOllama.invoke", return_value=_fake_response("Nie jestem pewien.")):
        result = judge_answer("pytanie", "kontekst", "odpowiedź")

    assert result.score is None
    assert result.reason == "Nie jestem pewien."
