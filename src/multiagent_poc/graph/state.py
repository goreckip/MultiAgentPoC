"""Shared state shape for the pipeline graph."""

from typing import TypedDict


class GraphState(TypedDict, total=False):
    question: str
    attachment_path: str | None
    rejected: bool
    rejection_reason: str | None
    intent: str | None
    confidence: float | None
    should_escalate: bool
    used_attachment: bool
    answer: str | None
    sources: list[str]
