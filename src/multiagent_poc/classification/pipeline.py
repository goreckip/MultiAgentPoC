"""Ties validation + classifier + gate + optional attachment together,
matching docs/sequence_diagram.md end to end (minus RAG/subagent generation
and HITL, still ahead in Week 4). Stand-in for the LangGraph orchestration —
small enough to be directly testable before the graph exists.

Order matters, in two ways:
1. Input validation runs first, before anything else — a PESEL, prompt
   injection attempt, or third-party data request never reaches the
   classifier or an LLM (raises ValidationRejected).
2. The malware scan runs immediately and unconditionally whenever an
   attachment is present, *before* classification — a rejected attachment
   aborts the whole request. PDF text extraction only happens afterwards,
   and only if the text-only classification was already below the
   confidence threshold (no point parsing a document the classifier
   didn't need).
"""

from dataclasses import dataclass
from pathlib import Path

from multiagent_poc.classification.classifier import classify
from multiagent_poc.classification.gate import GateDecision, decide
from multiagent_poc.observability.langfuse_client import observe
from multiagent_poc.validation.attachment import parse_pdf_text
from multiagent_poc.validation.attachment_scan import scan_file
from multiagent_poc.validation.input_validation import ValidationRejected, validate_input


@dataclass
class PipelineResult:
    decision: GateDecision
    used_attachment: bool
    validation_flags: list[str]


@observe(name="handle_question")
def handle_question(question: str, attachment_path: Path | None = None) -> PipelineResult:
    validation = validate_input(question)
    if not validation.allowed:
        raise ValidationRejected(validation.reason)

    if attachment_path is not None:
        scan_file(attachment_path)  # raises AttachmentRejected — caller decides how to surface that

    decision = decide(classify(question))
    if not decision.should_escalate or attachment_path is None:
        return PipelineResult(decision=decision, used_attachment=False, validation_flags=validation.flags)

    attachment_text = parse_pdf_text(attachment_path)  # already scanned above
    combined_question = f"{question}\n\n{attachment_text}"
    decision = decide(classify(combined_question))
    return PipelineResult(decision=decision, used_attachment=True, validation_flags=validation.flags)
