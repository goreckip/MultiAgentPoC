"""The mask is the last thing standing between sensitive data and a third-party
cloud, so it gets tested independently of whether Langfuse is even reachable.
"""

from multiagent_poc.observability.langfuse_client import MASKED, mask_sensitive
from multiagent_poc.validation.input_validation import _PESEL_RE as VALIDATION_PESEL_RE
from multiagent_poc.observability.langfuse_client import _PESEL_RE as MASK_PESEL_RE

VALID_PESEL = "44051401359"


def test_masks_a_pesel_in_a_plain_string():
    assert VALID_PESEL not in mask_sensitive(f"Jaki jest PESEL kierownika? {VALID_PESEL}")


def test_masks_inside_nested_structures():
    """Span inputs arrive as the decorated function's args/kwargs, so the mask
    has to walk dicts and sequences, not just top-level strings.
    """
    payload = {
        "question": f"PESEL {VALID_PESEL}",
        "history": [{"text": f"powtorzony {VALID_PESEL}"}],
        "meta": ("krotka", f"{VALID_PESEL}"),
    }

    masked = mask_sensitive(payload)

    assert VALID_PESEL not in str(masked)
    assert masked["meta"][0] == "krotka"  # untouched values survive
    assert isinstance(masked["meta"], tuple)  # and container types are preserved


def test_leaves_ordinary_content_untouched():
    text = "Zamowienie ZM-2024-00981, brakuje dwoch palet"

    assert mask_sensitive(text) == text


def test_non_string_values_pass_through():
    assert mask_sensitive({"confidence": 0.67, "ok": True, "nic": None}) == {
        "confidence": 0.67,
        "ok": True,
        "nic": None,
    }


def test_mask_pattern_matches_the_validation_layer():
    """Both layers must agree on what a PESEL looks like; if one is tightened and
    the other isn't, data the validator blocks could still reach Langfuse.
    """
    assert MASK_PESEL_RE.pattern == VALIDATION_PESEL_RE.pattern


def test_masked_marker_is_not_mistaken_for_data():
    assert MASKED and VALID_PESEL not in MASKED
