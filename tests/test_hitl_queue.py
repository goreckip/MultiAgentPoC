from multiagent_poc.hitl import queue as hitl_queue


def test_add_and_list_pending_across_multiple_threads():
    hitl_queue.add_pending("t1", "pytanie 1", "confidence=0.3 < próg")
    hitl_queue.add_pending("t2", "pytanie 2", "brak dopasowania do katalogu intencji")

    pending = hitl_queue.list_pending()
    thread_ids = {p.thread_id for p in pending}

    assert "t1" in thread_ids
    assert "t2" in thread_ids

    hitl_queue.pop_pending("t1")
    hitl_queue.pop_pending("t2")


def test_pending_is_ordered_by_creation_time():
    hitl_queue.add_pending("a", "pierwsze", "r")
    hitl_queue.add_pending("b", "drugie", "r")

    pending = [p for p in hitl_queue.list_pending() if p.thread_id in ("a", "b")]
    assert [p.thread_id for p in pending] == ["a", "b"]

    hitl_queue.pop_pending("a")
    hitl_queue.pop_pending("b")


def test_pop_pending_removes_it_from_the_queue():
    hitl_queue.add_pending("x", "pytanie", "r")
    assert hitl_queue.pop_pending("x") is not None
    assert "x" not in {p.thread_id for p in hitl_queue.list_pending()}
    assert hitl_queue.pop_pending("x") is None


def test_resolved_result_is_delivered_once():
    hitl_queue.set_resolved("y", {"answer": "odpowiedź operatora"})

    first = hitl_queue.take_resolved("y")
    second = hitl_queue.take_resolved("y")

    assert first == {"answer": "odpowiedź operatora"}
    assert second is None


def test_take_resolved_returns_none_when_nothing_pending():
    assert hitl_queue.take_resolved("does-not-exist") is None


def test_add_pending_document_review_carries_document_fields():
    hitl_queue.add_pending_document_review("doc1", "pytanie o wypadek", "Karta zdarzenia BHP", "SZKIC dokumentu")

    item = next(p for p in hitl_queue.list_pending() if p.thread_id == "doc1")
    assert item.kind == hitl_queue.KIND_DOCUMENT_REVIEW
    assert item.document_type == "Karta zdarzenia BHP"
    assert item.document_text == "SZKIC dokumentu"

    hitl_queue.pop_pending("doc1")


def test_add_pending_defaults_to_escalation_kind():
    hitl_queue.add_pending("esc1", "pytanie", "powód")

    item = next(p for p in hitl_queue.list_pending() if p.thread_id == "esc1")
    assert item.kind == hitl_queue.KIND_ESCALATION
    assert item.document_text is None

    hitl_queue.pop_pending("esc1")
