"""Confidence gate: decides whether the classifier's top intent is trustworthy
enough to auto-route, or whether the question should escalate to a human.

The classifier (classifier.py) only ever predicts one of the 8 process
intents — it has no exemplars for "inne". This module is what actually
produces Intent.INNE as an effective label, whenever confidence is too low
to trust the nearest-neighbor vote.
"""

from dataclasses import dataclass

from multiagent_poc.classification.classifier import IntentClassification
from multiagent_poc.config import settings
from multiagent_poc.intents import Intent
from multiagent_poc.observability.langfuse_client import observe


@dataclass
class GateDecision:
    effective_intent: Intent
    should_escalate: bool
    raw_classification: IntentClassification


@observe(name="confidence_gate")
def decide(classification: IntentClassification, threshold: float | None = None) -> GateDecision:
    threshold = settings.confidence_threshold if threshold is None else threshold

    if classification.confidence >= threshold:
        return GateDecision(
            effective_intent=classification.intent,
            should_escalate=False,
            raw_classification=classification,
        )

    return GateDecision(
        effective_intent=Intent.INNE,
        should_escalate=True,
        raw_classification=classification,
    )
