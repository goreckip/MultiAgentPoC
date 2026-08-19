"""Tests for classification/pipeline.py — mocks classify() so this runs fast
and deterministically (no live Ollama calls). Live classifier behavior is
covered separately in test_classifier.py.
"""

from unittest.mock import patch

import pytest

from multiagent_poc.classification.classifier import IntentClassification
from multiagent_poc.classification.pipeline import handle_question
from multiagent_poc.intents import Intent
from multiagent_poc.validation.attachment_scan import AttachmentRejected
from tests.test_attachment import _make_minimal_pdf_with_text


def _clf(intent: Intent, confidence: float) -> IntentClassification:
    return IntentClassification(intent=intent, confidence=confidence, vote_counts={intent.value: 2})


def test_high_confidence_never_touches_attachment(tmp_path):
    pdf_path = tmp_path / "order.pdf"
    pdf_path.write_bytes(_make_minimal_pdf_with_text("cokolwiek"))

    with patch("multiagent_poc.classification.pipeline.classify", return_value=_clf(Intent.DOSTAWY, 1.0)) as mock_classify:
        result = handle_question("Dostawa nie doszła", attachment_path=pdf_path)

    assert result.used_attachment is False
    assert result.decision.effective_intent == Intent.DOSTAWY
    mock_classify.assert_called_once()  # only the text-only pass — attachment never parsed


def test_low_confidence_with_attachment_reclassifies(tmp_path):
    pdf_path = tmp_path / "order.pdf"
    pdf_path.write_bytes(_make_minimal_pdf_with_text("Zamowienie ZM-2024-00981"))

    responses = [_clf(Intent.HR, 0.33), _clf(Intent.DOSTAWY, 0.67)]
    with patch("multiagent_poc.classification.pipeline.classify", side_effect=responses) as mock_classify:
        result = handle_question("Co robić z tym zamówieniem?", attachment_path=pdf_path)

    assert result.used_attachment is True
    assert result.decision.effective_intent == Intent.DOSTAWY
    assert mock_classify.call_count == 2
    second_call_arg = mock_classify.call_args_list[1].args[0]
    assert "ZM-2024-00981" in second_call_arg


def test_low_confidence_without_attachment_just_escalates():
    with patch("multiagent_poc.classification.pipeline.classify", return_value=_clf(Intent.HR, 0.33)) as mock_classify:
        result = handle_question("Pytanie bez załącznika")

    assert result.used_attachment is False
    assert result.decision.should_escalate is True
    mock_classify.assert_called_once()


def test_rejected_attachment_aborts_before_classification(tmp_path):
    big_file = tmp_path / "huge.pdf"
    big_file.write_bytes(b"0" * (11 * 1024 * 1024))

    with patch("multiagent_poc.classification.pipeline.classify") as mock_classify:
        with pytest.raises(AttachmentRejected):
            handle_question("Pytanie", attachment_path=big_file)

    mock_classify.assert_not_called()
