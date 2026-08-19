"""Ties classifier + gate + optional attachment together, matching the
"confidence gate" branch of docs/sequence_diagram.md. This is a stand-in for
the LangGraph orchestration planned for Week 4 (src/multiagent_poc/graph/) —
small enough to be directly testable before the graph exists.

Attachment handling order matters: the malware scan runs immediately and
unconditionally whenever an attachment is present, *before* classification —
a rejected attachment aborts the whole request. PDF text extraction only
happens afterwards, and only if the text-only classification was already
below the confidence threshold (no point parsing a document the classifier
didn't need).
"""

from dataclasses import dataclass
from pathlib import Path

from multiagent_poc.classification.classifier import classify
from multiagent_poc.classification.gate import GateDecision, decide
from multiagent_poc.validation.attachment import parse_pdf_text
from multiagent_poc.validation.attachment_scan import scan_file


@dataclass
class PipelineResult:
    decision: GateDecision
    used_attachment: bool


def handle_question(question: str, attachment_path: Path | None = None) -> PipelineResult:
    if attachment_path is not None:
        scan_file(attachment_path)  # raises AttachmentRejected — caller decides how to surface that

    decision = decide(classify(question))
    if not decision.should_escalate or attachment_path is None:
        return PipelineResult(decision=decision, used_attachment=False)

    attachment_text = parse_pdf_text(attachment_path)  # already scanned above
    combined_question = f"{question}\n\n{attachment_text}"
    decision = decide(classify(combined_question))
    return PipelineResult(decision=decision, used_attachment=True)
