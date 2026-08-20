"""Sprint 6: evaluation framework for RAG retrieval + answer quality.

Three complementary signals per question (see rag_eval_set.py for ground
truth and judge.py for the LLM-judge caveat):
1. Retrieval hit-rate — did the expected section actually get retrieved.
2. Keyword coverage — deterministic, cheap, catches obvious regressions.
3. LLM-as-judge score (1-5) — more nuanced, catches paraphrases, but a
   same-model judge is a known-weak signal, reported separately.

Bypasses the classifier entirely (calls agents.subagent.answer with the
*correct* intent pinned) — this isolates RAG/generation quality from
classifier accuracy, already evaluated in scripts/evaluate_classifier.py.
"""

from multiagent_poc.agents.subagent import answer as agent_answer
from multiagent_poc.evaluation.judge import judge_answer
from multiagent_poc.evaluation.rag_eval_set import RAG_EVAL_SET


def run():
    retrieval_hits = 0
    retrieval_evaluated = 0
    keyword_scores = []
    judge_scores = []
    rows = []

    for item in RAG_EVAL_SET:
        result = agent_answer(item.question, item.intent)

        retrieval_hit = None
        if item.expected_heading_substring:
            retrieval_evaluated += 1
            retrieval_hit = any(item.expected_heading_substring in c.heading_path for c in result.chunks)
            retrieval_hits += retrieval_hit

        answer_lower = result.text.lower()
        matched_keywords = [kw for kw in item.expected_keywords if kw.lower() in answer_lower]
        keyword_score = len(matched_keywords) / len(item.expected_keywords) if item.expected_keywords else None
        if keyword_score is not None:
            keyword_scores.append(keyword_score)

        context = "\n\n".join(f"[{c.heading_path}]\n{c.text}" for c in result.chunks)
        judge = judge_answer(item.question, context, result.text)
        if judge.score is not None:
            judge_scores.append(judge.score)

        rows.append((item, result, retrieval_hit, keyword_score, matched_keywords, judge))

    print("\n=== Summary ===")
    if retrieval_evaluated:
        print(f"Retrieval hit-rate: {retrieval_hits}/{retrieval_evaluated} ({100 * retrieval_hits / retrieval_evaluated:.0f}%)")
    if keyword_scores:
        print(f"Keyword coverage (avg): {100 * sum(keyword_scores) / len(keyword_scores):.0f}% (n={len(keyword_scores)})")
    if judge_scores:
        print(f"LLM-judge score (avg): {sum(judge_scores) / len(judge_scores):.2f}/5 (n={len(judge_scores)})")

    print("\n=== Per-question ===")
    for item, result, retrieval_hit, keyword_score, matched_keywords, judge in rows:
        hit_mark = "  - " if retrieval_hit is None else (" HIT" if retrieval_hit else "MISS")
        kw_str = f"{100 * keyword_score:.0f}%" if keyword_score is not None else "-"
        print(f"[retrieval={hit_mark}] [kw={kw_str}] [judge={judge.score}/5]  {item.question}")
        print(f"    intent={item.intent.value}  matched_keywords={matched_keywords}")
        print(f"    answer: {result.text[:220]}")
        print(f"    judge_reason: {judge.reason}")
        if item.note:
            print(f"    note: {item.note}")
        print()


if __name__ == "__main__":
    run()
