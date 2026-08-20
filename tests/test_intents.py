from multiagent_poc.intents import INTENT_RUNBOOK_MAP, Intent, runbook_path


def test_every_intent_except_inne_has_runbook():
    for intent in Intent:
        path = runbook_path(intent)
        if intent is Intent.INNE:
            assert path is None
        else:
            assert path is not None
            assert path.exists(), f"missing runbook file for {intent}"


def test_intent_map_covers_all_enum_members():
    assert set(INTENT_RUNBOOK_MAP.keys()) == set(Intent)
