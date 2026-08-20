"""Shared state shape for the pipeline graph."""

from typing import TypedDict

from multiagent_poc.rag.retrieval import RetrievedChunk


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
    answer_chunks: list[RetrievedChunk]
    draft_doc_type: str | None
    draft_text: str | None
    draft_pending_review: bool
