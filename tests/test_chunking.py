"""Structural comparison of the two chunking strategies, no embeddings needed.

Mirrors the experiment suggested in docs/runbooks/README.md: does the answer
to "dostawca przywiózł inny towar niż zamówiony, kierowca już odjechał" (section
4.3 of 01_dostawy.md) end up in a single, self-contained, on-topic chunk?
"""

from multiagent_poc.intents import RUNBOOKS_DIR
from multiagent_poc.rag.chunking import fixed_size_chunks, section_chunks

DOSTAWY_TEXT = (RUNBOOKS_DIR / "01_dostawy.md").read_text(encoding="utf-8")
NEEDLE = "Pomyłka dostawcy"
ANSWER_FRAGMENT = "produkt magazynować oddzielnie"


def test_section_chunk_is_self_contained_and_on_topic():
    chunks = section_chunks(DOSTAWY_TEXT, source="01_dostawy.md")
    matching = [c for c in chunks if ANSWER_FRAGMENT in c.text]

    assert len(matching) == 1, "answer should live in exactly one section chunk"
    chunk = matching[0]
    assert NEEDLE in chunk.heading_path, "heading_path should carry the parent section context"
    # single-topic: this chunk should not also contain unrelated sibling content
    assert "Brak towaru" not in chunk.text


def test_fixed_size_chunk_may_split_the_answer_across_boundaries():
    chunks = fixed_size_chunks(DOSTAWY_TEXT, source="01_dostawy.md", size=500, overlap=50)
    matching = [c for c in chunks if ANSWER_FRAGMENT in c.text]

    # Documents the trade-off: fixed-size chunking has no guarantee the answer
    # isn't split across two 500-char windows, or that a matching chunk carries
    # any indication of which section it belongs to.
    assert len(matching) >= 0  # informational — see decision_log.md for the write-up
    for c in matching:
        assert c.heading_path is None
