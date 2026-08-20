"""In-process, shared HITL queue (architecture layer 6).

Previously the Streamlit app tracked "the one pending escalation" in
st.session_state, scoped to a single browser session — an operator could
only ever see and resolve an escalation raised by their *own* session, which
isn't a queue, it's a private mailbox. This module is a module-level
registry (shared by every Streamlit session in the same process, since
Streamlit sessions run in threads of one process, not separate processes),
so an operator panel can list and resolve escalations raised by anyone.

Deliberately in-memory, not a database — same simplification as LangGraph's
MemorySaver checkpointer (state doesn't survive a process restart). A real
deployment would back this with Redis/Postgres so the queue survives
restarts and works across multiple app instances; out of scope for this PoC.

Two kinds of pending item share the same queue: "escalation" (confidence
gate couldn't route the question) and "document_review" (drafting_agent
produced a document for a category — BHP, HR — that always needs a human
look before it reaches the employee). Same underlying mechanism
(interrupt()/resume on a paused thread), different payload shape.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import threading

_lock = threading.Lock()

KIND_ESCALATION = "escalation"
KIND_DOCUMENT_REVIEW = "document_review"


@dataclass
class PendingEscalation:
    thread_id: str
    question: str
    reason: str
    kind: str = KIND_ESCALATION
    document_type: str | None = None
    document_text: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


_pending: dict[str, PendingEscalation] = {}
_resolved: dict[str, dict] = {}


def add_pending(thread_id: str, question: str, reason: str) -> None:
    with _lock:
        _pending[thread_id] = PendingEscalation(thread_id=thread_id, question=question, reason=reason)


def add_pending_document_review(thread_id: str, question: str, document_type: str, document_text: str) -> None:
    with _lock:
        _pending[thread_id] = PendingEscalation(
            thread_id=thread_id,
            question=question,
            reason=f"dokument do zatwierdzenia: {document_type}",
            kind=KIND_DOCUMENT_REVIEW,
            document_type=document_type,
            document_text=document_text,
        )


def list_pending() -> list[PendingEscalation]:
    with _lock:
        return sorted(_pending.values(), key=lambda p: p.created_at)


def pop_pending(thread_id: str) -> PendingEscalation | None:
    with _lock:
        return _pending.pop(thread_id, None)


def set_resolved(thread_id: str, result: dict) -> None:
    with _lock:
        _resolved[thread_id] = result


def take_resolved(thread_id: str) -> dict | None:
    """Fetches and removes the resolved result for a thread, if ready —
    'take' (not 'get') because each result is meant to be delivered once,
    back to the one session that asked the question.
    """
    with _lock:
        return _resolved.pop(thread_id, None)
