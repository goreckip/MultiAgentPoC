from multiagent_poc.agents.drafting_agent import DOCUMENT_TEMPLATES, draft_document
from multiagent_poc.intents import Intent


def test_higiena_and_inne_have_no_template():
    assert Intent.HIGIENA not in DOCUMENT_TEMPLATES
    assert Intent.INNE not in DOCUMENT_TEMPLATES


def test_sensitive_categories_require_human_review():
    assert DOCUMENT_TEMPLATES[Intent.BHP].requires_human_review is True
    assert DOCUMENT_TEMPLATES[Intent.HR].requires_human_review is True


def test_non_sensitive_categories_do_not_require_review():
    for intent in [Intent.DOSTAWY, Intent.REKLAMACJE, Intent.PLATNOSCI, Intent.AWARIE_TECHNICZNE, Intent.SKARGI_KLIENTA]:
        assert DOCUMENT_TEMPLATES[intent].requires_human_review is False


def test_draft_document_returns_none_for_intent_without_template():
    assert draft_document("pytanie", Intent.HIGIENA, chunks=[]) is None
