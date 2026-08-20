"""Sprint 3: run the intent classifier + confidence gate over the held-out
eval set and report accuracy, plus every misclassification for the log.
"""

from multiagent_poc.classification.classifier import build_exemplar_index, classify
from multiagent_poc.classification.eval_set import EVAL_QUESTIONS
from multiagent_poc.classification.gate import decide


def run():
    build_exemplar_index()

    correct = 0
    rows = []
    for item in EVAL_QUESTIONS:
        clf = classify(item.question)
        decision = decide(clf)

        if item.expect_escalate:
            is_correct = decision.should_escalate
        else:
            is_correct = (not decision.should_escalate) and clf.intent in item.expected_intents

        correct += is_correct
        rows.append((item, clf, decision, is_correct))

    print(f"\nAccuracy: {correct}/{len(EVAL_QUESTIONS)} ({100 * correct / len(EVAL_QUESTIONS):.0f}%)\n")

    for item, clf, decision, is_correct in rows:
        mark = "OK " if is_correct else "MISS"
        expected = "ESCALATE" if item.expect_escalate else "/".join(i.value for i in item.expected_intents)
        print(f"[{mark}] conf={clf.confidence:.2f} predicted={clf.intent.value:<20} escalate={decision.should_escalate!s:<5} expected={expected}")
        print(f"       {item.question}")
        if not is_correct:
            print(f"       votes: {clf.vote_counts}")
        print()


if __name__ == "__main__":
    run()
