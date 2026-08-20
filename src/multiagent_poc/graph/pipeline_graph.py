"""LangGraph wiring for the full flow in docs/sequence_diagram.md: validation
+ classification + confidence gate (+ optional attachment) already live in
classification/pipeline.py — this graph adds the branching or done in
Weeks 1-4 and the human-in-the-loop escalation via interrupt()/resume,
which needs an actual graph (a plain function can't pause and resume).

Thread-based resume: every conversation needs a stable `thread_id` in the
invoke config so the checkpointer can find the paused state again when a
human answer comes back via Command(resume=...).
"""

from pathlib import Path

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from multiagent_poc.agents.drafting_agent import draft_document
from multiagent_poc.agents.subagent import answer as agent_answer
from multiagent_poc.classification.pipeline import handle_question
from multiagent_poc.graph.state import GraphState
from multiagent_poc.intents import Intent
from multiagent_poc.observability.langfuse_client import observe
from multiagent_poc.validation.attachment_scan import AttachmentRejected
from multiagent_poc.validation.input_validation import ValidationRejected


def classify_node(state: GraphState) -> dict:
    attachment_path = Path(state["attachment_path"]) if state.get("attachment_path") else None
    try:
        result = handle_question(state["question"], attachment_path=attachment_path)
    except (ValidationRejected, AttachmentRejected) as e:
        return {"rejected": True, "rejection_reason": str(e)}

    return {
        "rejected": False,
        "intent": result.decision.effective_intent.value,
        "confidence": result.decision.raw_classification.confidence,
        "should_escalate": result.decision.should_escalate,
        "used_attachment": result.used_attachment,
        "attachment_text": result.attachment_text,
    }


def route_after_classify(state: GraphState) -> str:
    if state.get("rejected"):
        return "rejected"
    if state.get("should_escalate"):
        return "escalate"
    return "auto_answer"


def auto_answer_node(state: GraphState) -> dict:
    intent = Intent(state["intent"])
    attachment_text = state.get("attachment_text")
    result = agent_answer(state["question"], intent, attachment_text=attachment_text)
    update = {"answer": result.text, "sources": result.sources, "draft_pending_review": False}

    draft = draft_document(state["question"], intent, result.chunks, attachment_text=attachment_text)
    if draft is not None:
        update["draft_doc_type"] = draft.doc_type
        update["draft_text"] = draft.text
        update["draft_pending_review"] = draft.requires_review

    return update


def route_after_auto_answer(state: GraphState) -> str:
    return "document_review" if state.get("draft_pending_review") else "end"


def document_review_node(state: GraphState) -> dict:
    approved_text = interrupt(
        {
            "kind": "document_review",
            "question": state["question"],
            "document_type": state.get("draft_doc_type"),
            "document_text": state.get("draft_text"),
        }
    )
    return {"draft_text": approved_text, "draft_pending_review": False}


def escalate_node(state: GraphState) -> dict:
    confidence = state.get("confidence")
    reason = f"confidence={confidence:.2f} < próg" if confidence is not None else "brak dopasowania do katalogu intencji"
    human_answer = interrupt({"kind": "escalation", "question": state["question"], "reason": reason})
    return {"answer": human_answer, "sources": []}


def rejected_node(state: GraphState) -> dict:
    return {"answer": f"Nie mogę pomóc z tym pytaniem: {state['rejection_reason']}", "sources": []}


def build_graph():
    graph = StateGraph(GraphState)
    graph.add_node("classify", classify_node)
    graph.add_node("auto_answer", auto_answer_node)
    graph.add_node("document_review", document_review_node)
    graph.add_node("escalate", escalate_node)
    graph.add_node("rejected", rejected_node)

    graph.add_edge(START, "classify")
    graph.add_conditional_edges(
        "classify",
        route_after_classify,
        {"auto_answer": "auto_answer", "escalate": "escalate", "rejected": "rejected"},
    )
    graph.add_conditional_edges(
        "auto_answer",
        route_after_auto_answer,
        {"document_review": "document_review", "end": END},
    )
    graph.add_edge("document_review", END)
    graph.add_edge("escalate", END)
    graph.add_edge("rejected", END)

    return graph.compile(checkpointer=MemorySaver())


@observe(name="handle_user_turn")
def invoke_graph(graph, inputs, config: dict) -> dict:
    """Thin wrapper that gives every graph.invoke() call (a fresh question or
    a Command(resume=...) after HITL) its own Langfuse trace, with everything
    called underneath (validation, classification, gate, subagent, malware
    scan) nesting into it automatically via @observe's contextvar propagation
    — as long as the graph runs synchronously in this thread, which it does.
    """
    return graph.invoke(inputs, config=config)
